from __future__ import annotations

import json
from pathlib import Path

import pytest

from bootstrap_spec import BootstrapConfig, bootstrap_spec
from common import TalkingCraftError, write_json
from project_plan import advance, export_reviews, initialize, load_project, validate


@pytest.fixture
def spec(tmp_path: Path) -> Path:
    initialize(tmp_path, "demo", "演示")
    project = load_project(tmp_path)
    project.plan.update(duration_frames=300, segments=[{"id": "s1", "from": 0, "to": 300, "meaning": "真实演示", "screen_text": ["一次生成"], "asset_ids": ["demo"]}])
    project.assets["assets"] = [{"id": "demo", "kind": "user_recording", "provider": "user", "purpose": "操作", "status": "missing", "recording_request": {"content": "输入后点击生成，等待结果", "record_seconds": 18, "use_seconds": 10}}]
    write_json(tmp_path / "plan.json", project.plan)
    write_json(tmp_path / "assets.json", project.assets)
    return tmp_path


def test_bootstrap_v2_is_minimal_and_idempotent(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"dependencies":{"remotion":"4"}}')
    first = bootstrap_spec(BootstrapConfig(tmp_path, "demo", "演示"))
    second = bootstrap_spec(BootstrapConfig(tmp_path, "demo", "演示"))
    assert first.spec_dir == second.spec_dir
    assert not second.created
    assert {p.name for p in first.spec_dir.iterdir()} == {"plan.json", "assets.json", "state.json", "qa"}
    plan = json.loads((first.spec_dir / "plan.json").read_text())
    assert plan["output"] == {"width": 1920, "height": 1080}


def test_explicit_approval_and_no_skipping(spec: Path) -> None:
    with pytest.raises(TalkingCraftError):
        advance(spec, "BUILDING", "同意")
    advance(spec, "CONTENT_REVIEW")
    with pytest.raises(TalkingCraftError, match="Explicit"):
        advance(spec, "ACQUIRING_ASSETS")
    advance(spec, "ACQUIRING_ASSETS", "确认内容，我来录制")
    with pytest.raises(TalkingCraftError, match="not ready"):
        advance(spec, "VISUAL_REVIEW")


def test_content_change_invalidates_approval(spec: Path) -> None:
    advance(spec, "CONTENT_REVIEW")
    advance(spec, "ACQUIRING_ASSETS", "同意")
    project = load_project(spec)
    project.plan["segments"][0]["screen_text"] = ["另一个结论"]
    write_json(spec / "plan.json", project.plan)
    with pytest.raises(TalkingCraftError, match="Content changed"):
        advance(spec, "VISUAL_REVIEW")


@pytest.mark.parametrize("bad", [{"fit": "cover"}, {"zoom": 1.2}, {"crop": [0, 0, 1, 1]}])
def test_recording_spatial_changes_rejected(spec: Path, bad: dict) -> None:
    project = load_project(spec)
    project.plan["segments"][0]["visual"] = {"layout": "screen-full@1", "clips": [{"asset_id": "demo", "source_in": 0, "source_out": 10, **bad}]}
    assert any("uncropped" in error for error in validate(project, True))


def test_reviews_show_recording_durations(spec: Path) -> None:
    export_reviews(spec)
    text = (spec / "content-review.md").read_text()
    assert "18 秒" in text and "10 秒" in text and "输入后点击生成" in text
    visual = (spec / "visual-review.md").read_text()
    assert "画幅：1920×1080（16:9，默认）" in visual
    assert "背景：perspective-grid@1" in visual
    assert "配色：" in visual


def test_visual_requires_positive_output_dimensions(spec: Path) -> None:
    project = load_project(spec)
    project.plan["output"] = {"width": 0, "height": 1080}
    assert any("output.width" in error for error in validate(project, True))


def test_visual_requires_palette(spec: Path) -> None:
    project = load_project(spec)
    project.plan["segments"][0]["visual"] = {"layout": "screen-full@1", "clips": [{"asset_id": "demo", "source_in": 0, "source_out": 10}]}
    project.assets["assets"][0].update(status="ready", duration_seconds=20)
    assert any("palette required" in error for error in validate(project, True))


def test_ready_update_does_not_invalidate_content(spec: Path) -> None:
    advance(spec, "CONTENT_REVIEW")
    advance(spec, "ACQUIRING_ASSETS", "同意")
    p = load_project(spec)
    p.assets["assets"][0].update(status="ready", duration_seconds=20)
    p.plan["segments"][0]["visual"] = {"layout": "screen-pip-right@1", "clips": [{"asset_id": "demo", "source_in": 2, "source_out": 12}]}
    p.plan["palette"] = "grid-hud-cyan@1"
    write_json(spec / "assets.json", p.assets)
    write_json(spec / "plan.json", p.plan)
    advance(spec, "VISUAL_REVIEW")
    advance(spec, "BUILDING", "画面方案确认")
    with pytest.raises(TalkingCraftError, match="production.json"):
        advance(spec, "PREVIEW_REVIEW")


def test_no_silent_legacy_migration(tmp_path: Path) -> None:
    (tmp_path / "project.yaml").write_text("schema_version: 1")
    with pytest.raises(TalkingCraftError, match="Legacy"):
        initialize(tmp_path, "demo", "旧项目")
