from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from analyze_frame_signal import EdgeContentConfig, analyze_edge_content
from common import TalkingCraftError, read_json, write_json
from extract_frames import extract_frame_at
from inspect_media import MediaInfo, inspect_media
from PIL import Image, ImageDraw, ImageOps

# 预览前必须过的一步：从**渲染出来的成片**里按 plan 抽关键帧，拼成低分辨率联系表，
# 连同"这一帧本该呈现什么"一起交给复核，重点看文字重叠、文字出画、实际画面与计划不符。
# 数值上可确定的部分（四边出框、成片与计划帧数是否一致）由本脚本判定；
# 文字重叠与语义仍必须看联系表——本脚本的 passed 不代表那两项已经看过。


@dataclass(frozen=True)
class KeyframeIssue:
    severity: str
    category: str
    subject: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "category": self.category,
            "subject": self.subject,
            "message": self.message,
        }


@dataclass(frozen=True)
class KeyframeReviewConfig:
    video_path: Path
    spec_dir: Path
    output_dir: Path
    per_segment: int = 1
    completion_ratio: float = 0.85
    include_boundaries: bool = False
    frame_width: int = 960
    tile_width: int = 560
    columns: int = 3
    rows: int = 3

    @property
    def tiles_per_sheet(self) -> int:
        return self.columns * self.rows


@dataclass(frozen=True)
class KeyframeRequest:
    """A frame to pull, together with the plan content it is supposed to show."""

    segment_id: str
    frame: int
    seconds: float
    layout: str | None
    template: str | None
    screen_text: tuple[str, ...]
    beats: str

    def to_dict(self) -> dict[str, object]:
        return {
            "segment_id": self.segment_id,
            "frame": self.frame,
            "seconds": round(self.seconds, 3),
            "expected": {
                "layout": self.layout,
                "template": self.template,
                "screen_text": list(self.screen_text),
                "beats": self.beats,
            },
        }


@dataclass(frozen=True)
class KeyframeTile:
    request: KeyframeRequest
    image: Path
    sheet: Path
    edge_status: str
    edge_detail: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            **self.request.to_dict(),
            "image": str(self.image),
            "sheet": str(self.sheet),
            "edge_status": self.edge_status,
            "edge_detail": self.edge_detail,
            "reviewed": False,
        }


@dataclass(frozen=True)
class KeyframeReviewReport:
    passed: bool
    duration_frame_delta: int
    tiles: tuple[KeyframeTile, ...]
    sheets: tuple[Path, ...]
    issues: tuple[KeyframeIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "human_review_required": True,
            "checked_frames": len(self.tiles),
            "duration_frame_delta": self.duration_frame_delta,
            "sheets": [str(path) for path in self.sheets],
            "tiles": [tile.to_dict() for tile in self.tiles],
            "issues": [issue.to_dict() for issue in self.issues],
            "review_instructions": [
                "逐张联系表按段号核对：该帧是否显示 expected.screen_text 的内容，是否符合 expected.beats",
                "重点排查文字重叠、文字出画、卡片压住人物、模板压住录屏",
                "联系表是低分辨率缩略图，只用于定位；可疑帧按 image 路径单独看原尺寸",
                "passed 只代表四边出框与帧数一致性已由脚本判定，不代表文字重叠与语义已看过",
            ],
        }


def select_keyframes(
    plan: dict[str, object],
    *,
    per_segment: int = 1,
    completion_ratio: float = 0.85,
    include_boundaries: bool = False,
    timeline_fps: float = 30.0,
) -> tuple[KeyframeRequest, ...]:
    """Pick the frames worth reviewing: mostly the completed state of each segment."""
    if per_segment < 1:
        raise TalkingCraftError("per_segment must be at least 1")
    if not 0 < completion_ratio <= 1:
        raise TalkingCraftError("completion_ratio must be within (0, 1]")
    segments = plan.get("segments")
    if not isinstance(segments, list) or not segments:
        raise TalkingCraftError("plan.segments must be a non-empty list")
    requests: list[KeyframeRequest] = []
    for segment in segments:
        if not isinstance(segment, dict):
            raise TalkingCraftError("Every plan segment must be an object")
        start = segment.get("from")
        end = segment.get("to")
        if not isinstance(start, int) or not isinstance(end, int) or end <= start:
            raise TalkingCraftError(
                "Every plan segment needs integral from/to with to > from"
            )
        visual = segment.get("visual")
        visual = visual if isinstance(visual, dict) else {}
        screen_text = segment.get("screen_text")
        beats = visual.get("beats")
        frames = _segment_offsets(start, end, per_segment, completion_ratio)
        if include_boundaries:
            frames.insert(0, start)
        for frame in frames:
            requests.append(
                KeyframeRequest(
                    segment_id=str(segment.get("id") or "unknown"),
                    frame=frame,
                    seconds=round(frame / timeline_fps, 3),
                    layout=_optional_text(visual.get("layout")),
                    template=_optional_text(visual.get("template")),
                    screen_text=(
                        tuple(str(item) for item in screen_text)
                        if isinstance(screen_text, list)
                        else ()
                    ),
                    beats=str(beats) if isinstance(beats, str) else "",
                )
            )
    return tuple(requests)


def build_keyframe_review(
    config: KeyframeReviewConfig,
) -> KeyframeReviewReport:
    """Extract plan-derived key frames from a render and tile them into review sheets."""
    plan_path = config.spec_dir.expanduser().resolve() / "plan.json"
    plan = read_json(plan_path)
    if not isinstance(plan, dict):
        raise TalkingCraftError(f"{plan_path} must contain a JSON object")
    video = config.video_path.expanduser().resolve()
    if not video.is_file():
        raise TalkingCraftError(f"Rendered video not found: {video}")
    media = inspect_media(video)
    duration_delta = _plan_duration_delta(plan, _duration_frames(media))
    requests = select_keyframes(
        plan,
        per_segment=config.per_segment,
        completion_ratio=config.completion_ratio,
        include_boundaries=config.include_boundaries,
    )
    images = _extract_keyframes(video, requests, config, media)
    edge_flags = _edge_flags([path for _, path in images], config)
    sheets = _build_sheets(images, config)
    tiles = tuple(
        KeyframeTile(
            request=request,
            image=path,
            sheet=sheet,
            edge_status="flagged" if edge_flags.get(_key(path)) else "ok",
            edge_detail=edge_flags.get(_key(path)),
        )
        for sheet, group in sheets
        for request, path in group
    )
    issues = _collect_issues(tiles, duration_delta)
    return KeyframeReviewReport(
        passed=not any(issue.severity == "blocked" for issue in issues),
        duration_frame_delta=duration_delta,
        tiles=tiles,
        sheets=tuple(sheet for sheet, _ in sheets),
        issues=tuple(issues),
    )


def _segment_offsets(
    start: int, end: int, per_segment: int, completion_ratio: float
) -> list[int]:
    span = end - start - 1
    if per_segment == 1:
        return [start + round(span * completion_ratio)]
    return [
        start + round(span * (index + 1) / (per_segment + 1))
        for index in range(per_segment)
    ]


def _extract_keyframes(
    video: Path,
    requests: tuple[KeyframeRequest, ...],
    config: KeyframeReviewConfig,
    media: MediaInfo,
) -> list[tuple[KeyframeRequest, Path]]:
    frames_dir = config.output_dir.expanduser().resolve() / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    last_seconds = max(0.0, (media.duration_seconds or 0.0) - 0.05)
    images: list[tuple[KeyframeRequest, Path]] = []
    for request in requests:
        path = frames_dir / f"k{request.frame:05d}-{request.segment_id}.jpg"
        extract_frame_at(
            video, min(request.seconds, last_seconds), path, width=config.frame_width
        )
        images.append((request, path))
    return images


def _edge_flags(paths: list[Path], config: KeyframeReviewConfig) -> dict[str, str]:
    """Report which key frames have bright content inside the outer strips."""
    if not paths:
        return {}
    edge_config = EdgeContentConfig(
        strip_pixels=max(1, round(4 * config.frame_width / 1920))
    )
    report = analyze_edge_content(tuple(paths), config=edge_config)
    flags: dict[str, str] = {}
    for frame in report.frames:
        offenders = [
            strip
            for strip in frame.strips
            if strip.bright_ratio > edge_config.max_strip_ratio
        ]
        if offenders:
            flags[_key(frame.path)] = ", ".join(
                f"{strip.side} {strip.bright_ratio:.1%}" for strip in offenders
            )
    return flags


def _build_sheets(
    images: list[tuple[KeyframeRequest, Path]], config: KeyframeReviewConfig
) -> list[tuple[Path, list[tuple[KeyframeRequest, Path]]]]:
    output_dir = config.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sheets: list[tuple[Path, list[tuple[KeyframeRequest, Path]]]] = []
    per_sheet = config.tiles_per_sheet
    for index in range(0, len(images), per_sheet):
        group = images[index : index + per_sheet]
        sheet = output_dir / f"keyframes-{index // per_sheet + 1}.jpg"
        _render_sheet(group, sheet, config)
        sheets.append((sheet, group))
    return sheets


def _render_sheet(
    group: list[tuple[KeyframeRequest, Path]],
    sheet_path: Path,
    config: KeyframeReviewConfig,
) -> None:
    tile_w = config.tile_width
    tile_h = round(tile_w * 9 / 16)
    label_h = 30
    rows = min(config.rows, math.ceil(len(group) / config.columns))
    sheet = Image.new(
        "RGB", (config.columns * tile_w, rows * (tile_h + label_h)), "#111214"
    )
    draw = ImageDraw.Draw(sheet)
    for index, (request, path) in enumerate(group):
        x = index % config.columns * tile_w
        y = index // config.columns * (tile_h + label_h)
        with Image.open(path) as opened:
            thumb = ImageOps.contain(opened.convert("RGB"), (tile_w - 8, tile_h - 6))
        sheet.paste(thumb, (x + (tile_w - thumb.width) // 2, y + 4))
        draw.text(
            (x + 6, y + tile_h + 8),
            f"{request.segment_id} · f{request.frame} · {request.seconds:.2f}s",
            fill="white",
        )
    sheet.save(sheet_path, quality=88)


def _collect_issues(
    tiles: tuple[KeyframeTile, ...], duration_delta: int
) -> list[KeyframeIssue]:
    issues: list[KeyframeIssue] = []
    if duration_delta > 2:
        issues.append(
            KeyframeIssue(
                "blocked",
                "render_does_not_match_plan",
                "render",
                f"Rendered frame count differs from plan.duration_frames by "
                f"{duration_delta} frames; review the render this plan describes",
            )
        )
    for tile in tiles:
        if tile.edge_status == "flagged":
            issues.append(
                KeyframeIssue(
                    "blocked",
                    "content_at_frame_edge",
                    f"{tile.request.segment_id} frame {tile.request.frame}",
                    f"{tile.edge_detail}: content reaches the frame edge",
                )
            )
    return issues


def _duration_frames(media: MediaInfo) -> int:
    for stream in media.streams:
        if stream.codec_type == "video" and stream.frame_count:
            return int(stream.frame_count)
        if stream.codec_type == "video" and stream.fps and media.duration_seconds:
            return round(media.duration_seconds * stream.fps)
    raise TalkingCraftError(f"Cannot determine the video frame count: {media.path}")


def _plan_duration_delta(plan: dict[str, object], duration_frames: int) -> int:
    planned = plan.get("duration_frames")
    if not isinstance(planned, int):
        raise TalkingCraftError("plan.duration_frames must be an integer")
    return abs(duration_frames - planned)


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _key(path: Path) -> str:
    return str(path.expanduser().resolve())


def _parse_args() -> KeyframeReviewConfig:
    parser = argparse.ArgumentParser(
        description="Extract plan key frames from a render and tile low-resolution review sheets"
    )
    parser.add_argument("video", type=Path)
    parser.add_argument("spec_dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--per-segment", type=int, default=1)
    parser.add_argument("--completion-ratio", type=float, default=0.85)
    parser.add_argument("--include-boundaries", action="store_true")
    parser.add_argument("--frame-width", type=int, default=960)
    parser.add_argument("--tile-width", type=int, default=560)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--rows", type=int, default=3)
    args = parser.parse_args()
    return KeyframeReviewConfig(
        video_path=args.video,
        spec_dir=args.spec_dir,
        output_dir=args.output_dir or args.spec_dir / "qa" / "keyframes",
        per_segment=args.per_segment,
        completion_ratio=args.completion_ratio,
        include_boundaries=args.include_boundaries,
        frame_width=args.frame_width,
        tile_width=args.tile_width,
        columns=args.columns,
        rows=args.rows,
    )


def main() -> int:
    config = _parse_args()
    try:
        report = build_keyframe_review(config)
    except TalkingCraftError as error:
        print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        return 2
    payload = report.to_dict()
    write_json(
        config.output_dir.expanduser().resolve() / "keyframe-review.json", payload
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
