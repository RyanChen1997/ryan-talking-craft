from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from common import TalkingCraftError, write_json
from PIL import Image


@dataclass(frozen=True)
class RegionOfInterest:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class BlankRegionConfig:
    white_threshold: int = 245
    downsample_width: int = 320
    max_component_ratio: float = 0.25
    max_frame_delta: float = 0.12
    roi: RegionOfInterest | None = None
    intentional_blank_reason: str | None = None


_DEFAULT_CONFIG = BlankRegionConfig()


@dataclass(frozen=True)
class FrameBlankMetrics:
    path: Path
    width: int
    height: int
    analyzed_roi: RegionOfInterest
    near_white_ratio: float
    largest_near_white_component_ratio: float

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "width": self.width,
            "height": self.height,
            "analyzed_roi": {
                "x": self.analyzed_roi.x,
                "y": self.analyzed_roi.y,
                "width": self.analyzed_roi.width,
                "height": self.analyzed_roi.height,
            },
            "near_white_ratio": self.near_white_ratio,
            "largest_near_white_component_ratio": self.largest_near_white_component_ratio,
        }


@dataclass(frozen=True)
class BlankRegionIssue:
    severity: str
    category: str
    frame_path: Path | None
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "category": self.category,
            "frame_path": str(self.frame_path) if self.frame_path else None,
            "message": self.message,
        }


@dataclass(frozen=True)
class BlankRegionReport:
    passed: bool
    frames: tuple[FrameBlankMetrics, ...]
    issues: tuple[BlankRegionIssue, ...]
    intentional_blank_reason: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "checked_frames": len(self.frames),
            "frames": [frame.to_dict() for frame in self.frames],
            "issues": [issue.to_dict() for issue in self.issues],
            "intentional_blank_reason": self.intentional_blank_reason,
        }


def analyze_blank_regions(
    image_paths: tuple[Path, ...],
    *,
    config: BlankRegionConfig = _DEFAULT_CONFIG,
) -> BlankRegionReport:
    """Detect large connected near-white regions and camera-induced blank exposure."""
    if not image_paths:
        raise TalkingCraftError("At least one frame image is required")
    _validate_config(config)
    frames = tuple(_analyze_frame(path, config) for path in image_paths)
    issues: list[BlankRegionIssue] = []
    allowlisted = bool(config.intentional_blank_reason)
    for frame in frames:
        ratio = frame.largest_near_white_component_ratio
        if ratio > config.max_component_ratio and not allowlisted:
            issues.append(
                BlankRegionIssue(
                    "blocked",
                    "unplanned_blank_region",
                    frame.path,
                    f"Largest connected near-white region covers {ratio:.1%} of the media ROI",
                )
            )
    ratios = [frame.near_white_ratio for frame in frames]
    if len(ratios) > 1 and max(ratios) - min(ratios) > config.max_frame_delta:
        worst = frames[ratios.index(max(ratios))]
        issues.append(
            BlankRegionIssue(
                "blocked",
                "dynamic_canvas_exposure",
                worst.path,
                f"Near-white exposure changes by {max(ratios) - min(ratios):.1%} across sampled beats",
            )
        )
    return BlankRegionReport(
        passed=not any(issue.severity == "blocked" for issue in issues),
        frames=frames,
        issues=tuple(issues),
        intentional_blank_reason=config.intentional_blank_reason,
    )


def _analyze_frame(path: Path, config: BlankRegionConfig) -> FrameBlankMetrics:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise TalkingCraftError(f"Frame image does not exist: {resolved}")
    with Image.open(resolved) as opened:
        image = opened.convert("RGB")
    roi = _resolve_roi(config.roi, image.width, image.height)
    cropped = image.crop((roi.x, roi.y, roi.x + roi.width, roi.y + roi.height))
    target_width = min(config.downsample_width, cropped.width)
    target_height = max(1, round(cropped.height * target_width / cropped.width))
    sampled = cropped.resize((target_width, target_height), Image.Resampling.BOX)
    pixels = list(sampled.get_flattened_data())
    mask = [
        red >= config.white_threshold
        and green >= config.white_threshold
        and blue >= config.white_threshold
        for red, green, blue in pixels
    ]
    total = len(mask)
    near_white_ratio = sum(mask) / total
    largest = _largest_component(mask, sampled.width, sampled.height) / total
    return FrameBlankMetrics(
        path=resolved,
        width=image.width,
        height=image.height,
        analyzed_roi=roi,
        near_white_ratio=near_white_ratio,
        largest_near_white_component_ratio=largest,
    )


def _largest_component(mask: list[bool], width: int, height: int) -> int:
    visited = bytearray(len(mask))
    largest = 0
    for start, active in enumerate(mask):
        if not active or visited[start]:
            continue
        visited[start] = 1
        queue = deque([start])
        size = 0
        while queue:
            index = queue.popleft()
            size += 1
            x = index % width
            y = index // width
            for neighbor in (
                index - 1 if x > 0 else -1,
                index + 1 if x + 1 < width else -1,
                index - width if y > 0 else -1,
                index + width if y + 1 < height else -1,
            ):
                if neighbor >= 0 and mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    queue.append(neighbor)
        largest = max(largest, size)
    return largest


def _resolve_roi(
    requested: RegionOfInterest | None,
    image_width: int,
    image_height: int,
) -> RegionOfInterest:
    roi = requested or RegionOfInterest(0, 0, image_width, image_height)
    if (
        roi.x < 0
        or roi.y < 0
        or roi.width <= 0
        or roi.height <= 0
        or roi.x + roi.width > image_width
        or roi.y + roi.height > image_height
    ):
        raise TalkingCraftError("ROI must be a positive rectangle inside every frame")
    return roi


def _validate_config(config: BlankRegionConfig) -> None:
    if not 0 <= config.white_threshold <= 255:
        raise TalkingCraftError("white_threshold must be between 0 and 255")
    if config.downsample_width <= 0:
        raise TalkingCraftError("downsample_width must be positive")
    for label, value in (
        ("max_component_ratio", config.max_component_ratio),
        ("max_frame_delta", config.max_frame_delta),
    ):
        if not 0 <= value <= 1:
            raise TalkingCraftError(f"{label} must be between 0 and 1")


def _parse_roi(value: str | None) -> RegionOfInterest | None:
    if value is None:
        return None
    try:
        x, y, width, height = (int(part.strip()) for part in value.split(","))
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError("ROI must be x,y,width,height") from error
    return RegionOfInterest(x, y, width, height)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect large blank white regions inside rendered media viewports"
    )
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--roi", type=str, help="Pixel ROI: x,y,width,height")
    parser.add_argument("--white-threshold", type=int, default=245)
    parser.add_argument("--max-component-ratio", type=float, default=0.25)
    parser.add_argument("--max-frame-delta", type=float, default=0.12)
    parser.add_argument("--intentional-blank-reason")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = analyze_blank_regions(
            tuple(args.images),
            config=BlankRegionConfig(
                white_threshold=args.white_threshold,
                max_component_ratio=args.max_component_ratio,
                max_frame_delta=args.max_frame_delta,
                roi=_parse_roi(args.roi),
                intentional_blank_reason=args.intentional_blank_reason,
            ),
        )
    except (TalkingCraftError, argparse.ArgumentTypeError) as error:
        print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        return 2
    payload = report.to_dict()
    if args.output:
        write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
