from __future__ import annotations

import json
from pathlib import Path

from run_visual_qa import run_visual_qa


def test_visual_qa_detects_overflow_and_collision(tmp_path: Path) -> None:
    snapshot = {
        "canvas": {"width": 1920, "height": 1080},
        "frames": [
            {
                "frame": 30,
                "elements": [
                    {
                        "id": "title",
                        "role": "title",
                        "rect": {"x": 100, "y": 100, "width": 500, "height": 100},
                        "scroll_width": 550,
                        "scroll_height": 100,
                        "client_width": 500,
                        "client_height": 100,
                        "font_size": 64,
                        "contrast_ratio": 7,
                        "avoid_roles": ["face"],
                    },
                    {
                        "id": "face",
                        "role": "face",
                        "rect": {"x": 450, "y": 80, "width": 500, "height": 900},
                    },
                ],
            }
        ],
    }
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")

    report = run_visual_qa(path)

    categories = {issue.category for issue in report.issues}
    assert report.passed is False
    assert "text_overflow" in categories
    assert "layout_collision" in categories


def test_visual_qa_blocks_contain_without_empty_space_strategy(
    tmp_path: Path,
) -> None:
    snapshot = {
        "canvas": {"width": 1920, "height": 1080},
        "frames": [
            {
                "frame": 30,
                "elements": [
                    {
                        "id": "media",
                        "role": "main-media",
                        "rect": {"x": 100, "y": 100, "width": 1200, "height": 700},
                        "media_fit": "contain",
                        "empty_space_strategy": "none",
                        "camera_bounds_clamped": True,
                        "intrinsic_width": 1080,
                        "intrinsic_height": 1920,
                    }
                ],
            }
        ],
    }
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")

    report = run_visual_qa(path)

    categories = {issue.category for issue in report.issues}
    assert report.passed is False
    assert "unplanned_letterbox" in categories
    assert "large_letterbox_area" in categories


def test_visual_qa_accepts_safe_layout(tmp_path: Path) -> None:
    snapshot = {
        "canvas": {"width": 1920, "height": 1080},
        "frames": [
            {
                "frame": 30,
                "elements": [
                    {
                        "id": "title",
                        "role": "title",
                        "rect": {"x": 100, "y": 100, "width": 500, "height": 100},
                        "scroll_width": 500,
                        "scroll_height": 100,
                        "client_width": 500,
                        "client_height": 100,
                        "font_size": 64,
                        "contrast_ratio": 7,
                        "avoid_roles": ["face"],
                    },
                    {
                        "id": "face",
                        "role": "face",
                        "rect": {"x": 1300, "y": 80, "width": 500, "height": 900},
                    },
                ],
            }
        ],
    }
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")

    report = run_visual_qa(path)

    assert report.passed is True
