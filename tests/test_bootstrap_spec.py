from __future__ import annotations

import json
from pathlib import Path

from bootstrap_spec import BootstrapConfig, bootstrap_spec


def test_bootstrap_creates_only_spec_slug_directory(tmp_path: Path) -> None:
    _write_remotion_package(tmp_path)

    result = bootstrap_spec(
        BootstrapConfig(
            root=tmp_path, slug="Editable Design", title="Editable Design 工具介绍", legacy=True
        )
    )

    assert result.slug == "editable-design"
    assert (tmp_path / "spec/editable-design/project.yaml").is_file()
    assert (
        tmp_path / "spec/editable-design/02-analysis/representative-frames"
    ).is_dir()
    assert not (tmp_path / "src/editable-design").exists()
    assert not (tmp_path / "public/editable-design").exists()
    project_text = (result.spec_dir / "project.yaml").read_text(encoding="utf-8")
    assert "captions:\n  render: true" in project_text
    state = json.loads((result.spec_dir / "state.json").read_text(encoding="utf-8"))
    assert state["status"] == "INTAKE"


def test_bootstrap_reuses_same_title_and_resolves_collision(tmp_path: Path) -> None:
    _write_remotion_package(tmp_path)
    first = bootstrap_spec(BootstrapConfig(tmp_path, "demo", "First"))
    same = bootstrap_spec(BootstrapConfig(tmp_path, "demo", "First"))
    different = bootstrap_spec(BootstrapConfig(tmp_path, "demo", "Second"))

    assert first.spec_dir == same.spec_dir
    assert same.created is False
    assert different.spec_dir != first.spec_dir
    assert different.spec_dir.name.startswith("demo-")


def _write_remotion_package(root: Path) -> None:
    (root / "package.json").write_text(
        json.dumps({"dependencies": {"remotion": "4.0.512"}}), encoding="utf-8"
    )
