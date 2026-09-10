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
class StreamInfo:
    index: int
    codec_type: str
    codec_name: str | None
    width: int | None
    height: int | None
    fps: float | None
    sample_rate: int | None
    channels: int | None
    duration_seconds: float | None
    frame_count: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "codec_type": self.codec_type,
            "codec_name": self.codec_name,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration_seconds": self.duration_seconds,
            "frame_count": self.frame_count,
        }


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    size_bytes: int
    sha256: str
    duration_seconds: float | None
    bit_rate: int | None
    streams: tuple[StreamInfo, ...]
    decode_checked: bool
    decode_ok: bool | None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "duration_seconds": self.duration_seconds,
            "bit_rate": self.bit_rate,
            "streams": [stream.to_dict() for stream in self.streams],
            "decode_checked": self.decode_checked,
            "decode_ok": self.decode_ok,
        }


def inspect_media(path: Path, *, decode: bool = False) -> MediaInfo:
    """Inspect one media file with ffprobe and optionally decode it fully."""
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise TalkingCraftError(f"Media file does not exist: {resolved}")
    probe = run_command(
        (
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,sample_rate,channels,duration,nb_frames:stream_tags=rotate:stream_side_data=rotation",
            "-of",
            "json",
            str(resolved),
        )
    )
    try:
        payload = json.loads(probe.stdout)
    except json.JSONDecodeError as error:
        raise TalkingCraftError(
            f"ffprobe returned invalid JSON for {resolved}"
        ) from error

    format_info = payload.get("format", {})
    streams = tuple(_parse_stream(raw) for raw in payload.get("streams", []))
    decode_ok: bool | None = None
    if decode:
        decoded = run_command(
            (
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(resolved),
                "-map",
                "0:v?",
                "-map",
                "0:a?",
                "-f",
                "null",
                "-",
            ),
            check=False,
        )
        decode_ok = decoded.returncode == 0

    return MediaInfo(
        path=resolved,
        size_bytes=resolved.stat().st_size,
        sha256=sha256_file(resolved),
        duration_seconds=_optional_float(format_info.get("duration")),
        bit_rate=_optional_int(format_info.get("bit_rate")),
        streams=streams,
        decode_checked=decode,
        decode_ok=decode_ok,
    )


def inspect_many(paths: list[Path], *, decode: bool = False) -> list[MediaInfo]:
    """Inspect media paths in their supplied order."""
    return [inspect_media(path, decode=decode) for path in paths]


def _parse_stream(raw: dict[str, Any]) -> StreamInfo:
    fps = parse_fraction(raw.get("avg_frame_rate")) or parse_fraction(
        raw.get("r_frame_rate")
    )
    return StreamInfo(
        index=int(raw.get("index", 0)),
        codec_type=str(raw.get("codec_type", "unknown")),
        codec_name=_optional_string(raw.get("codec_name")),
        width=_optional_int(raw.get("width")),
        height=_optional_int(raw.get("height")),
        fps=fps,
        sample_rate=_optional_int(raw.get("sample_rate")),
        channels=_optional_int(raw.get("channels")),
        duration_seconds=_optional_float(raw.get("duration")),
        frame_count=_optional_int(raw.get("nb_frames")),
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
    parser = argparse.ArgumentParser(description="Inspect media for Ryan Talking Craft")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--decode", action="store_true", help="Fully decode all streams"
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        values = [
            item.to_dict() for item in inspect_many(args.paths, decode=args.decode)
        ]
    except TalkingCraftError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1
    report = {"ok": True, "media": values}
    if args.output:
        write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
