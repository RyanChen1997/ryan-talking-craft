"""Whitelist installer; never installs preview or development caches."""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path

from common import TalkingCraftError

FILES = ("SKILL.md", "pyproject.toml", "uv.lock")
DIRECTORIES = ("references", "scripts", "assets/visual-kit")
EXCLUDED = {
    ".DS_Store",
    ".tmp",
    "__pycache__",
    "fixtures",
    "gallery",
    "golden-frames",
    "golden-manifest.json",
    "node_modules",
    "previews",
}


@dataclass(frozen=True)
class InstallConfig:
    source: Path
    skills_dir: Path
    force: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class InstallReport:
    target: Path
    files: tuple[str, ...]
    backup: Path | None = None
    dry_run: bool = False

    def to_dict(self) -> dict:
        return {"target": str(self.target), "files": list(self.files), "backup": str(self.backup) if self.backup else None, "dry_run": self.dry_run}

    @classmethod
    def from_dict(cls, value: dict) -> InstallReport:
        return cls(Path(value["target"]), tuple(value["files"]), Path(value["backup"]) if value.get("backup") else None, value.get("dry_run", False))


def install(config: InstallConfig) -> InstallReport:
    source = config.source.expanduser().resolve()
    parent = config.skills_dir.expanduser().resolve()
    target = parent / "ryan-talking-craft"
    if parent == Path(parent.anchor) or parent == Path.home().resolve():
        raise TalkingCraftError("Choose a dedicated skills directory, not filesystem root or home")
    if target.is_symlink():
        raise TalkingCraftError("Refusing to replace a symlink target")
    if target == source or target in source.parents or source in target.parents:
        raise TalkingCraftError("Install target must not overlap source repository")
    paths = [source / name for name in FILES]
    for name in DIRECTORIES:
        directory = source / name
        if not directory.is_dir():
            raise TalkingCraftError(f"Missing runtime directory: {directory}")
        paths.extend(p for p in directory.rglob("*") if p.is_file() and not any(part in EXCLUDED for part in p.relative_to(directory).parts) and p.suffix != ".pyc")
    for path in paths:
        if not path.is_file() or path.is_symlink() or source not in path.resolve().parents:
            raise TalkingCraftError(f"Missing or unsafe runtime file: {path}")
    relative = tuple(sorted(str(p.relative_to(source)) for p in paths))
    if config.dry_run:
        return InstallReport(target, relative, dry_run=True)
    if target.exists() and not config.force:
        raise TalkingCraftError("Target exists; inspect --dry-run then pass --force to back up and replace")
    parent.mkdir(parents=True, exist_ok=True)
    backup = None
    with tempfile.TemporaryDirectory(prefix=".talking-craft-install-", dir=parent) as temp:
        stage = Path(temp) / "skill"
        stage.mkdir()
        for name in relative:
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, destination)
        if not (stage / "SKILL.md").read_text().startswith("---"):
            raise TalkingCraftError("Invalid SKILL.md frontmatter")
        if target.exists():
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            backup = parent / f".ryan-talking-craft-backup-{stamp}"
            target.rename(backup)
        try:
            stage.rename(target)
        except OSError:
            if backup:
                backup.rename(target)
            raise
    return InstallReport(target, relative, backup)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, default=Path.home() / ".pi/agent/skills")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        report = install(InstallConfig(Path(__file__).resolve().parents[1], args.skills_dir, args.force, args.dry_run))
    except (TalkingCraftError, OSError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, **report.to_dict()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
