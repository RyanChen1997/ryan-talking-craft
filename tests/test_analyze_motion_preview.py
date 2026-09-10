from __future__ import annotations

from analyze_motion_preview import MotionFrame, evaluate_motion_samples


def _frames(values: list[int], sample_fps: float = 10.0) -> list[MotionFrame]:
    result: list[MotionFrame] = []
    previous: bytes | None = None
    for index, value in enumerate(values):
        pixels = bytes([value] * 16)
        delta = (
            0.0
            if previous is None
            else sum(abs(a - b) for a, b in zip(previous, pixels, strict=True))
            / len(pixels)
        )
        result.append(MotionFrame(index / sample_fps, pixels, delta))
        previous = pixels
    return result


def _plan() -> dict[str, object]:
    return {
        "role": "bad_to_better",
        "initial_state": "旧状态",
        "beats": [
            {"at_frame": 12, "action": "建立问题", "purpose": "显示旧态"},
            {"at_frame": 30, "action": "变成新态", "purpose": "显示改善"},
        ],
        "final_state": "新状态",
        "removal_cost": "看不见改善过程",
        "hold_frames": 15,
    }


def test_rendered_beats_and_static_completion_hold_pass() -> None:
    frames = _frames([0, 0, 0, 0, 50, 50, 50, 50, 50, 50, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100])

    report = evaluate_motion_samples(
        frames,
        _plan(),
        sample_fps=10,
        timeline_fps=30,
        difference_threshold=10,
        beat_window_seconds=0.15,
    )

    assert report.passed is True
    assert report.active_ratio < 0.2
    assert report.longest_static_seconds >= 0.8


def test_static_preview_fails_semantic_motion() -> None:
    report = evaluate_motion_samples(
        _frames([0] * 20),
        _plan(),
        sample_fps=10,
        timeline_fps=30,
        difference_threshold=10,
        beat_window_seconds=0.15,
    )

    assert report.passed is False
    categories = {issue.category for issue in report.issues}
    assert "underanimated_preview" in categories
    assert "beat_without_rendered_motion" in categories
    assert "unchanged_final_state" in categories


def test_continuous_motion_is_flagged_for_review() -> None:
    plan = _plan() | {"allow_return_to_initial": True, "hold_frames": 0}
    report = evaluate_motion_samples(
        _frames([0, 30] * 10),
        plan,
        sample_fps=10,
        timeline_fps=30,
        difference_threshold=10,
        beat_window_seconds=0.15,
    )

    assert any(issue.category == "overanimated_preview" for issue in report.issues)
