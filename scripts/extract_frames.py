from __future__ import annotations

import argparse
import json
import math
import hashlib

from PIL import Image, ImageDraw, ImageOps
from dataclasses import dataclass
from pathlib import Path

from common import TalkingCraftError, run_command, write_json
from inspect_media import inspect_media


@dataclass(frozen=True)
class ExtractConfig:
    input_path: Path
    output_dir: Path
    times: tuple[float, ...] | None = None
    sample_count: int = 12
    width: int = 480


@dataclass(frozen=True)
class ExtractResult:
    input_path: Path
    duration_seconds: float
    frames: tuple[tuple[float, Path], ...]
    contact_sheet: Path | None
    cache_hit: bool = False

    @classmethod
    def from_dict(cls, value: dict) -> ExtractResult:
        return cls(Path(value["input_path"]), value["duration_seconds"], tuple((f["time_seconds"], Path(f["path"])) for f in value["frames"]), Path(value["contact_sheet"]) if value.get("contact_sheet") else None, value.get("cache_hit", False))

    def to_dict(self) -> dict[str, object]:
        return {
            "cache_hit": self.cache_hit,
            "input_path": str(self.input_path),
            "duration_seconds": self.duration_seconds,
            "frames": [
                {"time_seconds": time_value, "path": str(path)}
                for time_value, path in self.frames
            ],
            "contact_sheet": str(self.contact_sheet) if self.contact_sheet else None,
        }


def extract_frames(config: ExtractConfig) -> ExtractResult:
    """Extract representative frames and build a contact sheet."""
    if config.width < 64 or config.width > 2000:
        raise TalkingCraftError("Analysis frame long edge must be between 64 and 2000")
    if not 3 <= config.sample_count <= 48:
        raise TalkingCraftError("sample_count must be between 3 and 48; use targeted timestamps for detailed analysis")
    if config.times is not None and (not config.times or len(config.times) > 48 or any(not math.isfinite(t) or t < 0 for t in config.times)):
        raise TalkingCraftError("Provide 1–48 finite non-negative timestamps")
    media = inspect_media(config.input_path)
    if media.duration_seconds is None or media.duration_seconds <= 0:
        raise TalkingCraftError(f"Cannot determine video duration: {config.input_path}")
    if not any(stream.codec_type == "video" for stream in media.streams):
        raise TalkingCraftError(f"Input has no video stream: {config.input_path}")

    output_dir = config.output_dir.expanduser().resolve()
    signature = hashlib.sha256(json.dumps({"version": 2, "sha256": media.sha256, "path": str(media.path), "times": config.times, "count": config.sample_count, "width": config.width}, sort_keys=True).encode()).hexdigest()
    index_path = output_dir / "frame-index.json"
    if index_path.exists():
        try:
            cached = json.loads(index_path.read_text())
            result = ExtractResult.from_dict(cached)
            if cached.get("signature") == signature and all(p.is_file() for _, p in result.frames) and result.contact_sheet and result.contact_sheet.is_file():
                return ExtractResult(result.input_path, result.duration_seconds, result.frames, result.contact_sheet, True)
        except (ValueError, KeyError, TypeError):
            pass
    frames_dir = output_dir / "frames" / signature[:16]
    frames_dir.mkdir(parents=True, exist_ok=True)
    times = config.times or _representative_times(
        media.duration_seconds, config.sample_count
    )
    frames: list[tuple[float, Path]] = []
    for time_value in times:
        clamped = min(max(0.0, time_value), max(0.0, media.duration_seconds - 0.1))
        frame_path = frames_dir / f"{round(clamped * 1000):09d}ms.jpg"
        extract_frame_at(media.path, clamped, frame_path, width=config.width)
        frames.append((round(clamped, 3), frame_path))

    contact_sheet = _make_contact_sheet(tuple(path for _, path in frames), frames_dir)
    result = ExtractResult(
        input_path=media.path,
        duration_seconds=media.duration_seconds,
        frames=tuple(frames),
        contact_sheet=contact_sheet,
    )
    write_json(output_dir / "frame-index.json", {**result.to_dict(), "signature": signature})
    return result


def extract_frame_at(
    input_path: Path,
    time_seconds: float,
    output_path: Path,
    *,
    width: int = 480,
) -> Path:
    """Extract one frame at an exact timestamp, scaled to a bounded long edge."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        (
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{time_seconds:.3f}",
            "-i",
            str(input_path),
            "-frames:v",
            "1",
            "-vf",
            f"scale=w='min({width},iw)':h='min({width},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
            "-q:v",
            "2",
            "-y",
            str(output_path),
        )
    )
    return output_path


def _representative_times(duration: float, sample_count: int) -> tuple[float, ...]:
    if sample_count < 3:
        raise TalkingCraftError("sample_count must be at least 3")
    # Coarse survey, not a claim that every short event has been observed.
    anchors = [max(0.0, duration - 0.1) * index / (sample_count - 1) for index in range(sample_count)]
    unique = sorted(
        {
            round(min(value, duration - 0.001), 3)
            for value in anchors
            if value < duration
        }
    )
    return tuple(unique)


def _make_contact_sheet(frame_paths: tuple[Path, ...], output_dir: Path) -> Path | None:
    if not frame_paths:
        return None
    columns = min(4, len(frame_paths))
    rows = math.ceil(len(frame_paths) / columns)
    # Keep even explicitly dense sheets bounded; inspect individual ROIs if needed.
    tile_w = min(400, 1920 // columns, 1920 // rows)
    tile_h = tile_w
    sheet = Image.new("RGB", (columns * tile_w, rows * tile_h), "#202020")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(frame_paths):
        x, y = index % columns * tile_w, index // columns * tile_h
        with Image.open(path) as image:
            thumb = ImageOps.contain(image.convert("RGB"), (tile_w - 12, tile_h - 30))
            sheet.paste(thumb, (x + (tile_w - thumb.width) // 2, y + 4))
        seconds = int(path.stem.removesuffix("ms")) / 1000
        draw.text((x + 6, y + tile_h - 22), f"{seconds:.3f}s", fill="white")
    output_path = output_dir / "contact-sheet.jpg"
    sheet.save(output_path, quality=85)
    return output_path


def _parse_times(value: str | None) -> tuple[float, ...] | None:
    if not value:
        return None
    try:
        parsed = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as error:
        raise TalkingCraftError("--times must be comma-separated seconds") from error
    if not parsed:
        raise TalkingCraftError("--times did not contain any values")
    return parsed


def _parse_args() -> ExtractConfig:
    parser = argparse.ArgumentParser(
        description="Extract representative talking-head frames"
    )
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--times", help="Comma-separated exact timestamps in seconds")
    parser.add_argument("--sample-count", type=int, default=12)
    parser.add_argument("--width", type=int, default=480, help="Maximum long edge of analysis frames")
    args = parser.parse_args()
    return ExtractConfig(
        input_path=args.input_path,
        output_dir=args.output_dir,
        times=_parse_times(args.times),
        sample_count=args.sample_count,
        width=args.width,
    )


def main() -> int:
    try:
        result = extract_frames(_parse_args())
    except TalkingCraftError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, **result.to_dict()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
