from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from analyze_frame_signal import (
    ContinuityConfig,
    EdgeContentConfig,
    FrameScan,
    MotionInterval,
    MotionProfile,
    MotionProfileConfig,
    analyze_declared_windows,
    analyze_edge_content,
    evaluate_continuity,
    evaluate_motion_profile,
)
from common import TalkingCraftError
from PIL import Image

STABLE = 150.0


def _scan(means: list[float], *, sampled_fps: float = 30.0) -> FrameScan:
    deltas = [0.0] + [
        abs(means[index] - means[index - 1]) for index in range(1, len(means))
    ]
    return FrameScan(
        sampled_fps=sampled_fps,
        decoded_width=64,
        decoded_height=36,
        means=tuple(means),
        deltas=tuple(deltas),
    )


def _fade_in_scan() -> FrameScan:
    """A bright frame followed by an eight-frame fade from black, as a broken cut looks."""
    return _scan(
        [STABLE] * 30
        + [0.0, 19.6, 39.1, 58.7, 78.2, 97.7, 117.8, 137.2]
        + [STABLE] * 30
    )


def _profile(
    duration: float = 60.0, intervals: tuple[MotionInterval, ...] = ()
) -> MotionProfile:
    return MotionProfile(
        video_path=Path("unused.mp4"),
        duration_seconds=duration,
        sampled_fps=30.0,
        decoded_width=64,
        decoded_height=36,
        frames=int(duration * 30),
        median_delta=0.1,
        peak_delta=max((item.peak_delta for item in intervals), default=0.0),
        high_motion_intervals=intervals,
        static_intervals=((0.0, duration),),
        per_second_peak=(),
    )


def test_stable_frames_pass_continuity() -> None:
    report = evaluate_continuity(_scan([STABLE] * 40))

    assert report.passed
    assert report.outliers == ()
    assert report.dark_frame_ratio == 0.0


def test_fade_in_inside_segment_is_blocked() -> None:
    report = evaluate_continuity(_fade_in_scan())

    kinds = {outlier.kind for outlier in report.outliers}
    assert report.passed is False
    assert "luminance_dip" in kinds
    assert "blocked" in {issue.severity for issue in report.issues}


def test_fade_in_at_segment_boundary_is_expected() -> None:
    report = evaluate_continuity(_fade_in_scan(), cut_frames=(30,))

    assert all(
        outlier.at_segment_boundary for outlier in report.outliers if outlier.frame < 33
    )
    assert report.passed is False
    assert [issue.subject for issue in report.issues] == ["frame 33", "frame 34"]


def test_accepted_frames_suppress_blocking_issues() -> None:
    accepted = frozenset(range(30, 48))
    report = evaluate_continuity(_fade_in_scan(), accepted_frames=accepted)

    assert report.passed
    assert report.issues == ()
    assert report.accepted_frames == tuple(sorted(accepted))


def test_black_frame_is_reported() -> None:
    report = evaluate_continuity(_scan([STABLE] * 20 + [0.0, 0.0, 0.0] + [STABLE] * 20))

    assert report.passed is False
    assert report.dark_frame_ratio > 0
    assert "black_frame" in {outlier.kind for outlier in report.outliers}


@pytest.mark.parametrize(
    ("dipped", "expected_severity", "expected_passed"),
    [(50.0, "blocked", False), (120.0, "needs_review", True)],
)
def test_luminance_severity_scales_with_relative_depth(
    dipped: float, expected_severity: str, expected_passed: bool
) -> None:
    report = evaluate_continuity(_scan([STABLE] * 20 + [dipped, dipped, dipped] + [STABLE] * 20))

    assert report.passed is expected_passed
    luminance_issues = [
        issue for issue in report.issues if issue.category.startswith("luminance_")
    ]
    assert {issue.severity for issue in luminance_issues} == {expected_severity}


def test_deep_transient_at_segment_boundary_is_still_exempted() -> None:
    report = evaluate_continuity(
        _scan([STABLE] * 20 + [5.0, 5.0, 5.0] + [STABLE] * 20), cut_frames=(21,)
    )

    assert all(
        outlier.at_segment_boundary
        for outlier in report.outliers
        if outlier.frame <= 23
    )


def test_motion_spike_needs_review_but_passes() -> None:
    # A step small enough to stay inside luminance tolerance but far above the local motion floor.
    means = [STABLE] * 20 + [STABLE + 5] + [STABLE + 5] * 20
    report = evaluate_continuity(_scan(means))

    assert report.passed
    assert [issue.severity for issue in report.issues] == ["needs_review"]
    assert report.issues[0].category == "motion_spike_inside_segment"


def test_continuity_config_rejects_invalid_window() -> None:
    with pytest.raises(TalkingCraftError):
        evaluate_continuity(
            _fade_in_scan(), config=ContinuityConfig(transient_window_frames=0)
        )


def test_motion_profile_classifies_jump_fast_and_static() -> None:
    report = evaluate_motion_profile(
        _scan(
            [STABLE] * 30
            + [STABLE + 60]
            + [STABLE] * 30
            + [STABLE + 20]
            + [STABLE] * 30
        ),
        Path("source.mp4"),
        4.0,
    )

    levels = [
        (item.level, round(item.start_seconds, 3))
        for item in report.high_motion_intervals
    ]
    assert levels == [("jump", 1.0), ("fast", 2.033)]
    assert report.peak_delta == 60.0
    assert report.static_intervals[0] == (0.0, 1.0)


def test_motion_profile_rejects_inverted_thresholds() -> None:
    with pytest.raises(TalkingCraftError):
        evaluate_motion_profile(
            _scan([STABLE] * 4),
            Path("source.mp4"),
            1.0,
            config=MotionProfileConfig(fast_threshold=50.0, jump_threshold=10.0),
        )


def _write_edge_image(path: Path, *, edge: int, center: int, size: int = 40) -> None:
    image = Image.new("L", (size, size), center)
    last = size - 1
    for index in range(size):
        for offset in (0, 1, last - 1, last):
            image.putpixel((index, offset), edge)
            image.putpixel((offset, index), edge)
    image.save(path)


def test_bright_frame_edge_is_blocked(tmp_path: Path) -> None:
    path = tmp_path / "edge.png"
    _write_edge_image(path, edge=250, center=10)

    report = analyze_edge_content((path,))

    assert report.passed is False
    assert {issue.subject.split()[-1] for issue in report.issues} == {
        "top",
        "bottom",
        "left",
        "right",
    }


def test_dark_frame_edge_passes(tmp_path: Path) -> None:
    path = tmp_path / "clean.png"
    _write_edge_image(path, edge=5, center=200)

    report = analyze_edge_content((path,), config=EdgeContentConfig(strip_pixels=2))

    assert report.passed
    assert report.frames[0].strips[0].max_luminance == 5


def test_full_bleed_light_background_passes(tmp_path: Path) -> None:
    """整幅铺满的浅色舞台：四边全是背景色，不能被当成内容切边。"""
    path = tmp_path / "full-bleed-light.png"
    Image.new("L", (320, 180), 249).save(path)

    report = analyze_edge_content((path,))

    assert report.passed
    assert all(strip.flat for strip in report.frames[0].strips)
    assert all(strip.max_luminance == 249 for strip in report.frames[0].strips)


def test_dark_content_on_light_background_is_blocked(tmp_path: Path) -> None:
    """浅色背景下，被边缘切掉的深色内容仍然要报出来。"""
    path = tmp_path / "light-with-content.png"
    image = Image.new("L", (320, 180), 249)
    for x in range(140, 180):
        for y in range(0, 40):
            image.putpixel((x, y), 20)
    image.save(path)

    report = analyze_edge_content((path,))

    assert report.passed is False
    assert {issue.subject.split()[-1] for issue in report.issues} == {"top"}


def test_edge_tolerates_single_bright_pixel(tmp_path: Path) -> None:
    path = tmp_path / "stray.png"
    _write_edge_image(path, edge=0, center=200, size=200)
    with Image.open(path) as opened:
        image = opened.convert("L")
    image.putpixel((20, 0), 255)
    image.save(path)

    report = analyze_edge_content((path,), config=EdgeContentConfig(strip_pixels=2))

    assert report.passed


def test_edge_config_rejects_invalid_threshold(tmp_path: Path) -> None:
    path = tmp_path / "clean.png"
    _write_edge_image(path, edge=5, center=200)

    with pytest.raises(TalkingCraftError):
        analyze_edge_content((path,), config=EdgeContentConfig(luminance_threshold=300))


def _write_plan(path: Path, windows: list[tuple[str, str, float, float]]) -> None:
    segments = [
        {
            "id": segment_id,
            "visual": {
                "clips": [
                    {
                        "asset_id": asset_id,
                        "source_in": source_in,
                        "source_out": source_out,
                    }
                ]
            },
        }
        for segment_id, asset_id, source_in, source_out in windows
    ]
    payload = {"schema_version": 2, "segments": [{"id": "s1"}, *segments]}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_assets(path: Path, entries: dict[str, str]) -> None:
    payload = {
        "schema_version": 2,
        "assets": [{"id": key, "path": value} for key, value in entries.items()],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _stub_profile(monkeypatch: pytest.MonkeyPatch, profile: MotionProfile) -> None:
    monkeypatch.setattr(
        "analyze_frame_signal.sample_motion_profile",
        lambda path, **_kwargs: replace(profile, video_path=path),
    )


def test_window_without_jump_is_clear(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "site.mp4").write_bytes(b"stub")
    plan, assets = tmp_path / "plan.json", tmp_path / "assets.json"
    _write_plan(plan, [("s2", "site", 0.0, 5.0)])
    _write_assets(assets, {"site": "site.mp4"})
    _stub_profile(
        monkeypatch,
        _profile(intervals=(MotionInterval(20.0, 20.5, 90.0, "jump"),)),
    )

    report = analyze_declared_windows(plan, assets, root=tmp_path)

    assert report.passed
    assert report.verdicts[0].status == "clear"
    assert [profile.video_path for profile in report.profiles] == [
        tmp_path / "site.mp4"
    ]


def test_window_containing_jump_needs_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "site.mp4").write_bytes(b"stub")
    plan, assets = tmp_path / "plan.json", tmp_path / "assets.json"
    _write_plan(plan, [("s2", "site", 19.0, 21.0)])
    _write_assets(assets, {"site": "site.mp4"})
    _stub_profile(
        monkeypatch,
        _profile(intervals=(MotionInterval(20.0, 20.5, 90.0, "jump"),)),
    )

    report = analyze_declared_windows(plan, assets, root=tmp_path)

    assert report.passed is False
    assert report.verdicts[0].status == "needs_review"
    assert report.issues[0].category == "window_contains_jump"


def test_accepted_window_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "site.mp4").write_bytes(b"stub")
    plan, assets = tmp_path / "plan.json", tmp_path / "assets.json"
    _write_plan(plan, [("s2", "site", 19.0, 21.0)])
    _write_assets(assets, {"site": "site.mp4"})
    _stub_profile(
        monkeypatch,
        _profile(intervals=(MotionInterval(20.0, 20.5, 90.0, "jump"),)),
    )

    report = analyze_declared_windows(
        plan, assets, root=tmp_path, accepted_segments=frozenset({"s2"})
    )

    assert report.passed
    assert report.verdicts[0].status == "accepted"
    assert report.issues == ()


def test_window_beyond_source_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "site.mp4").write_bytes(b"stub")
    plan, assets = tmp_path / "plan.json", tmp_path / "assets.json"
    _write_plan(plan, [("s2", "site", 55.0, 70.0)])
    _write_assets(assets, {"site": "site.mp4"})
    _stub_profile(monkeypatch, _profile(duration=60.0))

    report = analyze_declared_windows(plan, assets, root=tmp_path)

    assert report.passed is False
    assert report.verdicts[0].status == "out_of_bounds"
    assert report.issues[0].category == "window_out_of_bounds"


def test_window_without_readable_asset_is_blocked(tmp_path: Path) -> None:
    plan, assets = tmp_path / "plan.json", tmp_path / "assets.json"
    _write_plan(plan, [("s2", "site", 0.0, 5.0)])
    _write_assets(assets, {"site": "missing.mp4"})

    report = analyze_declared_windows(plan, assets, root=tmp_path)

    assert report.passed is False
    assert report.verdicts[0].status == "missing_asset"
    assert report.issues[0].category == "missing_window_asset"


def test_plan_without_clips_is_not_a_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, assets = tmp_path / "plan.json", tmp_path / "assets.json"
    _write_plan(plan, [])
    _write_assets(assets, {})

    report = analyze_declared_windows(plan, assets, root=tmp_path)

    assert report.passed
    assert report.verdicts == ()
    assert report.profiles == ()
