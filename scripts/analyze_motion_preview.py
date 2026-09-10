from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import TalkingCraftError, read_json, write_json

SEMANTIC_ROLES = {
    "transform",
    "problem_to_solution",
    "bad_to_better",
    "before_to_after",
    "flat_to_structured",
    "decompose",
    "assemble",
    "progress",
    "skeleton_then_fill",
    "agenda",
    "taxonomy",
    "explain",
    "causal_chain",
    "compare",
    "synced_panel_probe",
    "verify",
    "gate",
    "constraint_check",
    "focus",
    "evidence",
    "recap",
    "replace",
    "draw",
    "populate",
    "classify",
    "reversal",
    "aggregate",
    "timed_phrase",
    "type",
}


@dataclass(frozen=True)
class MotionFrame:
    time_seconds: float
    pixels: bytes
    delta: float


@dataclass(frozen=True)
class PreviewIssue:
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
class PreviewReport:
    passed: bool
    sampled_frames: int
    active_ratio: float
    longest_static_seconds: float
    active_intervals: tuple[tuple[float, float], ...]
    issues: tuple[PreviewIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "sampled_frames": self.sampled_frames,
            "active_ratio": round(self.active_ratio, 4),
            "longest_static_seconds": round(self.longest_static_seconds, 3),
            "active_intervals": [
                {"start_seconds": round(start, 3), "end_seconds": round(end, 3)}
                for start, end in self.active_intervals
            ],
            "issues": [issue.to_dict() for issue in self.issues],
        }


def analyze_motion_preview(
    video_path: Path,
    plan_path: Path,
    *,
    sample_fps: float = 10.0,
    timeline_fps: float = 30.0,
    difference_threshold: float = 0.08,
    beat_window_seconds: float = 0.65,
) -> PreviewReport:
    """Measure rendered motion and compare it with an approved semantic motion plan."""
    if not video_path.is_file():
        raise TalkingCraftError(f"Video not found: {video_path}")
    payload = _require_object(read_json(plan_path), "motion plan")
    plan = payload.get("motion_plan") if isinstance(payload.get("motion_plan"), dict) else payload
    frames = _extract_gray_frames(video_path, sample_fps)
    return evaluate_motion_samples(
        frames,
        _require_object(plan, "motion plan"),
        sample_fps=sample_fps,
        timeline_fps=timeline_fps,
        difference_threshold=difference_threshold,
        beat_window_seconds=beat_window_seconds,
    )


def evaluate_motion_samples(
    frames: list[MotionFrame],
    plan: dict[str, Any],
    *,
    sample_fps: float,
    timeline_fps: float,
    difference_threshold: float,
    beat_window_seconds: float,
) -> PreviewReport:
    if len(frames) < 2:
        raise TalkingCraftError("Motion preview needs at least two sampled frames")
    if sample_fps <= 0 or timeline_fps <= 0:
        raise TalkingCraftError("sample_fps and timeline_fps must be positive")

    active = [frame.delta >= difference_threshold for frame in frames]
    active_count = sum(active[1:])
    comparable_count = max(1, len(active) - 1)
    active_ratio = active_count / comparable_count
    issues: list[PreviewIssue] = []
    role = plan.get("role")
    beats = plan.get("beats") if isinstance(plan.get("beats"), list) else []

    if role in SEMANTIC_ROLES:
        if active_ratio < 0.03:
            issues.append(
                PreviewIssue(
                    "needs_review",
                    "underanimated_preview",
                    "Rendered preview contains almost no measurable motion for a semantic sequence",
                )
            )
        if active_ratio > 0.65:
            issues.append(
                PreviewIssue(
                    "needs_review",
                    "overanimated_preview",
                    "More than 65% of sampled intervals move; verify that motion stops after meaning is established",
                )
            )
        for index, beat in enumerate(beats):
            if not isinstance(beat, dict) or not isinstance(beat.get("at_frame"), int):
                continue
            beat_seconds = beat["at_frame"] / timeline_fps
            nearby = [
                frame.delta
                for frame in frames
                if abs(frame.time_seconds - beat_seconds) <= beat_window_seconds
            ]
            if not nearby or max(nearby) < difference_threshold:
                issues.append(
                    PreviewIssue(
                        "blocked",
                        "beat_without_rendered_motion",
                        f"Beat {index} at {beat_seconds:.2f}s has no measurable nearby motion",
                    )
                )
        if role not in {"focus", "evidence", "recap"} and not plan.get(
            "allow_return_to_initial"
        ):
            state_delta = _pixel_delta(frames[0].pixels, frames[-1].pixels)
            if state_delta < difference_threshold:
                issues.append(
                    PreviewIssue(
                        "blocked",
                        "unchanged_final_state",
                        "First and final sampled frames are nearly identical despite a semantic state change",
                    )
                )

    hold_frames = plan.get("hold_frames")
    if isinstance(hold_frames, int) and hold_frames > 0:
        hold_seconds = hold_frames / timeline_fps
        hold_start = max(0.0, frames[-1].time_seconds - hold_seconds)
        hold_samples = [
            frame.delta >= difference_threshold
            for frame in frames
            if frame.time_seconds >= hold_start
        ]
        hold_active_ratio = sum(hold_samples) / max(1, len(hold_samples))
        if role in SEMANTIC_ROLES and hold_active_ratio > 0.2:
            issues.append(
                PreviewIssue(
                    "needs_review",
                    "moving_completion_hold",
                    f"Completion hold remains active for {hold_active_ratio:.0%} of sampled intervals",
                )
            )

    intervals = _active_intervals(frames, active, sample_fps)
    longest_static = _longest_static_seconds(active, sample_fps)
    return PreviewReport(
        passed=not any(issue.severity == "blocked" for issue in issues),
        sampled_frames=len(frames),
        active_ratio=active_ratio,
        longest_static_seconds=longest_static,
        active_intervals=tuple(intervals),
        issues=tuple(issues),
    )


def _extract_gray_frames(video_path: Path, sample_fps: float) -> list[MotionFrame]:
    width = 160
    height = 90
    frame_size = width * height
    command = (
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vf",
        f"fps={sample_fps},scale={width}:{height},format=gray",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-",
    )
    result = subprocess.run(command, check=False, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise TalkingCraftError(f"ffmpeg motion sampling failed: {message}")
    raw = result.stdout
    if len(raw) % frame_size != 0:
        raise TalkingCraftError("ffmpeg returned an incomplete grayscale frame")

    frames: list[MotionFrame] = []
    previous: bytes | None = None
    for index in range(len(raw) // frame_size):
        pixels = raw[index * frame_size : (index + 1) * frame_size]
        delta = 0.0 if previous is None else _pixel_delta(previous, pixels)
        frames.append(MotionFrame(index / sample_fps, pixels, delta))
        previous = pixels
    return frames


def _pixel_delta(left: bytes, right: bytes) -> float:
    if len(left) != len(right) or not left:
        raise TalkingCraftError("Motion frames must have matching non-zero dimensions")
    return sum(abs(a - b) for a, b in zip(left, right, strict=True)) / len(left)


def _active_intervals(
    frames: list[MotionFrame], active: list[bool], sample_fps: float
) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    start: float | None = None
    for frame, is_active in zip(frames, active, strict=True):
        if is_active and start is None:
            start = frame.time_seconds
        elif not is_active and start is not None:
            result.append((start, frame.time_seconds))
            start = None
    if start is not None:
        result.append((start, frames[-1].time_seconds + 1 / sample_fps))
    return result


def _longest_static_seconds(active: list[bool], sample_fps: float) -> float:
    longest = 0
    current = 0
    for is_active in active[1:]:
        if is_active:
            longest = max(longest, current)
            current = 0
        else:
            current += 1
    return max(longest, current) / sample_fps


def _require_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TalkingCraftError(f"{label} must be a JSON object")
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare rendered segment motion with a semantic motion plan"
    )
    parser.add_argument("video", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--sample-fps", type=float, default=10.0)
    parser.add_argument("--timeline-fps", type=float, default=30.0)
    parser.add_argument("--difference-threshold", type=float, default=0.08)
    parser.add_argument("--beat-window-seconds", type=float, default=0.65)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = analyze_motion_preview(
            args.video,
            args.plan,
            sample_fps=args.sample_fps,
            timeline_fps=args.timeline_fps,
            difference_threshold=args.difference_threshold,
            beat_window_seconds=args.beat_window_seconds,
        )
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
