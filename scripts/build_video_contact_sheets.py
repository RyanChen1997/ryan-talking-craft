from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from common import TalkingCraftError, write_json
from extract_frames import ExtractConfig, ExtractResult, extract_frames


@dataclass(frozen=True)
class BatchContactConfig:
    inputs: tuple[Path, ...]
    output_dir: Path
    sample_count: int = 12
    width: int = 480


@dataclass(frozen=True)
class BatchContactResult:
    results: tuple[ExtractResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "videos": [result.to_dict() for result in self.results],
        }


def build_video_contact_sheets(config: BatchContactConfig) -> BatchContactResult:
    """Build reproducible frame indexes and contact sheets for multiple recordings."""
    if not config.inputs:
        raise TalkingCraftError("At least one input video is required")
    output_root = config.output_dir.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()
    results: list[ExtractResult] = []
    for input_path in config.inputs:
        base_name = _safe_name(input_path.stem)
        name = _unique_name(base_name, used_names)
        used_names.add(name)
        results.append(
            extract_frames(
                ExtractConfig(
                    input_path=input_path,
                    output_dir=output_root / name,
                    sample_count=config.sample_count,
                    width=config.width,
                )
            )
        )
    result = BatchContactResult(results=tuple(results))
    write_json(output_root / "contact-sheet-index.json", result.to_dict())
    return result


def _safe_name(value: str) -> str:
    name = value.strip().lower().replace("_", "-")
    name = re.sub(r"[^a-z0-9\u4e00-\u9fff-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "video"


def _unique_name(base_name: str, used_names: set[str]) -> str:
    if base_name not in used_names:
        return base_name
    suffix = 2
    while f"{base_name}-{suffix:02d}" in used_names:
        suffix += 1
    return f"{base_name}-{suffix:02d}"


def _parse_args() -> BatchContactConfig:
    parser = argparse.ArgumentParser(
        description="Build contact sheets for user recordings"
    )
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--sample-count", default=12, type=int)
    parser.add_argument("--width", default=480, type=int)
    args = parser.parse_args()
    return BatchContactConfig(
        inputs=tuple(args.inputs),
        output_dir=args.output_dir,
        sample_count=args.sample_count,
        width=args.width,
    )


def main() -> int:
    try:
        result = build_video_contact_sheets(_parse_args())
    except TalkingCraftError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True, **result.to_dict()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
