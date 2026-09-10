from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import BinaryIO

from analyze_blank_regions import RegionOfInterest
from common import TalkingCraftError, read_json, write_json
from inspect_media import MediaInfo, inspect_media
from PIL import Image, ImageChops, ImageStat

# 本脚本只做数值：把视频解成低分辨率灰度帧序列后按帧算标量，不提交任何图片给模型。
# 三种信号：
#   ① 素材运动量剖面——相邻帧变化量随时间的曲线，用来选录屏窗口、找可定格区间。
#   ② 成片连续性——平均亮度的离群与变化量尖峰，用来找黑帧和段首淡入这类"闪一下"。
#   ③ 边缘出框——画面四边窄条里的亮像素，用来找关键文字／卡片被画面边缘切掉。
# 阈值与采样率绑定：改动 sample_fps 必须重新校准阈值，不要跨采样率套用默认值。


@dataclass(frozen=True)
class FrameSignalIssue:
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
class FrameScan:
    """一次解码得到的逐帧标量；剖面与连续性共用同一次扫描。"""

    sampled_fps: float
    decoded_width: int
    decoded_height: int
    means: tuple[float, ...]
    deltas: tuple[float, ...]

    @property
    def frame_count(self) -> int:
        return len(self.means)

    @property
    def duration_seconds(self) -> float:
        return self.frame_count / self.sampled_fps if self.sampled_fps > 0 else 0.0


@dataclass(frozen=True)
class MotionProfileConfig:
    sample_fps: float = 30.0
    width: int = 240
    fast_threshold: float = 12.0
    jump_threshold: float = 40.0
    static_threshold: float = 1.0
    roi: RegionOfInterest | None = None


_DEFAULT_MOTION_CONFIG = MotionProfileConfig()


@dataclass(frozen=True)
class MotionInterval:
    start_seconds: float
    end_seconds: float
    peak_delta: float
    level: str

    def to_dict(self) -> dict[str, object]:
        return {
            "start_seconds": round(self.start_seconds, 3),
            "end_seconds": round(self.end_seconds, 3),
            "peak_delta": round(self.peak_delta, 2),
            "level": self.level,
        }


@dataclass(frozen=True)
class MotionProfile:
    video_path: Path
    duration_seconds: float
    sampled_fps: float
    decoded_width: int
    decoded_height: int
    frames: int
    median_delta: float
    peak_delta: float
    high_motion_intervals: tuple[MotionInterval, ...]
    static_intervals: tuple[tuple[float, float], ...]
    per_second_peak: tuple[float, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "video_path": str(self.video_path),
            "duration_seconds": round(self.duration_seconds, 3),
            "sampled_fps": self.sampled_fps,
            "decoded": {
                "width": self.decoded_width,
                "height": self.decoded_height,
                "frames": self.frames,
            },
            "median_delta": round(self.median_delta, 3),
            "peak_delta": round(self.peak_delta, 2),
            "high_motion_intervals": [
                interval.to_dict() for interval in self.high_motion_intervals
            ],
            "static_intervals": [
                {"start_seconds": round(start, 3), "end_seconds": round(end, 3)}
                for start, end in self.static_intervals
            ],
            "per_second_peak": [round(value, 2) for value in self.per_second_peak],
        }


@dataclass(frozen=True)
class ContinuityConfig:
    sample_fps: float = 30.0
    width: int = 240
    black_threshold: float = 8.0
    luminance_tolerance: float = 8.0
    delta_ratio: float = 3.0
    delta_min: float = 1.5
    transient_window_frames: int = 8
    boundary_window_frames: int = 2
    blocking_depth_ratio: float = 0.5
    roi: RegionOfInterest | None = None


_DEFAULT_CONTINUITY_CONFIG = ContinuityConfig()


BLOCKING_OUTLIER_KINDS = frozenset({"black_frame"})
LUMINANCE_OUTLIER_KINDS = frozenset({"luminance_dip", "luminance_flash"})


@dataclass(frozen=True)
class FrameOutlier:
    frame: int
    seconds: float
    kind: str
    value: float
    baseline: float
    relative_deviation: float
    at_segment_boundary: bool
    boundary_distance_frames: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "frame": self.frame,
            "seconds": round(self.seconds, 3),
            "kind": self.kind,
            "value": round(self.value, 2),
            "baseline": round(self.baseline, 2),
            "relative_deviation": round(self.relative_deviation, 4),
            "at_segment_boundary": self.at_segment_boundary,
            "boundary_distance_frames": self.boundary_distance_frames,
        }


@dataclass(frozen=True)
class ContinuityReport:
    passed: bool
    sampled_fps: float
    frames: int
    dark_frame_ratio: float
    outliers: tuple[FrameOutlier, ...]
    issues: tuple[FrameSignalIssue, ...]
    accepted_frames: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "sampled_fps": self.sampled_fps,
            "frames": self.frames,
            "dark_frame_ratio": round(self.dark_frame_ratio, 4),
            "outlier_count": len(self.outliers),
            "outliers": [outlier.to_dict() for outlier in self.outliers],
            "accepted_frames": list(self.accepted_frames),
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class EdgeContentConfig:
    strip_pixels: int = 4
    luminance_threshold: int = 80
    max_strip_ratio: float = 0.005
    roi: RegionOfInterest | None = None


_DEFAULT_EDGE_CONFIG = EdgeContentConfig()


@dataclass(frozen=True)
class EdgeStripMetrics:
    side: str
    pixels: int
    bright_pixels: int
    bright_ratio: float
    max_luminance: int

    def to_dict(self) -> dict[str, object]:
        return {
            "side": self.side,
            "pixels": self.pixels,
            "bright_pixels": self.bright_pixels,
            "bright_ratio": round(self.bright_ratio, 4),
            "max_luminance": self.max_luminance,
        }


@dataclass(frozen=True)
class FrameEdgeMetrics:
    path: Path
    width: int
    height: int
    analyzed_roi: RegionOfInterest
    strips: tuple[EdgeStripMetrics, ...]

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
            "strips": [strip.to_dict() for strip in self.strips],
        }


@dataclass(frozen=True)
class EdgeContentReport:
    passed: bool
    frames: tuple[FrameEdgeMetrics, ...]
    issues: tuple[FrameSignalIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "checked_frames": len(self.frames),
            "frames": [frame.to_dict() for frame in self.frames],
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class DeclaredWindow:
    segment_id: str
    asset_id: str
    source_in: float
    source_out: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "segment_id": self.segment_id,
            "asset_id": self.asset_id,
            "source_in": self.source_in,
            "source_out": self.source_out,
        }


@dataclass(frozen=True)
class WindowVerdict:
    segment_id: str
    asset_id: str
    source_in: float
    source_out: float
    source_duration_seconds: float | None
    peak_delta: float
    jump_intervals: int
    fast_intervals: int
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "segment_id": self.segment_id,
            "asset_id": self.asset_id,
            "source_in": round(self.source_in, 3),
            "source_out": round(self.source_out, 3),
            "played_seconds": round(self.source_out - self.source_in, 3),
            "source_duration_seconds": (
                round(self.source_duration_seconds, 3)
                if self.source_duration_seconds is not None
                else None
            ),
            "peak_delta": round(self.peak_delta, 2),
            "jump_intervals": self.jump_intervals,
            "fast_intervals": self.fast_intervals,
            "status": self.status,
        }


@dataclass(frozen=True)
class WindowReport:
    passed: bool
    verdicts: tuple[WindowVerdict, ...]
    profiles: tuple[MotionProfile, ...]
    issues: tuple[FrameSignalIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "checked_windows": len(self.verdicts),
            "windows": [verdict.to_dict() for verdict in self.verdicts],
            "profiles": [profile.to_dict() for profile in self.profiles],
            "issues": [issue.to_dict() for issue in self.issues],
        }


def sample_frame_scan(
    video_path: Path,
    *,
    sample_fps: float,
    width: int,
    roi: RegionOfInterest | None = None,
) -> FrameScan:
    """Decode one video into low-resolution frames and reduce each frame to scalars."""
    _validate_scan_request(sample_fps, width)
    resolved = video_path.expanduser().resolve()
    if not resolved.is_file():
        raise TalkingCraftError(f"Video not found: {resolved}")
    media = inspect_media(resolved)
    source_width, source_height = _source_dimensions(media)
    decoded_width, decoded_height = _decoded_geometry(
        source_width, source_height, width, roi
    )
    means: list[float] = []
    deltas: list[float] = []
    previous: Image.Image | None = None
    for image in _iter_gray_frames(
        resolved, sample_fps, decoded_width, decoded_height, roi
    ):
        means.append(ImageStat.Stat(image).mean[0])
        if previous is None:
            deltas.append(0.0)
        else:
            difference = ImageChops.difference(previous, image)
            deltas.append(ImageStat.Stat(difference).mean[0])
        previous = image
    if not means:
        raise TalkingCraftError(f"No frames decoded from {resolved}")
    return FrameScan(
        sampled_fps=sample_fps,
        decoded_width=decoded_width,
        decoded_height=decoded_height,
        means=tuple(means),
        deltas=tuple(deltas),
    )


def evaluate_motion_profile(
    scan: FrameScan,
    video_path: Path,
    duration_seconds: float,
    *,
    config: MotionProfileConfig = _DEFAULT_MOTION_CONFIG,
) -> MotionProfile:
    """Classify a decoded scan into fast, jump and static intervals."""
    _validate_motion_config(config)
    high_motion: list[MotionInterval] = []
    for start, end in _merge_runs(
        [delta >= config.fast_threshold for delta in scan.deltas]
    ):
        peak = max(scan.deltas[start : end + 1])
        high_motion.append(
            MotionInterval(
                start_seconds=start / scan.sampled_fps,
                end_seconds=(end + 1) / scan.sampled_fps,
                peak_delta=peak,
                level="jump" if peak >= config.jump_threshold else "fast",
            )
        )
    static_intervals = [
        (start / scan.sampled_fps, (end + 1) / scan.sampled_fps)
        for start, end in _merge_runs(
            [delta <= config.static_threshold for delta in scan.deltas]
        )
    ]
    return MotionProfile(
        video_path=video_path,
        duration_seconds=duration_seconds,
        sampled_fps=scan.sampled_fps,
        decoded_width=scan.decoded_width,
        decoded_height=scan.decoded_height,
        frames=scan.frame_count,
        median_delta=statistics.median(scan.deltas),
        peak_delta=max(scan.deltas),
        high_motion_intervals=tuple(high_motion),
        static_intervals=tuple(static_intervals),
        per_second_peak=_per_second_peak(scan.deltas, scan.sampled_fps),
    )


def sample_motion_profile(
    video_path: Path,
    *,
    config: MotionProfileConfig = _DEFAULT_MOTION_CONFIG,
) -> MotionProfile:
    """Measure how much a source recording moves over time."""
    resolved = video_path.expanduser().resolve()
    scan = sample_frame_scan(
        resolved,
        sample_fps=config.sample_fps,
        width=config.width,
        roi=config.roi,
    )
    media = inspect_media(resolved)
    duration = media.duration_seconds or scan.duration_seconds
    return evaluate_motion_profile(scan, resolved, duration, config=config)


def evaluate_continuity(
    scan: FrameScan,
    *,
    cut_frames: tuple[int, ...] = (),
    accepted_frames: frozenset[int] = frozenset(),
    config: ContinuityConfig = _DEFAULT_CONTINUITY_CONFIG,
) -> ContinuityReport:
    """Find black frames, luminance transients and motion spikes in a rendered cut."""
    _validate_continuity_config(config)
    outliers = _continuity_outliers(scan, cut_frames, config)
    issues: list[FrameSignalIssue] = []
    for outlier in outliers:
        if outlier.at_segment_boundary or outlier.frame in accepted_frames:
            continue
        severity = _outlier_severity(outlier, config)
        issues.append(
            FrameSignalIssue(
                severity,
                f"{outlier.kind}_inside_segment",
                f"frame {outlier.frame}",
                f"{outlier.kind} at {outlier.seconds:.2f}s "
                f"(value {outlier.value:.2f} vs baseline {outlier.baseline:.2f}, "
                f"{outlier.relative_deviation:.0%} off) is not at a segment boundary",
            )
        )
    blocked = [issue for issue in issues if issue.severity == "blocked"]
    dark_ratio = (
        sum(1 for mean in scan.means if mean < config.black_threshold)
        / scan.frame_count
    )
    return ContinuityReport(
        passed=not blocked,
        sampled_fps=scan.sampled_fps,
        frames=scan.frame_count,
        dark_frame_ratio=dark_ratio,
        outliers=outliers,
        issues=tuple(issues),
        accepted_frames=tuple(sorted(accepted_frames)),
    )


def _continuity_outliers(
    scan: FrameScan,
    cut_frames: tuple[int, ...],
    config: ContinuityConfig,
) -> tuple[FrameOutlier, ...]:
    """Flag transient brightness departures and motion spikes.

    Brightness is compared with the median of the frames *before* and *after* the
    current one, and the stricter of the two sides wins. A dip or flash that both
    sides disagree with is a transient; a permanent move to a darker or brighter
    scene (a scroll into a dark page) leaves both sides agreeing and stays clean.
    """
    outliers: list[FrameOutlier] = []
    window = config.transient_window_frames
    for index in range(scan.frame_count):
        mean = scan.means[index]
        neighbors = [
            side
            for side in (
                _side_median(scan.means, index - window, index),
                _side_median(scan.means, index + 1, index + 1 + window),
            )
            if side is not None
        ]
        delta = scan.deltas[index]
        baseline_delta = _local_median(scan.deltas, index, 2)
        kind: str | None = None
        value = mean
        baseline = min(neighbors) if neighbors else mean
        if mean < config.black_threshold:
            kind = "black_frame"
        elif neighbors and mean < min(neighbors) - config.luminance_tolerance:
            kind = "luminance_dip"
            baseline = min(neighbors)
        elif neighbors and mean > max(neighbors) + config.luminance_tolerance:
            kind = "luminance_flash"
            baseline = max(neighbors)
        elif delta > max(config.delta_min, baseline_delta * config.delta_ratio):
            kind = "motion_spike"
            value = delta
            baseline = baseline_delta
        if kind is None:
            continue
        # 亮度类：去掉基线亮度的比例；运动尖峰：当前变化量相对局部变化底噪的倍数。
        relative = abs(value - baseline) / max(baseline, 1.0)
        distance = _boundary_distance(index, cut_frames)
        outliers.append(
            FrameOutlier(
                frame=index,
                seconds=index / scan.sampled_fps,
                kind=kind,
                value=value,
                baseline=baseline,
                relative_deviation=relative,
                at_segment_boundary=distance is not None
                and distance <= config.boundary_window_frames,
                boundary_distance_frames=distance,
            )
        )
    return tuple(outliers)


def _outlier_severity(outlier: FrameOutlier, config: ContinuityConfig) -> str:
    """Severity scales with how much of the frame's brightness the deviation removes.

    A whole screen fading up from black, or a card fading in over the dark stage,
    takes most of the light away and is a defect; a gentle overlap between two
    similar images only removes a fifth and is worth a look, not a gate failure.
    """
    if outlier.kind in BLOCKING_OUTLIER_KINDS:
        return "blocked"
    if outlier.kind in LUMINANCE_OUTLIER_KINDS:
        return (
            "blocked"
            if outlier.relative_deviation >= config.blocking_depth_ratio
            else "needs_review"
        )
    return "needs_review"


def analyze_continuity(
    video_path: Path,
    *,
    cut_frames: tuple[int, ...] = (),
    accepted_frames: frozenset[int] = frozenset(),
    config: ContinuityConfig = _DEFAULT_CONTINUITY_CONFIG,
) -> ContinuityReport:
    """Check one rendered file for frame-to-frame discontinuities."""
    resolved = video_path.expanduser().resolve()
    scan = sample_frame_scan(
        resolved,
        sample_fps=config.sample_fps,
        width=config.width,
        roi=config.roi,
    )
    return evaluate_continuity(
        scan,
        cut_frames=cut_frames,
        accepted_frames=accepted_frames,
        config=config,
    )


def analyze_edge_content(
    image_paths: tuple[Path, ...],
    *,
    config: EdgeContentConfig = _DEFAULT_EDGE_CONFIG,
) -> EdgeContentReport:
    """Detect bright content inside the outermost strips of each frame."""
    if not image_paths:
        raise TalkingCraftError("At least one frame image is required")
    _validate_edge_config(config)
    frames = tuple(_analyze_edge_frame(path, config) for path in image_paths)
    issues: list[FrameSignalIssue] = []
    for frame in frames:
        for strip in frame.strips:
            if strip.bright_ratio <= config.max_strip_ratio:
                continue
            issues.append(
                FrameSignalIssue(
                    "blocked",
                    "content_at_frame_edge",
                    f"{frame.path} {strip.side}",
                    f"{strip.bright_pixels} of {strip.pixels} pixels in the {strip.side} "
                    f"{config.strip_pixels}px strip reach luminance {config.luminance_threshold}"
                    f"+ ({strip.bright_ratio:.2%})",
                )
            )
    return EdgeContentReport(
        passed=not issues,
        frames=frames,
        issues=tuple(issues),
    )


def analyze_declared_windows(
    plan_path: Path,
    assets_path: Path,
    *,
    root: Path,
    config: MotionProfileConfig = _DEFAULT_MOTION_CONFIG,
    accepted_segments: frozenset[str] = frozenset(),
) -> WindowReport:
    """Compare every declared clip window with the motion profile of its source."""
    windows = _declared_windows(read_json(plan_path))
    asset_paths = _asset_paths(read_json(assets_path), root)
    profiles: dict[str, MotionProfile] = {}
    verdicts: list[WindowVerdict] = []
    issues: list[FrameSignalIssue] = []
    for window in windows:
        path = asset_paths.get(window.asset_id)
        if path is None or not path.is_file():
            verdicts.append(
                WindowVerdict(
                    window.segment_id,
                    window.asset_id,
                    window.source_in,
                    window.source_out or 0.0,
                    None,
                    0.0,
                    0,
                    0,
                    "missing_asset",
                )
            )
            issues.append(
                FrameSignalIssue(
                    "blocked",
                    "missing_window_asset",
                    window.segment_id,
                    f"Window references asset {window.asset_id!r} without a readable file",
                )
            )
            continue
        key = str(path)
        if key not in profiles:
            profiles[key] = sample_motion_profile(path, config=config)
        profile = profiles[key]
        source_out = (
            window.source_out
            if window.source_out is not None
            else profile.duration_seconds
        )
        overlaps = _overlapping_intervals(
            profile.high_motion_intervals, window.source_in, source_out
        )
        jumps = sum(1 for interval in overlaps if interval.level == "jump")
        verdict = WindowVerdict(
            window.segment_id,
            window.asset_id,
            window.source_in,
            source_out,
            profile.duration_seconds,
            max((interval.peak_delta for interval in overlaps), default=0.0),
            jumps,
            len(overlaps) - jumps,
            "clear",
        )
        if source_out > profile.duration_seconds + 0.05 or window.source_in < 0:
            verdict = replace(verdict, status="out_of_bounds")
            issues.append(
                FrameSignalIssue(
                    "blocked",
                    "window_out_of_bounds",
                    window.segment_id,
                    f"Window {window.source_in:.2f}-{source_out:.2f}s exceeds the "
                    f"{profile.duration_seconds:.2f}s source",
                )
            )
        elif jumps and window.segment_id not in accepted_segments:
            verdict = replace(verdict, status="needs_review")
            issues.append(
                FrameSignalIssue(
                    "needs_review",
                    "window_contains_jump",
                    window.segment_id,
                    f"Window {window.source_in:.2f}-{source_out:.2f}s contains {jumps} jump-level "
                    f"motion interval(s) up to delta {verdict.peak_delta:.1f}; "
                    "narrow the window or accept it with --accept",
                )
            )
        elif jumps:
            verdict = replace(verdict, status="accepted")
        verdicts.append(verdict)
    return WindowReport(
        passed=not any(issue.severity == "blocked" for issue in issues)
        and not any(issue.severity == "needs_review" for issue in issues),
        verdicts=tuple(verdicts),
        profiles=tuple(profiles.values()),
        issues=tuple(issues),
    )


def _source_dimensions(media: MediaInfo) -> tuple[int | None, int | None]:
    for stream in media.streams:
        if stream.codec_type == "video" and stream.width and stream.height:
            return stream.width, stream.height
    return None, None


def _decoded_geometry(
    source_width: int | None,
    source_height: int | None,
    width: int,
    roi: RegionOfInterest | None,
) -> tuple[int, int]:
    if roi is not None:
        aspect = roi.height / roi.width
    elif source_width and source_height:
        aspect = source_height / source_width
    else:
        aspect = 9 / 16
    return width, max(2, round(width * aspect))


def _iter_gray_frames(
    video_path: Path,
    sample_fps: float,
    width: int,
    height: int,
    roi: RegionOfInterest | None,
) -> Iterator[Image.Image]:
    if shutil.which("ffmpeg") is None:
        raise TalkingCraftError("ffmpeg is required to decode frame signals")
    filters = []
    if roi is not None:
        filters.append(f"crop={roi.width}:{roi.height}:{roi.x}:{roi.y}")
    filters.extend((f"fps={sample_fps}", f"scale={width}:{height}", "format=gray"))
    command = (
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-i",
        str(video_path),
        "-an",
        "-sn",
        "-vf",
        ",".join(filters),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-",
    )
    frame_size = width * height
    with tempfile.TemporaryFile() as error_log:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=error_log,
        )
        stdout = process.stdout
        if stdout is None:
            raise TalkingCraftError("ffmpeg stdout pipe is unavailable")
        try:
            while True:
                buffer = _read_exact(stdout, frame_size)
                if len(buffer) < frame_size:
                    if buffer:
                        raise TalkingCraftError(
                            f"ffmpeg returned an incomplete grayscale frame for {video_path}"
                        )
                    break
                yield Image.frombytes("L", (width, height), buffer)
        finally:
            stdout.close()
            returncode = process.wait()
        if returncode != 0:
            error_log.seek(0)
            message = error_log.read().decode("utf-8", errors="replace").strip()
            raise TalkingCraftError(
                f"ffmpeg frame sampling failed for {video_path}: {message}"
            )


def _read_exact(handle: BinaryIO, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = handle.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _merge_runs(flags: list[bool]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, flag in enumerate(flags):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, len(flags) - 1))
    return runs


def _per_second_peak(
    deltas: tuple[float, ...], sampled_fps: float
) -> tuple[float, ...]:
    if sampled_fps <= 0 or not deltas:
        return ()
    peaks: list[float] = []
    for index, delta in enumerate(deltas):
        second = int(index // sampled_fps)
        while len(peaks) <= second:
            peaks.append(0.0)
        peaks[second] = max(peaks[second], delta)
    return tuple(peaks)


def _local_median(values: tuple[float, ...], index: int, window: int) -> float:
    low = max(0, index - window)
    high = min(len(values), index + window + 1)
    return statistics.median(values[low:high])


def _side_median(values: tuple[float, ...], start: int, stop: int) -> float | None:
    if stop <= start:
        return None
    low = max(0, start)
    high = min(len(values), stop)
    if high <= low:
        return None
    return statistics.median(values[low:high])


def _boundary_distance(frame: int, cut_frames: tuple[int, ...]) -> int | None:
    if not cut_frames:
        return None
    return min(abs(frame - cut) for cut in cut_frames)


def _overlapping_intervals(
    intervals: tuple[MotionInterval, ...], start: float, end: float
) -> list[MotionInterval]:
    return [
        interval
        for interval in intervals
        if interval.start_seconds < end and interval.end_seconds > start
    ]


def _analyze_edge_frame(path: Path, config: EdgeContentConfig) -> FrameEdgeMetrics:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise TalkingCraftError(f"Frame image does not exist: {resolved}")
    with Image.open(resolved) as opened:
        image = opened.convert("L")
    roi = _resolve_roi(config.roi, image.width, image.height)
    strip = min(config.strip_pixels, roi.width // 2, roi.height // 2)
    if strip < 1:
        raise TalkingCraftError("strip_pixels must leave at least one pixel of content")
    regions = {
        "top": (roi.x, roi.y, roi.x + roi.width, roi.y + strip),
        "bottom": (
            roi.x,
            roi.y + roi.height - strip,
            roi.x + roi.width,
            roi.y + roi.height,
        ),
        "left": (roi.x, roi.y, roi.x + strip, roi.y + roi.height),
        "right": (
            roi.x + roi.width - strip,
            roi.y,
            roi.x + roi.width,
            roi.y + roi.height,
        ),
    }
    strips = tuple(
        _strip_metrics(side, image.crop(box), config.luminance_threshold)
        for side, box in regions.items()
    )
    return FrameEdgeMetrics(
        path=resolved,
        width=image.width,
        height=image.height,
        analyzed_roi=roi,
        strips=strips,
    )


def _strip_metrics(side: str, strip: Image.Image, threshold: int) -> EdgeStripMetrics:
    histogram = strip.histogram()
    pixels = strip.width * strip.height
    bright = sum(histogram[threshold:])
    top_luminance = [index for index, count in enumerate(histogram) if count > 0]
    return EdgeStripMetrics(
        side=side,
        pixels=pixels,
        bright_pixels=bright,
        bright_ratio=bright / pixels if pixels else 0.0,
        max_luminance=max(top_luminance, default=0),
    )


def _declared_windows(plan_payload: object) -> tuple[DeclaredWindow, ...]:
    plan = _require_object(plan_payload, "plan")
    segments = plan.get("segments")
    if not isinstance(segments, list):
        raise TalkingCraftError("plan.segments must be a list")
    windows: list[DeclaredWindow] = []
    for segment in segments:
        if not isinstance(segment, dict):
            raise TalkingCraftError("Every plan segment must be an object")
        segment_id = str(segment.get("id") or "unknown")
        visual = segment.get("visual")
        clips = visual.get("clips") if isinstance(visual, dict) else None
        if not isinstance(clips, list):
            continue
        for clip in clips:
            if not isinstance(clip, dict):
                raise TalkingCraftError(f"Segment {segment_id} has a non-object clip")
            asset_id = clip.get("asset_id")
            source_in = clip.get("source_in")
            if not isinstance(asset_id, str) or not isinstance(source_in, (int, float)):
                raise TalkingCraftError(
                    f"Segment {segment_id} clip needs asset_id and numeric source_in"
                )
            source_out = clip.get("source_out")
            windows.append(
                DeclaredWindow(
                    segment_id=segment_id,
                    asset_id=asset_id,
                    source_in=float(source_in),
                    source_out=float(source_out)
                    if isinstance(source_out, (int, float))
                    else None,
                )
            )
    return tuple(windows)


def _asset_paths(assets_payload: object, root: Path) -> dict[str, Path]:
    assets = _require_object(assets_payload, "assets").get("assets")
    if not isinstance(assets, list):
        raise TalkingCraftError("assets.assets must be a list")
    paths: dict[str, Path] = {}
    for entry in assets:
        if not isinstance(entry, dict):
            raise TalkingCraftError("Every asset entry must be an object")
        asset_id = entry.get("id")
        raw_path = entry.get("path")
        if not isinstance(asset_id, str) or not isinstance(raw_path, str):
            continue
        candidate = Path(raw_path).expanduser()
        paths[asset_id] = candidate if candidate.is_absolute() else root / candidate
    return paths


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


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TalkingCraftError(f"{label} must be a JSON object")
    return value


def _validate_scan_request(sample_fps: float, width: int) -> None:
    if not 1 <= sample_fps <= 120:
        raise TalkingCraftError("sample_fps must be between 1 and 120")
    if not 64 <= width <= 640:
        raise TalkingCraftError("Analysis width must be between 64 and 640")


def _validate_motion_config(config: MotionProfileConfig) -> None:
    if (
        not 0
        < config.static_threshold
        <= config.fast_threshold
        <= config.jump_threshold
    ):
        raise TalkingCraftError(
            "Require 0 < static_threshold <= fast_threshold <= jump_threshold"
        )


def _validate_continuity_config(config: ContinuityConfig) -> None:
    if not 0 <= config.black_threshold <= 255:
        raise TalkingCraftError("black_threshold must be between 0 and 255")
    if config.luminance_tolerance < 0:
        raise TalkingCraftError("luminance_tolerance must not be negative")
    if config.delta_ratio <= 0 or config.delta_min < 0:
        raise TalkingCraftError(
            "delta_ratio must be positive and delta_min non-negative"
        )
    if config.transient_window_frames < 1:
        raise TalkingCraftError("transient_window_frames must be at least 1")
    if config.boundary_window_frames < 0:
        raise TalkingCraftError("boundary_window_frames must not be negative")
    if not 0 <= config.blocking_depth_ratio <= 1:
        raise TalkingCraftError("blocking_depth_ratio must be between 0 and 1")


def _validate_edge_config(config: EdgeContentConfig) -> None:
    if config.strip_pixels < 1:
        raise TalkingCraftError("strip_pixels must be positive")
    if not 0 <= config.luminance_threshold <= 255:
        raise TalkingCraftError("luminance_threshold must be between 0 and 255")
    if not 0 <= config.max_strip_ratio <= 1:
        raise TalkingCraftError("max_strip_ratio must be between 0 and 1")


def _parse_roi(value: str | None) -> RegionOfInterest | None:
    if value is None:
        return None
    try:
        x, y, width, height = (int(part.strip()) for part in value.split(","))
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError("ROI must be x,y,width,height") from error
    return RegionOfInterest(x, y, width, height)


def _parse_cut_frames(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()
    frames: list[int] = []
    for part in value.split(","):
        try:
            frames.append(int(part.strip()))
        except ValueError as error:
            raise argparse.ArgumentTypeError("cut frames must be integers") from error
    if any(frame < 0 for frame in frames):
        raise argparse.ArgumentTypeError("cut frames must not be negative")
    return tuple(frames)


def _plan_cut_frames(plan_path: Path) -> tuple[int, ...]:
    plan = _require_object(read_json(plan_path), "plan")
    segments = plan.get("segments")
    if not isinstance(segments, list):
        raise TalkingCraftError("plan.segments must be a list")
    frames: list[int] = []
    for segment in segments:
        if isinstance(segment, dict) and isinstance(segment.get("from"), int):
            frames.append(segment["from"])
    return tuple(sorted(set(frames)))


def _parse_frame_set(value: str | None) -> frozenset[int]:
    """Parse frame numbers and inclusive ranges, e.g. "1200,4060-4070"."""
    if not value:
        return frozenset()
    frames: set[int] = set()
    for part in value.split(","):
        token = part.strip()
        if not token:
            continue
        try:
            if "-" in token:
                start_text, end_text = token.split("-", maxsplit=1)
                start, end = int(start_text), int(end_text)
                if end < start:
                    raise ValueError
                frames.update(range(start, end + 1))
            else:
                frames.add(int(token))
        except ValueError as error:
            raise argparse.ArgumentTypeError(
                "accepted frames must be frame numbers or start-end ranges"
            ) from error
    if any(frame < 0 for frame in frames):
        raise argparse.ArgumentTypeError("accepted frames must not be negative")
    return frozenset(frames)


def _parse_accept(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(part.strip() for part in value.split(",") if part.strip())


def _chart_lines(profile: MotionProfile, jump_threshold: float) -> list[str]:
    lines = [
        f"{profile.video_path.name} 每秒最大变化量（刻度 0-{int(jump_threshold * 3)}）"
    ]
    for second, peak in enumerate(profile.per_second_peak):
        bar = "█" * round(peak / 3)
        tag = "  ← 剧烈跳变" if peak >= jump_threshold else ""
        lines.append(f"{second:4d}s |{bar:<40}| {peak:6.1f}{tag}")
    return lines


def _run_mode(args: argparse.Namespace) -> tuple[dict[str, object], bool]:
    if args.mode == "motion":
        config = MotionProfileConfig(
            sample_fps=args.sample_fps,
            width=args.width,
            fast_threshold=args.fast_threshold,
            jump_threshold=args.jump_threshold,
            static_threshold=args.static_threshold,
            roi=_parse_roi(args.roi),
        )
        profiles = [
            sample_motion_profile(video, config=config) for video in args.videos
        ]
        if args.chart:
            for profile in profiles:
                print(
                    "\n".join(_chart_lines(profile, config.jump_threshold)),
                    file=sys.stderr,
                )
        return (
            {
                "mode": "motion",
                "checked_videos": len(profiles),
                "profiles": [profile.to_dict() for profile in profiles],
            },
            True,
        )
    if args.mode == "windows":
        report = analyze_declared_windows(
            args.plan,
            args.assets,
            root=args.root,
            config=MotionProfileConfig(
                sample_fps=args.sample_fps,
                width=args.width,
                fast_threshold=args.fast_threshold,
                jump_threshold=args.jump_threshold,
                static_threshold=args.static_threshold,
            ),
            accepted_segments=_parse_accept(args.accept),
        )
        if args.chart:
            for profile in report.profiles:
                print(
                    "\n".join(_chart_lines(profile, args.jump_threshold)),
                    file=sys.stderr,
                )
        return report.to_dict(), report.passed
    if args.mode == "continuity":
        cut_frames = (
            _plan_cut_frames(args.plan)
            if args.plan
            else _parse_cut_frames(args.cut_frames)
        )
        report = analyze_continuity(
            args.video,
            cut_frames=cut_frames,
            accepted_frames=_parse_frame_set(args.accept_frames),
            config=ContinuityConfig(
                sample_fps=args.sample_fps,
                width=args.width,
                black_threshold=args.black_threshold,
                luminance_tolerance=args.luminance_tolerance,
                delta_ratio=args.delta_ratio,
                delta_min=args.delta_min,
                transient_window_frames=args.transient_window_frames,
                boundary_window_frames=args.boundary_window_frames,
                blocking_depth_ratio=args.blocking_depth_ratio,
                roi=_parse_roi(args.roi),
            ),
        )
        return report.to_dict(), report.passed
    report = analyze_edge_content(
        tuple(args.images),
        config=EdgeContentConfig(
            strip_pixels=args.strip_pixels,
            luminance_threshold=args.luminance_threshold,
            max_strip_ratio=args.max_strip_ratio,
            roi=_parse_roi(args.roi),
        ),
    )
    return report.to_dict(), report.passed


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan frame-level signals: source motion, cut continuity, frame edges"
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    motion = subparsers.add_parser(
        "motion", help="Per-second motion profile of source videos"
    )
    motion.add_argument("videos", nargs="+", type=Path)
    motion.add_argument("--sample-fps", type=float, default=30.0)
    motion.add_argument("--width", type=int, default=240)
    motion.add_argument("--fast-threshold", type=float, default=12.0)
    motion.add_argument("--jump-threshold", type=float, default=40.0)
    motion.add_argument("--static-threshold", type=float, default=1.0)
    motion.add_argument("--roi", type=str)
    motion.add_argument(
        "--chart", action="store_true", help="print the profile to stderr"
    )
    motion.add_argument("--output", type=Path)

    windows = subparsers.add_parser(
        "windows", help="Compare declared clip windows with their source motion"
    )
    windows.add_argument("plan", type=Path)
    windows.add_argument("assets", type=Path)
    windows.add_argument("--root", type=Path, default=Path("."))
    windows.add_argument("--accept", type=str, help="Comma-separated segment ids")
    windows.add_argument("--sample-fps", type=float, default=30.0)
    windows.add_argument("--width", type=int, default=240)
    windows.add_argument("--fast-threshold", type=float, default=12.0)
    windows.add_argument("--jump-threshold", type=float, default=40.0)
    windows.add_argument("--static-threshold", type=float, default=1.0)
    windows.add_argument("--chart", action="store_true")
    windows.add_argument("--output", type=Path)

    continuity = subparsers.add_parser(
        "continuity", help="Find black frames, brightness dips and motion spikes"
    )
    continuity.add_argument("video", type=Path)
    continuity.add_argument(
        "--plan", type=Path, help="Use segment starts as expected cuts"
    )
    continuity.add_argument("--cut-frames", type=str)
    continuity.add_argument("--sample-fps", type=float, default=30.0)
    continuity.add_argument("--width", type=int, default=240)
    continuity.add_argument("--black-threshold", type=float, default=8.0)
    continuity.add_argument("--luminance-tolerance", type=float, default=18.0)
    continuity.add_argument("--delta-ratio", type=float, default=3.0)
    continuity.add_argument("--delta-min", type=float, default=1.5)
    continuity.add_argument("--transient-window-frames", type=int, default=8)
    continuity.add_argument("--boundary-window-frames", type=int, default=2)
    continuity.add_argument(
        "--blocking-depth-ratio",
        type=float,
        default=0.5,
        help="Relative brightness loss that counts as a defect instead of a review note",
    )
    continuity.add_argument(
        "--accept-frames",
        type=str,
        help="Frames of intentional transitions, e.g. 4060-4070",
    )
    continuity.add_argument("--roi", type=str)
    continuity.add_argument("--output", type=Path)

    edges = subparsers.add_parser("edges", help="Find bright content at frame edges")
    edges.add_argument("images", nargs="+", type=Path)
    edges.add_argument("--strip-pixels", type=int, default=4)
    edges.add_argument("--luminance-threshold", type=int, default=80)
    edges.add_argument("--max-strip-ratio", type=float, default=0.005)
    edges.add_argument("--roi", type=str)
    edges.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        payload, passed = _run_mode(args)
    except (TalkingCraftError, argparse.ArgumentTypeError) as error:
        print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        return 2
    if args.output:
        write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
