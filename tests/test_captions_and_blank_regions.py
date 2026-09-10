from __future__ import annotations

from pathlib import Path

from analyze_blank_regions import BlankRegionConfig, analyze_blank_regions
from convert_subtitles import SubtitleConfig, convert_subtitles
from PIL import Image, ImageDraw


def test_convert_subtitles_splits_long_cue_and_preserves_timing(
    tmp_path: Path,
) -> None:
    source = tmp_path / "captions.srt"
    source.write_text(
        "1\n00:00:00,000 --> 00:00:04,000\n"
        "这是一个很长的口播字幕，需要按标点拆开，不能全部塞进同一屏。\n\n"
        "2\n00:00:04,500 --> 00:00:06,000\n第二句。\n",
        encoding="utf-8",
    )

    cues = convert_subtitles(source, config=SubtitleConfig(max_chars=12))

    assert len(cues) >= 3
    assert cues[0].start_ms == 0
    assert cues[-1].end_ms == 6000
    assert all(cue.end_ms > cue.start_ms for cue in cues)
    assert all(len(cue.text.replace(" ", "")) <= 12 for cue in cues)


def test_convert_webvtt_without_hour_field(tmp_path: Path) -> None:
    source = tmp_path / "captions.vtt"
    source.write_text(
        "WEBVTT\n\n00:01.000 --> 00:02.500\n默认也要显示字幕\n",
        encoding="utf-8",
    )

    cues = convert_subtitles(source)

    assert cues[0].start_ms == 1000
    assert cues[0].end_ms == 2500


def test_blank_region_is_blocked_unless_it_has_an_intentional_reason(
    tmp_path: Path,
) -> None:
    frame = tmp_path / "frame.png"
    image = Image.new("RGB", (400, 200), "#15171c")
    ImageDraw.Draw(image).rectangle((0, 0, 270, 199), fill="white")
    image.save(frame)

    blocked = analyze_blank_regions((frame,))
    allowlisted = analyze_blank_regions(
        (frame,),
        config=BlankRegionConfig(
            intentional_blank_reason="官方白色文档页面必须完整展示"
        ),
    )

    assert blocked.passed is False
    assert any(issue.category == "unplanned_blank_region" for issue in blocked.issues)
    assert allowlisted.passed is True


def test_dynamic_blank_exposure_is_blocked_even_with_static_allowlist(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    Image.new("RGB", (400, 200), "#15171c").save(first)
    exposed = Image.new("RGB", (400, 200), "#15171c")
    ImageDraw.Draw(exposed).rectangle((0, 0, 220, 199), fill="white")
    exposed.save(second)

    report = analyze_blank_regions(
        (first, second),
        config=BlankRegionConfig(intentional_blank_reason="静态白底已核验"),
    )

    assert report.passed is False
    assert any(issue.category == "dynamic_canvas_exposure" for issue in report.issues)
