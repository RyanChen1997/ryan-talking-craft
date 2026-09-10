from pathlib import Path
import re

import pytest

from common import TalkingCraftError
from install_skill import InstallConfig, install

ROOT = Path(__file__).resolve().parents[1]


def test_install_is_whitelisted_and_safe(tmp_path: Path) -> None:
    report = install(InstallConfig(ROOT, tmp_path, dry_run=True))
    assert not report.target.exists()
    assert not any("preview/" in p or "node_modules" in p or "__pycache__" in p for p in report.files)
    result = install(InstallConfig(ROOT, tmp_path))
    assert (result.target / "assets/visual-kit/templates/diagram/data-chart/numbered-step-stack/Template.tsx").is_file()
    assert (result.target / "assets/visual-kit/templates/typography/emphasis/ink-underline/Template.tsx").is_file()
    assert (result.target / "assets/visual-kit/layouts/stage/Layout.tsx").is_file()
    assert not (result.target / "assets/visual-kit/layouts/presenter").exists()
    assert not (result.target / "assets/visual-kit/templates/typography/ordered-steps").exists()
    assert not (result.target / "assets/visual-kit/templates/typography/before-after").exists()
    assert not (result.target / "assets/visual-kit/gallery").exists()
    assert not (result.target / "preview").exists()
    assert not (result.target / "archive").exists()
    assert not (result.target / "references/legacy").exists()
    assert not (result.target / "assets/visual-kit/components").exists()
    assert not (result.target / "assets/visual-kit/registry.json").exists()
    assert (result.target / "scripts/project_plan.py").is_file()
    for source in (result.target / "assets/visual-kit").rglob("*.ts*"):
        for module in re.findall(r'''(?:from|import)\s*["'](\.[^"']+)["']''', source.read_text()):
            base = source.parent / module
            assert any(candidate.is_file() for candidate in (base, base.with_suffix(".ts"), base.with_suffix(".tsx"), base / "index.ts", base / "index.tsx")), (source, module)
    with pytest.raises(TalkingCraftError, match="exists"):
        install(InstallConfig(ROOT, tmp_path))
    (result.target / "user-file").write_text("retain in backup")
    replacement = install(InstallConfig(ROOT, tmp_path, force=True))
    assert replacement.backup is not None
    assert (replacement.backup / "user-file").read_text() == "retain in backup"


def test_refuses_overlapping_target() -> None:
    with pytest.raises(TalkingCraftError, match="overlap"):
        install(InstallConfig(ROOT, ROOT.parent, force=True))


def test_refuses_target_symlink(tmp_path: Path) -> None:
    (tmp_path / "ryan-talking-craft").symlink_to(ROOT, target_is_directory=True)
    with pytest.raises(TalkingCraftError, match="symlink"):
        install(InstallConfig(ROOT, tmp_path, force=True))
