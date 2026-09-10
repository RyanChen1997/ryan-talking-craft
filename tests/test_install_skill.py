from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _make_source(tmp_path: Path) -> Path:
    source = tmp_path / "source" / "ryan-talking-craft"
    source.mkdir(parents=True)
    shutil.copy2(ROOT / "install.sh", source / "install.sh")
    for directory in ("references", "scripts", "assets/visual-kit"):
        (source / directory).mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
    (source / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (source / "uv.lock").write_text("", encoding="utf-8")
    (source / "references/runtime.md").write_text("runtime", encoding="utf-8")
    (source / "scripts/run.py").write_text("print('ok')\n", encoding="utf-8")
    (source / "assets/visual-kit/index.ts").write_text("export {};\n", encoding="utf-8")
    (source / "references/.tmp").mkdir()
    (source / "references/.tmp/private.txt").write_text("private", encoding="utf-8")
    (source / "scripts/__pycache__").mkdir()
    (source / "scripts/__pycache__/run.pyc").write_bytes(b"cache")
    (source / "preview").mkdir()
    (source / "preview/dev.txt").write_text("dev", encoding="utf-8")
    return source


def _run(source: Path, skills_dir: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(source / "install.sh"), "--skills-dir", str(skills_dir), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def test_install_uses_top_level_whitelist_and_removes_caches(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    skills_dir = tmp_path / "skills"

    dry_run = _run(source, skills_dir, "--dry-run")
    assert dry_run.returncode == 0
    assert "SKILL.md" in dry_run.stdout and "assets/visual-kit" in dry_run.stdout
    assert not skills_dir.exists()

    result = _run(source, skills_dir)
    target = skills_dir / "ryan-talking-craft"
    assert result.returncode == 0, result.stderr
    assert (target / "SKILL.md").is_file()
    assert (target / "references/runtime.md").is_file()
    assert (target / "scripts/run.py").is_file()
    assert (target / "assets/visual-kit/index.ts").is_file()
    assert (target / "pyproject.toml").is_file()
    assert (target / "uv.lock").is_file()
    assert not (target / "preview").exists()
    assert not (target / "references/.tmp").exists()
    assert not (target / "scripts/__pycache__").exists()


def test_force_backs_up_existing_install(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    skills_dir = tmp_path / "skills"
    assert _run(source, skills_dir).returncode == 0
    target = skills_dir / "ryan-talking-craft"
    (target / "user-file").write_text("retain", encoding="utf-8")

    refused = _run(source, skills_dir)
    assert refused.returncode == 1
    assert "--force" in refused.stderr

    replaced = _run(source, skills_dir, "--force")
    assert replaced.returncode == 0, replaced.stderr
    backups = list(skills_dir.glob(".ryan-talking-craft-backup-*"))
    assert len(backups) == 1
    assert (backups[0] / "user-file").read_text(encoding="utf-8") == "retain"
    assert not (target / "user-file").exists()


def test_refuses_overlapping_target(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    result = _run(source, source.parent)
    assert result.returncode == 1
    assert "overlap" in result.stderr


def test_refuses_target_symlink(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "ryan-talking-craft").symlink_to(source, target_is_directory=True)

    result = _run(source, skills_dir, "--force")
    assert result.returncode == 1
    assert "symlink" in result.stderr


@pytest.mark.parametrize("argument", ["--unknown", "--skills-dir"])
def test_rejects_invalid_arguments(tmp_path: Path, argument: str) -> None:
    source = _make_source(tmp_path)
    result = subprocess.run(
        [str(source / "install.sh"), argument],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
