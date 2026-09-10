from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import (
    TalkingCraftError,
    parse_fraction,
    run_command,
    sha256_file,
    write_json,
)


@dataclass(frozen=True)
class RenderExpectations:
    width: int
    height: int
    fps: float
    frames: int
    require_audio: bool = True
    audio_sample_rate: int = 48000
    max_stream_duration_delta: float = 0.1


@dataclass(frozen=True)
class RenderIssue:
    severity: str
    category: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
        }


@dataclass(frozen=True)
class RenderReport:
    path: Path
    passed: bool
    size_bytes: int
    sha256: str
    duration_seconds: float | None
    video: dict[str, object] | None
    audio: dict[str, object] | None
    decode_ok: bool
    issues: tuple[RenderIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "passed": self.passed,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "duration_seconds": self.duration_seconds,
            "video": self.video,
            "audio": self.audio,
            "decode_ok": self.decode_ok,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def validate_render(path: Path, expectations: RenderExpectations) -> RenderReport:
    """Validate a final rendered file with ffprobe and a full decode pass."""
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise TalkingCraftError(f"Rendered file is missing or empty: {resolved}")
    payload = _probe(resolved)
    streams = payload.get("streams", [])
    video_raw = next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "video"
        ),
        None,
    )
    audio_raw = next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "audio"
        ),
        None,
    )
    issues: list[RenderIssue] = []
    video = _validate_video(video_raw, expectations, issues)
    audio = _validate_audio(audio_raw, expectations, issues)
    _validate_duration_delta(video, audio, expectations, issues)
    decode = run_command(
        (
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(resolved),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-f",
            "null",
            "-",
        ),
        check=False,
    )
    decode_ok = decode.returncode == 0
    if not decode_ok:
        issues.append(
            RenderIssue(
                "blocked", "decode", decode.stderr.strip() or "Full decode failed"
            )
        )

    format_info = (
        payload.get("format", {}) if isinstance(payload.get("format"), dict) else {}
    )
    return RenderReport(
        path=resolved,
        passed=not any(issue.severity == "blocked" for issue in issues),
        size_bytes=resolved.stat().st_size,
        sha256=sha256_file(resolved),
        duration_seconds=_optional_float(format_info.get("duration")),
        video=video,
        audio=audio,
        decode_ok=decode_ok,
        issues=tuple(issues),
    )


def _probe(path: Path) -> dict[str, Any]:
    result = run_command(
        (
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,bit_rate:stream=index,codec_name,codec_type,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_frames,duration,sample_rate,channels,bit_rate",
            "-of",
            "json",
            str(path),
        )
    )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise TalkingCraftError("ffprobe returned invalid JSON") from error
    if not isinstance(value, dict):
        raise TalkingCraftError("ffprobe JSON root must be an object")
    return value


def _validate_video(
    raw: object,
    expected: RenderExpectations,
    issues: list[RenderIssue],
) -> dict[str, object] | None:
    if not isinstance(raw, dict):
        issues.append(RenderIssue("blocked", "video", "No video stream found"))
        return None
    width = _optional_int(raw.get("width"))
    height = _optional_int(raw.get("height"))
    fps = parse_fraction(_optional_string(raw.get("avg_frame_rate"))) or parse_fraction(
        _optional_string(raw.get("r_frame_rate"))
    )
    frames = _optional_int(raw.get("nb_frames"))
    duration = _optional_float(raw.get("duration"))
    if width != expected.width or height != expected.height:
        issues.append(
            RenderIssue(
                "blocked",
                "dimensions",
                f"Expected {expected.width}x{expected.height}, got {width}x{height}",
            )
        )
    if fps is None or abs(fps - expected.fps) > 0.001:
        issues.append(
            RenderIssue("blocked", "fps", f"Expected {expected.fps:g}fps, got {fps}")
        )
    if frames != expected.frames:
        issues.append(
            RenderIssue(
                "blocked", "frames", f"Expected {expected.frames} frames, got {frames}"
            )
        )
    return {
        "codec": raw.get("codec_name"),
        "width": width,
        "height": height,
        "fps": fps,
        "frames": frames,
        "duration_seconds": duration,
        "pixel_format": raw.get("pix_fmt"),
        "bit_rate": _optional_int(raw.get("bit_rate")),
    }


def _validate_audio(
    raw: object,
    expected: RenderExpectations,
    issues: list[RenderIssue],
) -> dict[str, object] | None:
    if not isinstance(raw, dict):
        if expected.require_audio:
            issues.append(RenderIssue("blocked", "audio", "No audio stream found"))
        return None
    sample_rate = _optional_int(raw.get("sample_rate"))
    if sample_rate != expected.audio_sample_rate:
        issues.append(
            RenderIssue(
                "blocked",
                "audio_sample_rate",
                f"Expected {expected.audio_sample_rate}Hz, got {sample_rate}",
            )
        )
    return {
        "codec": raw.get("codec_name"),
        "sample_rate": sample_rate,
        "channels": _optional_int(raw.get("channels")),
        "duration_seconds": _optional_float(raw.get("duration")),
        "bit_rate": _optional_int(raw.get("bit_rate")),
    }


def _validate_duration_delta(
    video: dict[str, object] | None,
    audio: dict[str, object] | None,
    expected: RenderExpectations,
    issues: list[RenderIssue],
) -> None:
    if video is None or audio is None:
        return
    video_duration = video.get("duration_seconds")
    audio_duration = audio.get("duration_seconds")
    if not isinstance(video_duration, float) or not isinstance(audio_duration, float):
        return
    delta = abs(video_duration - audio_duration)
    if delta > expected.max_stream_duration_delta:
        issues.append(
            RenderIssue(
                "blocked",
                "stream_duration_delta",
                f"Audio/video duration delta {delta:.3f}s exceeds {expected.max_stream_duration_delta:.3f}s",
            )
        )


def _optional_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_string(value: object) -> str | None:
    return str(value) if value is not None else None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a final Remotion render")
    parser.add_argument("path", type=Path)
    parser.add_argument("--width", required=True, type=int)
    parser.add_argument("--height", required=True, type=int)
    parser.add_argument("--fps", required=True, type=float)
    parser.add_argument("--frames", required=True, type=int)
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--audio-sample-rate", default=48000, type=int)
    parser.add_argument("--max-duration-delta", default=0.1, type=float)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    expected = RenderExpectations(
        width=args.width,
        height=args.height,
        fps=args.fps,
        frames=args.frames,
        require_audio=not args.no_audio,
        audio_sample_rate=args.audio_sample_rate,
        max_stream_duration_delta=args.max_duration_delta,
    )
    try:
        report = validate_render(args.path, expected)
    except TalkingCraftError as error:
        print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        return 2
    payload = report.to_dict()
    if args.output:
        write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
