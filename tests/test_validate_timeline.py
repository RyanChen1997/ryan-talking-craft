from __future__ import annotations

import json
from pathlib import Path

from validate_timeline import validate_timeline

REGISTRY = Path(__file__).resolve().parents[1] / "archive/legacy/visual-kit/registry.json"


def test_valid_timeline_passes(tmp_path: Path) -> None:
    timeline = _base_timeline()
    timeline_path = _write_json(tmp_path / "timeline.json", timeline)

    report = validate_timeline(timeline_path, registry_path=REGISTRY)

    assert report.passed is True
    assert report.issue_count == 0


def test_gap_and_second_audible_track_fail(tmp_path: Path) -> None:
    timeline = _base_timeline()
    timeline["segments"][1]["start_frame"] = 61
    timeline["audio"] = [timeline["audio"], {**timeline["audio"], "asset_id": "A099"}]
    timeline_path = _write_json(tmp_path / "timeline.json", timeline)

    report = validate_timeline(timeline_path, registry_path=REGISTRY)

    categories = {issue.category for issue in report.issues}
    assert report.passed is False
    assert "timing_gap" in categories
    assert "audio" in categories


def test_missing_caption_policy_is_blocked(tmp_path: Path) -> None:
    timeline = _base_timeline()
    timeline.pop("captions")
    timeline_path = _write_json(tmp_path / "timeline.json", timeline)

    report = validate_timeline(timeline_path, registry_path=REGISTRY)

    assert report.passed is False
    assert any(issue.category == "captions_missing" for issue in report.issues)


def test_enabled_caption_json_is_validated(tmp_path: Path) -> None:
    public = tmp_path / "public"
    public.mkdir()
    _write_json(
        public / "captions.json",
        [
            {
                "text": "默认字幕",
                "startMs": 0,
                "endMs": 2000,
                "timestampMs": None,
                "confidence": None,
            }
        ],
    )
    timeline = _base_timeline()
    timeline["captions"] = {
        "enabled": True,
        "asset_id": "A003",
        "runtime_path": "captions.json",
        "format": "caption-json",
        "placement": "bottom-safe",
        "max_lines": 2,
        "style_preset": "clean-talking-head",
    }
    manifest = {
        "assets": [
            {
                "asset_id": "A003",
                "type": "caption_json",
                "status": "ready",
                "runtime_path": "captions.json",
            }
        ]
    }
    timeline_path = _write_json(tmp_path / "timeline.json", timeline)
    manifest_path = _write_json(tmp_path / "assets.json", manifest)

    report = validate_timeline(
        timeline_path,
        registry_path=REGISTRY,
        asset_manifest_path=manifest_path,
        public_root=public,
    )

    assert report.passed is True


def test_complete_asset_requires_full_source_duration(tmp_path: Path) -> None:
    timeline = _base_timeline()
    timeline["segments"] = [
        {
            "segment_id": "S001",
            "start_frame": 0,
            "duration_in_frames": 119,
            "template": "ScreenDemo@1",
            "presenter_mode": "HIDDEN",
            "asset_ids": ["A001"],
            "props": {},
            "source_trim": {"start_frame": 1},
        }
    ]
    timeline["composition"]["duration_in_frames"] = 119
    timeline["audio"]["duration_in_frames"] = 119
    manifest = {
        "schema_version": 1,
        "assets": [
            {
                "asset_id": "A001",
                "status": "ready",
                "playback": "complete",
                "duration_seconds": 4.0,
                "runtime_path": "demo.mp4",
            }
        ],
    }
    timeline_path = _write_json(tmp_path / "timeline.json", timeline)
    manifest_path = _write_json(tmp_path / "assets.json", manifest)

    report = validate_timeline(
        timeline_path,
        registry_path=REGISTRY,
        asset_manifest_path=manifest_path,
    )

    assert report.passed is False
    assert any(issue.category == "complete_playback" for issue in report.issues)


def _base_timeline() -> dict[str, object]:
    return {
        "schema_version": 1,
        "composition": {
            "id": "Demo",
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "duration_in_frames": 120,
        },
        "audio": {
            "asset_id": "A000",
            "start_frame": 0,
            "duration_in_frames": 120,
            "audible": True,
        },
        "captions": {
            "enabled": False,
            "explicit_user_request": True,
            "opt_out_reason": "Test fixture explicitly requests no captions",
        },
        "segments": [
            {
                "segment_id": "S001",
                "start_frame": 0,
                "duration_in_frames": 60,
                "template": "KeywordOverlay@1",
                "presenter_mode": "MEDIUM",
                "asset_ids": [],
                "props": {},
            },
            {
                "segment_id": "S002",
                "start_frame": 60,
                "duration_in_frames": 60,
                "template": "EndCard@1",
                "presenter_mode": "MEDIUM",
                "asset_ids": [],
                "props": {},
            },
        ],
    }


def _write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path
