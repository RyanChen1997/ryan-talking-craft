from __future__ import annotations

import json
from pathlib import Path

from validate_design import validate_design


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _valid_design(tmp_path: Path) -> tuple[Path, Path, Path]:
    function_map = {
        "modules": [
            {
                "function_id": "F001",
                "segment_ids": ["S001"],
                "start_ms": 0,
                "end_ms": 1000,
                "asset_ids": ["A001"],
            }
        ]
    }
    storyboard = {
        "audio": {"asset_id": "A002"},
        "shots": [
            {
                "shot_id": "SH001",
                "segment_ids": ["S001"],
                "start_ms": 0,
                "end_ms": 1000,
                "asset_ids": ["A001"],
            }
        ],
    }
    manifest = {
        "assets": [
            {"asset_id": "A001", "required": True, "status": "ready"},
            {"asset_id": "A002", "required": True, "status": "ready"},
        ]
    }
    return (
        _write_json(tmp_path / "function-map.json", function_map),
        _write_json(tmp_path / "storyboard.json", storyboard),
        _write_json(tmp_path / "asset-manifest.json", manifest),
    )


def test_validate_design_accepts_linked_assets(tmp_path: Path) -> None:
    report = validate_design(*_valid_design(tmp_path))

    assert report.passed is True
    assert report.issues == ()


def test_validate_design_rejects_dangling_function_asset(tmp_path: Path) -> None:
    function_path, storyboard_path, manifest_path = _valid_design(tmp_path)
    function_map = json.loads(function_path.read_text(encoding="utf-8"))
    function_map["modules"][0]["asset_ids"].append("A003")
    function_path = _write_json(function_path, function_map)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"].append(
        {"asset_id": "A003", "required": False, "status": "ready"}
    )
    manifest_path = _write_json(manifest_path, manifest)

    report = validate_design(function_path, storyboard_path, manifest_path)

    assert report.passed is False
    assert any(issue.category == "dangling_function_asset" for issue in report.issues)


def test_validate_design_blocks_media_without_layout_plan(tmp_path: Path) -> None:
    function_path, storyboard_path, manifest_path = _valid_design(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"][0].update(
        {"type": "screen_recording", "allow_crop": True}
    )
    manifest_path = _write_json(manifest_path, manifest)

    report = validate_design(function_path, storyboard_path, manifest_path)

    assert report.passed is False
    assert any(issue.category == "media_layout_missing" for issue in report.issues)


def test_validate_design_blocks_unplanned_contain_letterbox(tmp_path: Path) -> None:
    function_path, storyboard_path, manifest_path = _valid_design(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"][0].update(
        {"type": "screenshot", "allow_crop": True}
    )
    manifest_path = _write_json(manifest_path, manifest)
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    storyboard["shots"][0]["media_layout"] = {
        "fit": "contain",
        "empty_space_strategy": "none",
        "camera_bounds_clamped": True,
        "blank_space_reason": None,
    }
    storyboard_path = _write_json(storyboard_path, storyboard)

    report = validate_design(function_path, storyboard_path, manifest_path)

    categories = {issue.category for issue in report.issues}
    assert report.passed is False
    assert "unplanned_letterbox" in categories
    assert "blank_space_reason" in categories


def test_validate_design_allows_focus_crop_with_explicit_region(
    tmp_path: Path,
) -> None:
    function_path, storyboard_path, manifest_path = _valid_design(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"][0].update(
        {"type": "screen_recording", "allow_crop": True}
    )
    manifest_path = _write_json(manifest_path, manifest)
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    storyboard["shots"][0]["media_layout"] = {
        "fit": "focus_crop",
        "focal_region": {"x": 0.1, "y": 0.2, "width": 0.8, "height": 0.6},
        "empty_space_strategy": "none",
        "camera_bounds_clamped": True,
        "blank_space_reason": None,
    }
    storyboard_path = _write_json(storyboard_path, storyboard)

    report = validate_design(function_path, storyboard_path, manifest_path)

    assert report.passed is True


def test_validate_design_allows_explicit_backup_asset(tmp_path: Path) -> None:
    function_path, storyboard_path, manifest_path = _valid_design(tmp_path)
    function_map = json.loads(function_path.read_text(encoding="utf-8"))
    function_map["modules"][0]["asset_ids"].append("A003")
    function_map["modules"][0]["backup_asset_ids"] = ["A003"]
    function_path = _write_json(function_path, function_map)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"].append(
        {"asset_id": "A003", "required": False, "status": "ready"}
    )
    manifest_path = _write_json(manifest_path, manifest)

    report = validate_design(function_path, storyboard_path, manifest_path)

    assert report.passed is True
