from __future__ import annotations

import argparse
import filecmp
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from common import TalkingCraftError


@dataclass(frozen=True)
class InstallResult:
    destination: Path
    copied_files: tuple[str, ...]
    skipped_files: tuple[str, ...]
    conflicts: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "destination": str(self.destination),
            "copied_files": list(self.copied_files),
            "skipped_files": list(self.skipped_files),
            "conflicts": list(self.conflicts),
        }


def install_motion_kit(
    project_root: Path,
    *,
    source_dir: Path,
    force: bool = False,
) -> InstallResult:
    """Install the bundled motion kit without overwriting user changes by default."""
    root = project_root.expanduser().resolve()
    if not (root / "package.json").is_file():
        raise TalkingCraftError(f"Missing package.json in {root}")
    source = source_dir.expanduser().resolve()
    if not source.is_dir():
        raise TalkingCraftError(f"Motion kit source does not exist: {source}")
    destination = root / "src" / "motion-library"
    copied: list[str] = []
    skipped: list[str] = []
    conflicts: list[str] = []

    for source_path in sorted(path for path in source.rglob("*") if path.is_file()):
        relative = source_path.relative_to(source)
        target_path = destination / relative
        if target_path.exists() and not force:
            if filecmp.cmp(source_path, target_path, shallow=False):
                skipped.append(str(relative))
            else:
                conflicts.append(str(relative))
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied.append(str(relative))

    return InstallResult(
        destination=destination,
        copied_files=tuple(copied),
        skipped_files=tuple(skipped),
        conflicts=tuple(conflicts),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the bundled Ryan motion kit")
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        result = install_motion_kit(
            args.project_root, source_dir=args.source, force=args.force
        )
    except TalkingCraftError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2
    payload = {"ok": not result.conflicts, **result.to_dict()}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not result.conflicts else 1


if __name__ == "__main__":
    raise SystemExit(main())
