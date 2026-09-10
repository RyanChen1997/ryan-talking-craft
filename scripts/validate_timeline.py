from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import TalkingCraftError, read_json, write_json


@dataclass(frozen=True)
class TimelineIssue:
    severity: str
    category: str
    message: str
    segment_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "category": self.category,
            "segment_id": self.segment_id,
            "message": self.message,
        }


@dataclass(frozen=True)
class TimelineReport:
    passed: bool
    issue_count: int
    issues: tuple[TimelineIssue, ...]
    checked_segments: int

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "issue_count": self.issue_count,
            "checked_segments": self.checked_segments,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def validate_timeline(
    timeline_path: Path,
    *,
    registry_path: Path,
    asset_manifest_path: Path | None = None,
    public_root: Path | None = None,
) -> TimelineReport:
    """Validate timeline continuity, template registration, assets, and audio."""
    timeline = _require_object(read_json(timeline_path), "timeline")
    registry = _template_index(_require_object(read_json(registry_path), "registry"))
    assets = _asset_index(asset_manifest_path)
    issues: list[TimelineIssue] = []

    composition = _require_object(timeline.get("composition"), "composition")
    duration = _positive_int(
        composition.get("duration_in_frames"), "composition.duration_in_frames"
    )
    fps = _positive_number(composition.get("fps"), "composition.fps")
    segments = timeline.get("segments")
    if not isinstance(segments, list) or not segments:
        raise TalkingCraftError("timeline.segments must be a non-empty array")

    expected_start = 0
    seen_ids: set[str] = set()
    for raw_segment in segments:
        segment = _require_object(raw_segment, "segment")
        segment_id = str(segment.get("segment_id", ""))
        if not segment_id:
            issues.append(
                TimelineIssue("blocked", "schema", "Segment is missing segment_id")
            )
            segment_id = None
        elif segment_id in seen_ids:
            issues.append(
                TimelineIssue("blocked", "schema", "Duplicate segment_id", segment_id)
            )
        else:
            seen_ids.add(segment_id)

        start = _integer_or_issue(
            segment.get("start_frame"), "start_frame", segment_id, issues
        )
        segment_duration = _integer_or_issue(
            segment.get("duration_in_frames"), "duration_in_frames", segment_id, issues
        )
        if start is None or segment_duration is None:
            continue
        if segment_duration <= 0:
            issues.append(
                TimelineIssue(
                    "blocked",
                    "timing",
                    "duration_in_frames must be positive",
                    segment_id,
                )
            )
        if start > expected_start:
            issues.append(
                TimelineIssue(
                    "blocked",
                    "timing_gap",
                    f"Gap of {start - expected_start} frame(s) before segment",
                    segment_id,
                )
            )
        elif start < expected_start:
            issues.append(
                TimelineIssue(
                    "blocked",
                    "timing_overlap",
                    f"Overlap of {expected_start - start} frame(s) before segment",
                    segment_id,
                )
            )
        expected_start = max(expected_start, start + max(segment_duration, 0))

        _validate_template(segment, registry, fps, segment_duration, segment_id, issues)
        _validate_assets(
            segment, assets, fps, segment_duration, segment_id, public_root, issues
        )

    if expected_start != duration:
        issues.append(
            TimelineIssue(
                "blocked",
                "timing_end",
                f"Timeline ends at frame {expected_start}, composition ends at {duration}",
            )
        )

    _validate_audio(timeline.get("audio"), duration, issues)
    _validate_captions(
        timeline.get("captions"),
        assets,
        duration,
        fps,
        public_root,
        issues,
    )
    return TimelineReport(
        passed=not any(issue.severity == "blocked" for issue in issues),
        issue_count=len(issues),
        issues=tuple(issues),
        checked_segments=len(segments),
    )


def _validate_template(
    segment: dict[str, Any],
    registry: dict[str, dict[str, Any]],
    fps: float,
    duration: int,
    segment_id: str | None,
    issues: list[TimelineIssue],
) -> None:
    template_id = segment.get("template")
    if not isinstance(template_id, str) or template_id not in registry:
        issues.append(
            TimelineIssue(
                "blocked",
                "template",
                f"Unregistered template: {template_id!r}",
                segment_id,
            )
        )
        return
    metadata = registry[template_id]
    if metadata.get("requiresMediaLayoutPlan") is True and not isinstance(
        segment.get("media_layout"), dict
    ):
        issues.append(
            TimelineIssue(
                "blocked",
                "media_layout_missing",
                f"Template {template_id} requires a media_layout plan",
                segment_id,
            )
        )
    if metadata.get("requiresCameraBoundsClamp") is True:
        layout = segment.get("media_layout")
        if not isinstance(layout, dict) or layout.get("camera_bounds_clamped") is not True:
            issues.append(
                TimelineIssue(
                    "blocked",
                    "camera_bounds",
                    f"Template {template_id} requires camera_bounds_clamped=true",
                    segment_id,
                )
            )
    minimum_at_30 = metadata.get("minDurationFramesAt30")
    maximum_at_30 = metadata.get("maxDurationFramesAt30")
    if isinstance(minimum_at_30, (int, float)):
        minimum = round(float(minimum_at_30) * fps / 30)
        if duration < minimum:
            issues.append(
                TimelineIssue(
                    "blocked",
                    "readability",
                    f"Template requires at least {minimum} frames at {fps:g}fps",
                    segment_id,
                )
            )
    if isinstance(maximum_at_30, (int, float)):
        maximum = round(float(maximum_at_30) * fps / 30)
        if duration > maximum:
            issues.append(
                TimelineIssue(
                    "needs_review",
                    "timing",
                    f"Template exceeds recommended {maximum} frames at {fps:g}fps",
                    segment_id,
                )
            )


def _validate_assets(
    segment: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    fps: float,
    segment_duration: int,
    segment_id: str | None,
    public_root: Path | None,
    issues: list[TimelineIssue],
) -> None:
    asset_ids = segment.get("asset_ids", [])
    if not isinstance(asset_ids, list):
        issues.append(
            TimelineIssue("blocked", "schema", "asset_ids must be an array", segment_id)
        )
        return
    _validate_segment_media_layout(segment, assets, segment_id, issues)
    for asset_id_value in asset_ids:
        asset_id = str(asset_id_value)
        asset = assets.get(asset_id)
        if assets and asset is None:
            issues.append(
                TimelineIssue(
                    "blocked",
                    "asset_missing",
                    f"Unknown asset_id: {asset_id}",
                    segment_id,
                )
            )
            continue
        if asset is None:
            continue
        if asset.get("status") != "ready":
            issues.append(
                TimelineIssue(
                    "blocked",
                    "asset_not_ready",
                    f"Asset {asset_id} is not ready",
                    segment_id,
                )
            )
        runtime_path = asset.get("runtime_path")
        if (
            public_root
            and isinstance(runtime_path, str)
            and not (public_root / runtime_path).is_file()
        ):
            issues.append(
                TimelineIssue(
                    "blocked",
                    "asset_missing",
                    f"Runtime file does not exist: {runtime_path}",
                    segment_id,
                )
            )
        if asset.get("playback") == "complete":
            trim = segment.get("source_trim")
            if not isinstance(trim, dict) or trim.get("start_frame") != 0:
                issues.append(
                    TimelineIssue(
                        "blocked",
                        "complete_playback",
                        f"Asset {asset_id} must start from source frame 0",
                        segment_id,
                    )
                )
            source_duration = asset.get("duration_seconds")
            if isinstance(source_duration, (int, float)):
                expected = round(float(source_duration) * fps)
                if abs(segment_duration - expected) > 1:
                    issues.append(
                        TimelineIssue(
                            "blocked",
                            "complete_playback",
                            f"Asset {asset_id} expects about {expected} frames, got {segment_duration}",
                            segment_id,
                        )
                    )


def _validate_segment_media_layout(
    segment: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    segment_id: str | None,
    issues: list[TimelineIssue],
) -> None:
    layout = segment.get("media_layout")
    if not isinstance(layout, dict):
        return
    fit = layout.get("fit")
    strategy = layout.get("empty_space_strategy")
    if fit == "contain" and strategy in {None, "none"}:
        issues.append(
            TimelineIssue(
                "blocked",
                "unplanned_letterbox",
                "Contain media requires a non-empty visual strategy",
                segment_id,
            )
        )
    if fit == "contain" and not _nonempty_string(layout.get("blank_space_reason")):
        issues.append(
            TimelineIssue(
                "blocked",
                "blank_space_reason",
                "Contain media requires a recorded blank-space reason",
                segment_id,
            )
        )
    if fit not in {"cover", "focus_crop"}:
        return
    for asset_id in segment.get("asset_ids", []):
        asset = assets.get(str(asset_id))
        if asset is None or asset.get("type") not in {
            "screen_recording",
            "screenshot",
            "source_capture",
            "image",
            "b_roll",
        }:
            continue
        if asset.get("allow_crop") is not True:
            issues.append(
                TimelineIssue(
                    "blocked",
                    "crop_not_allowed",
                    f"Asset {asset_id} must explicitly allow crop for {fit}",
                    segment_id,
                )
            )


def _validate_audio(
    raw_audio: object, duration: int, issues: list[TimelineIssue]
) -> None:
    tracks = raw_audio if isinstance(raw_audio, list) else [raw_audio]
    valid_tracks = [track for track in tracks if isinstance(track, dict)]
    audible = [track for track in valid_tracks if track.get("audible") is True]
    if len(audible) != 1:
        issues.append(
            TimelineIssue(
                "blocked",
                "audio",
                f"Expected exactly one audible track, found {len(audible)}",
            )
        )
        return
    track = audible[0]
    if track.get("start_frame") != 0:
        issues.append(
            TimelineIssue("blocked", "audio", "Narration must start at frame 0")
        )
    audio_duration = track.get("duration_in_frames")
    if audio_duration != duration:
        issues.append(
            TimelineIssue(
                "blocked",
                "audio",
                f"Narration duration {audio_duration} does not equal composition duration {duration}",
            )
        )


def _validate_captions(
    raw_captions: object,
    assets: dict[str, dict[str, Any]],
    duration_frames: int,
    fps: float,
    public_root: Path | None,
    issues: list[TimelineIssue],
) -> None:
    if not isinstance(raw_captions, dict):
        issues.append(
            TimelineIssue(
                "blocked",
                "captions_missing",
                "Timeline must enable captions or record an explicit user opt-out",
            )
        )
        return
    enabled = raw_captions.get("enabled")
    if enabled is False:
        if raw_captions.get("explicit_user_request") is not True or not _nonempty_string(
            raw_captions.get("opt_out_reason")
        ):
            issues.append(
                TimelineIssue(
                    "blocked",
                    "captions_opt_out",
                    "Disabled captions require an explicit user request and recorded reason",
                )
            )
        return
    if enabled is not True:
        issues.append(
            TimelineIssue(
                "blocked",
                "captions_missing",
                "captions.enabled must be true unless explicitly opted out",
            )
        )
        return
    asset_id = raw_captions.get("asset_id")
    if not isinstance(asset_id, str) or not asset_id:
        issues.append(
            TimelineIssue(
                "blocked", "captions_asset", "Enabled captions need an asset_id"
            )
        )
        return
    asset = assets.get(asset_id)
    if assets and asset is None:
        issues.append(
            TimelineIssue(
                "blocked",
                "captions_asset",
                f"Unknown caption asset {asset_id}",
            )
        )
        return
    if asset is not None:
        if asset.get("status") != "ready":
            issues.append(
                TimelineIssue(
                    "blocked",
                    "captions_asset",
                    f"Caption asset {asset_id} is not ready",
                )
            )
        if asset.get("type") != "caption_json":
            issues.append(
                TimelineIssue(
                    "blocked",
                    "captions_asset",
                    f"Caption asset {asset_id} must use type caption_json",
                )
            )
    runtime_path = raw_captions.get("runtime_path")
    if not isinstance(runtime_path, str) and asset is not None:
        runtime_path = asset.get("runtime_path")
    if not isinstance(runtime_path, str) or not runtime_path:
        issues.append(
            TimelineIssue(
                "blocked",
                "captions_asset",
                "Enabled captions need a runtime_path",
            )
        )
        return
    if public_root is None:
        return
    caption_path = public_root / runtime_path
    if not caption_path.is_file():
        issues.append(
            TimelineIssue(
                "blocked",
                "captions_asset",
                f"Caption runtime file does not exist: {runtime_path}",
            )
        )
        return
    _validate_caption_file(caption_path, duration_frames, fps, issues)


def _validate_caption_file(
    path: Path,
    duration_frames: int,
    fps: float,
    issues: list[TimelineIssue],
) -> None:
    try:
        payload = read_json(path)
    except (TalkingCraftError, json.JSONDecodeError) as error:
        issues.append(
            TimelineIssue(
                "blocked", "captions_data", f"Cannot read caption JSON: {error}"
            )
        )
        return
    if not isinstance(payload, list) or not payload:
        issues.append(
            TimelineIssue(
                "blocked", "captions_data", "Caption JSON must be a non-empty array"
            )
        )
        return
    previous_start = -1.0
    composition_end_ms = duration_frames / fps * 1000
    for index, raw_cue in enumerate(payload):
        if not isinstance(raw_cue, dict):
            issues.append(
                TimelineIssue(
                    "blocked", "captions_data", f"Caption cue {index} is not an object"
                )
            )
            continue
        text = raw_cue.get("text")
        start_ms = raw_cue.get("startMs")
        end_ms = raw_cue.get("endMs")
        if (
            not _nonempty_string(text)
            or not isinstance(start_ms, (int, float))
            or not isinstance(end_ms, (int, float))
            or start_ms < 0
            or end_ms <= start_ms
        ):
            issues.append(
                TimelineIssue(
                    "blocked",
                    "captions_data",
                    f"Caption cue {index} has invalid text or timing",
                )
            )
            continue
        if float(start_ms) < previous_start:
            issues.append(
                TimelineIssue(
                    "blocked",
                    "captions_data",
                    f"Caption cue {index} starts before the previous cue",
                )
            )
        if float(end_ms) > composition_end_ms + 1000 / fps:
            issues.append(
                TimelineIssue(
                    "blocked",
                    "captions_data",
                    f"Caption cue {index} exceeds the Composition duration",
                )
            )
        previous_start = float(start_ms)


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _template_index(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    templates = registry.get("templates")
    if not isinstance(templates, list):
        raise TalkingCraftError("registry.templates must be an array")
    result: dict[str, dict[str, Any]] = {}
    for raw in templates:
        item = _require_object(raw, "template")
        template_id = item.get("id")
        if not isinstance(template_id, str):
            raise TalkingCraftError("Every registry template must have a string id")
        result[template_id] = item
    return result


def _asset_index(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    manifest = _require_object(read_json(path), "asset manifest")
    values = manifest.get("assets", [])
    if not isinstance(values, list):
        raise TalkingCraftError("asset manifest assets must be an array")
    return {
        str(item["asset_id"]): item
        for item in values
        if isinstance(item, dict) and "asset_id" in item
    }


def _require_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TalkingCraftError(f"{label} must be a JSON object")
    return value


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise TalkingCraftError(f"{label} must be a positive integer")
    return value


def _positive_number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or value <= 0:
        raise TalkingCraftError(f"{label} must be a positive number")
    return float(value)


def _integer_or_issue(
    value: object,
    label: str,
    segment_id: str | None,
    issues: list[TimelineIssue],
) -> int | None:
    if not isinstance(value, int):
        issues.append(
            TimelineIssue(
                "blocked", "schema", f"{label} must be an integer", segment_id
            )
        )
        return None
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a Ryan Talking Craft timeline"
    )
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--assets", type=Path)
    parser.add_argument("--public-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = validate_timeline(
            args.timeline,
            registry_path=args.registry,
            asset_manifest_path=args.assets,
            public_root=args.public_root,
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
