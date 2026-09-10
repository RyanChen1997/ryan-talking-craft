from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from build_video_contact_sheets import BatchContactConfig, build_video_contact_sheets
from extract_frames import ExtractConfig, extract_frames
from inspect_media import inspect_media
from prepare_narration import prepare_narration
from validate_render import RenderExpectations, validate_render


@pytest.fixture(scope="module")
def sample_media(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg and ffprobe are required")
    root = tmp_path_factory.mktemp("media")
    output = root / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=#2855f5:s=320x240:r=30:d=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            "-y",
            str(output),
        ],
        check=True,
    )
    return output


def test_inspect_and_decode(sample_media: Path) -> None:
    result = inspect_media(sample_media, decode=True)

    assert result.decode_ok is True
    assert any(stream.codec_type == "video" for stream in result.streams)
    assert any(stream.codec_type == "audio" for stream in result.streams)
    assert result.sha256


def test_prepare_narration_creates_continuous_pcm_wav(
    sample_media: Path, tmp_path: Path
) -> None:
    report = prepare_narration(sample_media, tmp_path / "narration-master.wav")

    assert report.passed is True
    assert report.codec == "pcm_s16le"
    assert report.sample_rate == 48_000
    assert report.channels == 1
    assert report.start_time_seconds == 0
    assert report.max_packet_gap_ms <= 2


def test_extract_frames(sample_media: Path, tmp_path: Path) -> None:
    result = extract_frames(
        ExtractConfig(
            input_path=sample_media,
            output_dir=tmp_path / "analysis",
            times=(0.0, 0.5, 0.9),
            width=160,
        )
    )

    assert len(result.frames) == 3
    assert all(path.is_file() for _, path in result.frames)
    assert (tmp_path / "analysis/frame-index.json").is_file()
    assert result.contact_sheet is not None and result.contact_sheet.is_file()
    cached = extract_frames(ExtractConfig(sample_media, tmp_path / "analysis", times=(0.0, 0.5, 0.9), width=160))
    assert cached.cache_hit is True
    result.frames[0][1].unlink()
    refreshed = extract_frames(ExtractConfig(sample_media, tmp_path / "analysis", times=(0.0, 0.5, 0.9), width=160))
    assert refreshed.cache_hit is False


def test_build_video_contact_sheets(sample_media: Path, tmp_path: Path) -> None:
    duplicate_name = tmp_path / "copy" / sample_media.name
    duplicate_name.parent.mkdir()
    shutil.copy2(sample_media, duplicate_name)

    result = build_video_contact_sheets(
        BatchContactConfig(
            inputs=(sample_media, duplicate_name),
            output_dir=tmp_path / "recordings",
            sample_count=3,
            width=160,
        )
    )

    assert len(result.results) == 2
    assert (tmp_path / "recordings/contact-sheet-index.json").is_file()
    assert (tmp_path / "recordings/sample/frame-index.json").is_file()
    assert (tmp_path / "recordings/sample-02/frame-index.json").is_file()


def test_validate_render(sample_media: Path) -> None:
    report = validate_render(
        sample_media,
        RenderExpectations(width=320, height=240, fps=30, frames=30),
    )

    assert report.passed is True
    assert report.decode_ok is True
