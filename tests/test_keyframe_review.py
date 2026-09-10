from __future__ import annotations

from pathlib import Path

import pytest
from build_keyframe_review import (
    KeyframeRequest,
    KeyframeTile,
    _collect_issues,
    _plan_duration_delta,
    select_keyframes,
)
from common import TalkingCraftError


def _plan(segments: list[dict[str, object]]) -> dict[str, object]:
    return {"duration_frames": 300, "segments": segments}


def _segment(segment_id: str, start: int, end: int) -> dict[str, object]:
    return {
        "id": segment_id,
        "from": start,
        "to": end,
        "screen_text": ["上屏文字一", "上屏文字二"],
        "visual": {
            "layout": "whiteboard-pip-right@1",
            "template": "outline-box-title@1",
            "beats": "先出标题",
        },
    }


def test_one_keyframe_per_segment_lands_near_completion() -> None:
    requests = select_keyframes(_plan([_segment("s1", 0, 100)]), completion_ratio=0.85)

    assert [request.frame for request in requests] == [84]
    assert requests[0].segment_id == "s1"
    assert requests[0].seconds == pytest.approx(2.8)


def test_each_segment_is_covered_once() -> None:
    plan = _plan([_segment("s1", 0, 100), _segment("s2", 100, 200)])

    requests = select_keyframes(plan)

    assert [request.segment_id for request in requests] == ["s1", "s2"]
    assert all(request.frame < 200 for request in requests)


def test_per_segment_samples_multiple_points() -> None:
    requests = select_keyframes(_plan([_segment("s1", 0, 300)]), per_segment=3)

    assert [request.frame for request in requests] == [75, 150, 224]


def test_include_boundaries_prepends_segment_start() -> None:
    requests = select_keyframes(
        _plan([_segment("s1", 60, 160)]), include_boundaries=True
    )

    assert [request.frame for request in requests] == [60, 144]


def test_expected_content_is_carried_for_review() -> None:
    request = select_keyframes(_plan([_segment("s7", 0, 100)]))[0]

    assert request.screen_text == ("上屏文字一", "上屏文字二")
    assert request.template == "outline-box-title@1"
    assert request.layout == "whiteboard-pip-right@1"
    assert request.beats == "先出标题"


def test_segment_without_visual_still_gets_a_keyframe() -> None:
    plan = _plan([{"id": "s9", "from": 0, "to": 100, "screen_text": []}])

    request = select_keyframes(plan)[0]

    assert request.layout is None
    assert request.template is None
    assert request.screen_text == ()


@pytest.mark.parametrize("per_segment", [0, -1])
def test_invalid_per_segment_is_rejected(per_segment: int) -> None:
    with pytest.raises(TalkingCraftError):
        select_keyframes(_plan([_segment("s1", 0, 100)]), per_segment=per_segment)


@pytest.mark.parametrize("ratio", [0.0, 1.5])
def test_invalid_completion_ratio_is_rejected(ratio: float) -> None:
    with pytest.raises(TalkingCraftError):
        select_keyframes(_plan([_segment("s1", 0, 100)]), completion_ratio=ratio)


def test_plan_without_segments_is_rejected() -> None:
    with pytest.raises(TalkingCraftError):
        select_keyframes({"segments": []})


@pytest.mark.parametrize(("start", "end"), [(100, 100), (200, 100), ("0", 100)])
def test_segment_needs_ordered_integral_frames(start: object, end: int) -> None:
    with pytest.raises(TalkingCraftError):
        select_keyframes(_plan([{"id": "s1", "from": start, "to": end}]))


def test_plan_duration_delta_measures_drift() -> None:
    assert _plan_duration_delta({"duration_frames": 300}, 300) == 0
    assert _plan_duration_delta({"duration_frames": 300}, 512) == 212

    with pytest.raises(TalkingCraftError):
        _plan_duration_delta({}, 300)


def _tile(segment_id: str, edge_status: str, detail: str | None = None) -> KeyframeTile:
    return KeyframeTile(
        request=KeyframeRequest(
            segment_id=segment_id,
            frame=10,
            seconds=0.333,
            layout=None,
            template=None,
            screen_text=(),
            beats="",
        ),
        image=Path(f"/tmp/{segment_id}.jpg"),
        sheet=Path("/tmp/keyframes-1.jpg"),
        edge_status=edge_status,
        edge_detail=detail,
    )


def test_matching_render_and_clean_edges_pass() -> None:
    assert _collect_issues((_tile("s1", "ok"),), duration_delta=0) == []


def test_render_drift_blocks() -> None:
    issues = _collect_issues((_tile("s1", "ok"),), duration_delta=30)

    assert [issue.category for issue in issues] == ["render_does_not_match_plan"]
    assert issues[0].severity == "blocked"


def test_flagged_edge_blocks() -> None:
    issues = _collect_issues((_tile("s1", "flagged", "top 3.2%"),), duration_delta=0)

    assert [issue.category for issue in issues] == ["content_at_frame_edge"]
    assert "top 3.2%" in issues[0].message
