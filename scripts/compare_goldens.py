from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from common import TalkingCraftError, read_json, run_command, sha256_file, write_json


@dataclass(frozen=True)
class GoldenResult:
    template: str
    expected: Path
    actual: Path
    normalized_rmse: float
    passed: bool
    diff: Path | None

    def to_dict(self) -> dict[str, object]:
        return {
            "template": self.template,
            "expected": str(self.expected),
            "actual": str(self.actual),
            "normalized_rmse": self.normalized_rmse,
            "passed": self.passed,
            "diff": str(self.diff) if self.diff else None,
        }


def compare_goldens(
    manifest_path: Path,
    actual_dir: Path,
    *,
    threshold: float = 0.01,
    diff_dir: Path | None = None,
) -> tuple[GoldenResult, ...]:
    """Compare actual stills with the motion kit golden manifest."""
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("goldens"), list):
        raise TalkingCraftError("Golden manifest must contain a goldens array")
    base_dir = manifest_path.parent
    results: list[GoldenResult] = []
    for raw in manifest["goldens"]:
        if not isinstance(raw, dict):
            raise TalkingCraftError("Each golden entry must be an object")
        expected = base_dir / str(raw["path"])
        actual = actual_dir / expected.name
        if not expected.is_file() or not actual.is_file():
            raise TalkingCraftError(f"Missing golden pair: {expected} / {actual}")
        diff_path = None
        if diff_dir is not None:
            diff_dir.mkdir(parents=True, exist_ok=True)
            diff_path = diff_dir / expected.name
        normalized = _compare_images(expected, actual, diff_path)
        results.append(
            GoldenResult(
                template=str(raw["template"]),
                expected=expected,
                actual=actual,
                normalized_rmse=normalized,
                passed=normalized <= threshold,
                diff=diff_path,
            )
        )
    return tuple(results)


def _compare_images(expected: Path, actual: Path, diff: Path | None) -> float:
    magick = shutil.which("magick")
    if not magick:
        return 0.0 if sha256_file(expected) == sha256_file(actual) else 1.0
    output = diff or Path("/dev/null")
    result = run_command(
        (magick, "compare", "-metric", "RMSE", str(expected), str(actual), str(output)),
        check=False,
    )
    match = re.search(
        r"\(([0-9]*\.?[0-9]+(?:e[-+]?\d+)?)\)", result.stderr, re.IGNORECASE
    )
    if not match:
        if result.returncode == 0:
            return 0.0
        raise TalkingCraftError(
            f"Cannot parse ImageMagick RMSE: {result.stderr.strip()}"
        )
    return float(match.group(1))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare motion kit golden stills")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("actual_dir", type=Path)
    parser.add_argument("--threshold", type=float, default=0.01)
    parser.add_argument("--diff-dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        results = compare_goldens(
            args.manifest,
            args.actual_dir,
            threshold=args.threshold,
            diff_dir=args.diff_dir,
        )
    except TalkingCraftError as error:
        print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        return 2
    payload = {
        "passed": all(result.passed for result in results),
        "results": [result.to_dict() for result in results],
    }
    if args.output:
        write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
