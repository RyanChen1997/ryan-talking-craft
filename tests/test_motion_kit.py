from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from compare_goldens import compare_goldens
from install_motion_kit import install_motion_kit

SKILL_ROOT = Path(__file__).resolve().parents[1]
MOTION_KIT = SKILL_ROOT / "archive/legacy/visual-kit"


def test_four_content_style_presets_are_complete_and_unique() -> None:
    preset_dir = MOTION_KIT / "presets"
    presets = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(preset_dir.glob("*.json"))
    ]

    assert len(presets) == 4
    assert {preset["content_type"] for preset in presets} == {
        "tutorial_demo",
        "tool_review_roundup",
        "pure_opinion",
        "news_fact_analysis",
    }
    assert len({preset["id"] for preset in presets}) == 4
    assert all(preset["template_priority"] for preset in presets)
    assert all(preset["qa_focus"] for preset in presets)
    assert all(preset["caption_policy"]["default"] == "enabled" for preset in presets)
    assert all(preset["media_layout_policy"]["forbid_unplanned_blank"] for preset in presets)
    assert all(preset["audio_policy"]["continuous_pts"] for preset in presets)


def test_registry_json_and_typescript_ids_match() -> None:
    registry = json.loads((MOTION_KIT / "registry.json").read_text(encoding="utf-8"))
    json_ids = {item["id"] for item in registry["templates"]}
    source = (MOTION_KIT / "registry.ts").read_text(encoding="utf-8")
    ts_ids = set(re.findall(r'id: "([A-Za-z][A-Za-z0-9]+@[0-9]+)"', source))

    assert json_ids == ts_ids


def test_semantic_motion_templates_are_registered() -> None:
    registry = json.loads((MOTION_KIT / "registry.json").read_text(encoding="utf-8"))
    templates = {item["id"]: item for item in registry["templates"]}

    assert registry["version"] == "0.6.0"
    for template_id in (
        "StateTransition@1",
        "LayerExplodeAssembly@1",
        "ProgressiveList@1",
        "ProgressiveChecklist@1",
        "DataLineStory@1",
        "DataScatterStory@1",
        "EvidenceFocusSequence@1",
    ):
        assert templates[template_id]["status"] == "stable"
        assert templates[template_id]["motionMode"] == "semantic_sequence"
        assert templates[template_id]["motionRoles"]

    assert templates["TwoColorCompare@1"]["motionMode"] == "entrance_only"


def test_default_caption_and_media_safety_components_are_bundled() -> None:
    caption = MOTION_KIT / "components/CaptionOverlay.tsx"
    evidence = (MOTION_KIT / "components/EvidenceFocusSequence.tsx").read_text(
        encoding="utf-8"
    )

    assert caption.is_file()
    assert "clampCameraTranslation" in evidence
    assert 'mediaMatte ?? "#15171C"' in evidence


def test_installer_does_not_overwrite_conflicts(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    existing = tmp_path / "src/motion-library/tokens.ts"
    existing.parent.mkdir(parents=True)
    existing.write_text("// user change\n", encoding="utf-8")

    result = install_motion_kit(tmp_path, source_dir=MOTION_KIT)

    assert "tokens.ts" in result.conflicts
    assert existing.read_text(encoding="utf-8") == "// user change\n"
    assert (tmp_path / "src/motion-library/index.ts").is_file()


def test_golden_comparison_accepts_identical_images(tmp_path: Path) -> None:
    manifest = MOTION_KIT / "golden-manifest.json"
    actual_dir = tmp_path / "actual"
    actual_dir.mkdir()
    for golden in (MOTION_KIT / "golden-frames").glob("*.png"):
        shutil.copy2(golden, actual_dir / golden.name)

    results = compare_goldens(manifest, actual_dir)

    assert results
    assert all(result.passed for result in results)
