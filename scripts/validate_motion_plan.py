from __future__ import annotations

import argparse
import json
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
STATIC_ROLES = {
    "none",
    "reading_hold",
    "presenter_hold",
    "recorded_action",
    "deliberate_stillness",
}


@dataclass(frozen=True)
class MotionIssue:
    severity: str
    category: str
    shot_id: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "category": self.category,
            "shot_id": self.shot_id,
            "message": self.message,
        }


@dataclass(frozen=True)
class MotionReport:
    passed: bool
    shot_count: int
    issues: tuple[MotionIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "shot_count": self.shot_count,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def validate_motion_plan(
    storyboard_path: Path,
    registry_path: Path,
    function_map_path: Path | None = None,
    reference_storyboard_path: Path | None = None,
) -> MotionReport:
    storyboard = _require_object(read_json(storyboard_path), "storyboard")
    registry = _require_object(read_json(registry_path), "registry")
    raw_shots = storyboard.get("shots")
    collection_label = "storyboard.shots"
    if raw_shots is None:
        raw_shots = storyboard.get("segments")
        collection_label = "timeline.segments"
    shots = _object_list(raw_shots, collection_label)
    templates = _template_index(_object_list(registry.get("templates"), "registry.templates"))
    modules = (
        _object_list(
            _require_object(read_json(function_map_path), "function map").get("modules"),
            "function_map.modules",
        )
        if function_map_path
        else []
    )
    fps = _storyboard_fps(storyboard)
    reference_plans = (
        _motion_plan_index(reference_storyboard_path) if reference_storyboard_path else {}
    )
    reference_layouts = (
        _media_layout_index(reference_storyboard_path) if reference_storyboard_path else {}
    )
    issues: list[MotionIssue] = []

    for shot in shots:
        shot_id = _shot_id(shot)
        duration = _positive_int(shot.get("duration_in_frames"), f"{shot_id}.duration_in_frames")
        if shot_id in reference_layouts:
            current_layout = shot.get("media_layout")
            if not isinstance(current_layout, dict):
                issues.append(
                    MotionIssue(
                        "blocked",
                        "media_layout_not_propagated",
                        shot_id,
                        "Approved storyboard media_layout is missing from the built timeline",
                    )
                )
            elif current_layout != reference_layouts[shot_id]:
                issues.append(
                    MotionIssue(
                        "blocked",
                        "media_layout_drift",
                        shot_id,
                        "Built timeline media_layout differs from the approved storyboard",
                    )
                )
        if shot_id in reference_plans:
            current_plan = shot.get("motion_plan")
            if not isinstance(current_plan, dict):
                issues.append(
                    MotionIssue(
                        "blocked",
                        "motion_plan_not_propagated",
                        shot_id,
                        "Approved storyboard motion_plan is missing from the built timeline",
                    )
                )
            elif current_plan != reference_plans[shot_id]:
                issues.append(
                    MotionIssue(
                        "blocked",
                        "motion_plan_drift",
                        shot_id,
                        "Built timeline motion_plan differs from the approved storyboard",
                    )
                )
        template_id = shot.get("template")
        metadata = templates.get(template_id) if isinstance(template_id, str) else None
        plan = shot.get("motion_plan")
        if metadata is None:
            if isinstance(plan, dict) and plan.get("custom_animation_required") is True:
                _check_plan(shot_id, duration, fps, "semantic_sequence", plan, None, issues)
                continue
            issues.append(
                MotionIssue("blocked", "unknown_template", shot_id, f"Unknown template: {template_id!r}")
            )
            continue
        intent = _related_intent(shot, modules)
        supported_intents = _string_set(metadata.get("supportedIntents"))
        if intent and intent not in supported_intents:
            issues.append(
                MotionIssue(
                    "blocked",
                    "intent_mismatch",
                    shot_id,
                    f"Intent {intent!r} is not supported by {template_id}",
                )
            )

        motion_mode = metadata.get("motionMode")
        if not isinstance(plan, dict):
            _check_missing_plan(shot, shot_id, duration, fps, motion_mode, issues)
            continue
        _check_plan(shot_id, duration, fps, motion_mode, plan, metadata, issues)

    return MotionReport(
        passed=not any(issue.severity == "blocked" for issue in issues),
        shot_count=len(shots),
        issues=tuple(issues),
    )


def _check_missing_plan(
    shot: dict[str, Any],
    shot_id: str,
    duration: int,
    fps: float,
    motion_mode: object,
    issues: list[MotionIssue],
) -> None:
    presenter_mode = shot.get("presenter_mode")
    if motion_mode == "semantic_sequence":
        issues.append(
            MotionIssue(
                "blocked",
                "missing_motion_plan",
                shot_id,
                "Semantic-sequence template requires an explicit motion_plan",
            )
        )
        return
    entrance_budget = round(fps * 1.0)
    if motion_mode == "entrance_only" and presenter_mode == "HIDDEN" and duration > entrance_budget * 3:
        issues.append(
            MotionIssue(
                "blocked",
                "unexplained_static_hold",
                shot_id,
                "Long presenter-hidden shot uses entrance-only motion without semantic beats or a static-hold reason",
            )
        )
    elif motion_mode not in {"presenter", "recorded"}:
        issues.append(
            MotionIssue(
                "needs_review",
                "missing_motion_plan",
                shot_id,
                "Record the motion role, trigger, beats, final state, and hold reason",
            )
        )


def _check_plan(
    shot_id: str,
    duration: int,
    fps: float,
    motion_mode: object,
    plan: dict[str, Any],
    metadata: dict[str, Any] | None,
    issues: list[MotionIssue],
) -> None:
    role = plan.get("role")
    if not isinstance(role, str) or role not in SEMANTIC_ROLES | STATIC_ROLES:
        issues.append(
            MotionIssue("blocked", "invalid_motion_role", shot_id, f"Invalid motion role: {role!r}")
        )
        return
    beats = plan.get("beats")
    beat_list = beats if isinstance(beats, list) else []
    if role in SEMANTIC_ROLES:
        supported_roles = _string_set(metadata.get("motionRoles")) if metadata else set()
        if supported_roles and role not in supported_roles:
            issues.append(
                MotionIssue(
                    "blocked",
                    "motion_role_mismatch",
                    shot_id,
                    f"Motion role {role!r} is not supported by the selected template",
                )
            )
        if motion_mode == "entrance_only":
            issues.append(
                MotionIssue(
                    "blocked",
                    "template_motion_mismatch",
                    shot_id,
                    "Semantic state change cannot be delegated to an entrance-only template",
                )
            )
        trigger = plan.get("trigger")
        if not isinstance(trigger, dict) or not _nonempty_string(trigger.get("text")):
            issues.append(
                MotionIssue(
                    "blocked",
                    "missing_trigger",
                    shot_id,
                    "Semantic motion requires the narration trigger text and local at_frame",
                )
            )
        else:
            trigger_frame = trigger.get("at_frame")
            if (
                not isinstance(trigger_frame, int)
                or isinstance(trigger_frame, bool)
                or trigger_frame < 0
                or trigger_frame >= duration
            ):
                issues.append(
                    MotionIssue(
                        "blocked",
                        "invalid_trigger_frame",
                        shot_id,
                        "Trigger at_frame must be inside the shot",
                    )
                )
            else:
                beat_frames = [
                    beat.get("at_frame")
                    for beat in beat_list
                    if isinstance(beat, dict) and isinstance(beat.get("at_frame"), int)
                ]
                if beat_frames and min(abs(frame - trigger_frame) for frame in beat_frames) > fps * 1.5:
                    issues.append(
                        MotionIssue(
                            "needs_review",
                            "trigger_far_from_motion",
                            shot_id,
                            "No semantic beat occurs within 1.5 seconds of the narration trigger",
                        )
                    )
        if not _nonempty_string(plan.get("initial_state")) or not _nonempty_string(plan.get("final_state")):
            issues.append(
                MotionIssue(
                    "blocked",
                    "missing_state_pair",
                    shot_id,
                    "Semantic motion requires non-empty initial_state and final_state",
                )
            )
        if not _nonempty_string(plan.get("removal_cost")):
            issues.append(
                MotionIssue(
                    "blocked",
                    "missing_removal_cost",
                    shot_id,
                    "Semantic motion must state what understanding is lost if the motion is removed",
                )
            )
        if len(beat_list) < 2:
            issues.append(
                MotionIssue(
                    "blocked",
                    "insufficient_semantic_beats",
                    shot_id,
                    "Semantic motion requires at least two meaningful beats",
                )
            )
    elif role in {"none", "reading_hold", "presenter_hold", "deliberate_stillness"}:
        static_trigger = plan.get("trigger")
        if static_trigger is not None and (
            not isinstance(static_trigger, dict)
            or not _nonempty_string(static_trigger.get("text"))
            or not isinstance(static_trigger.get("at_frame"), int)
            or isinstance(static_trigger.get("at_frame"), bool)
            or static_trigger["at_frame"] < 0
            or static_trigger["at_frame"] >= duration
        ):
            issues.append(
                MotionIssue(
                    "blocked",
                    "invalid_trigger",
                    shot_id,
                    "When present, trigger must contain text and an in-range local at_frame",
                )
            )
        if not _nonempty_string(plan.get("static_hold_reason")):
            issues.append(
                MotionIssue(
                    "blocked",
                    "missing_static_hold_reason",
                    shot_id,
                    "Static or reading hold requires static_hold_reason",
                )
            )

    previous_frame = -1
    for index, beat in enumerate(beat_list):
        if not isinstance(beat, dict):
            issues.append(
                MotionIssue(
                    "blocked",
                    "invalid_beat",
                    shot_id,
                    f"Beat {index} must be an object",
                )
            )
            continue
        at_frame = beat.get("at_frame")
        if not isinstance(at_frame, int) or isinstance(at_frame, bool):
            issues.append(
                MotionIssue(
                    "blocked",
                    "invalid_beat_frame",
                    shot_id,
                    f"Beat {index} needs an integer at_frame",
                )
            )
            continue
        if at_frame < 0 or at_frame >= duration:
            issues.append(
                MotionIssue(
                    "blocked",
                    "beat_out_of_range",
                    shot_id,
                    f"Beat {index} frame {at_frame} is outside 0..{duration - 1}",
                )
            )
        if at_frame < previous_frame:
            issues.append(
                MotionIssue(
                    "blocked",
                    "beats_not_monotonic",
                    shot_id,
                    "Beat frames must be monotonic",
                )
            )
        previous_frame = at_frame
        if not _nonempty_string(beat.get("action")) or not _nonempty_string(beat.get("purpose")):
            issues.append(
                MotionIssue(
                    "blocked",
                    "beat_without_meaning",
                    shot_id,
                    f"Beat {index} needs action and purpose",
                )
            )

    hold_frames = plan.get("hold_frames", 0)
    if not isinstance(hold_frames, int) or isinstance(hold_frames, bool) or hold_frames < 0:
        issues.append(
            MotionIssue("blocked", "invalid_hold", shot_id, "hold_frames must be a non-negative integer")
        )
    elif beat_list and previous_frame >= 0 and previous_frame + hold_frames > duration:
        issues.append(
            MotionIssue(
                "blocked",
                "hold_out_of_range",
                shot_id,
                "Last beat plus hold_frames exceeds shot duration",
            )
        )


def _related_intent(shot: dict[str, Any], modules: list[dict[str, Any]]) -> str | None:
    shot_segments = _string_set(shot.get("segment_ids"))
    segment_id = shot.get("segment_id")
    if isinstance(segment_id, str) and segment_id:
        shot_segments.add(segment_id)
    for module in modules:
        if shot_segments.intersection(_string_set(module.get("segment_ids"))):
            intent = module.get("primary_intent")
            return intent if isinstance(intent, str) else None
    return None


def _storyboard_fps(storyboard: dict[str, Any]) -> float:
    composition = storyboard.get("composition")
    if isinstance(composition, dict) and isinstance(composition.get("fps"), (int, float)):
        return float(composition["fps"])
    return 30.0


def _motion_plan_index(storyboard_path: Path) -> dict[str, dict[str, Any]]:
    payload = _require_object(read_json(storyboard_path), "reference storyboard")
    shots = _object_list(payload.get("shots"), "reference storyboard.shots")
    result: dict[str, dict[str, Any]] = {}
    for shot in shots:
        plan = shot.get("motion_plan")
        if isinstance(plan, dict):
            result[_shot_id(shot)] = plan
    return result


def _media_layout_index(storyboard_path: Path) -> dict[str, dict[str, Any]]:
    payload = _require_object(read_json(storyboard_path), "reference storyboard")
    shots = _object_list(payload.get("shots"), "reference storyboard.shots")
    result: dict[str, dict[str, Any]] = {}
    for shot in shots:
        layout = shot.get("media_layout")
        if isinstance(layout, dict):
            result[_shot_id(shot)] = layout
    return result


def _template_index(templates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for template in templates:
        template_id = template.get("id")
        if not isinstance(template_id, str) or not template_id:
            raise TalkingCraftError("Every registry template needs a non-empty id")
        if template_id in result:
            raise TalkingCraftError(f"Duplicate template id: {template_id}")
        result[template_id] = template
    return result


def _shot_id(shot: dict[str, Any]) -> str:
    value = shot.get("shot_id")
    if not isinstance(value, str) or not value:
        raise TalkingCraftError("Every storyboard shot needs a non-empty shot_id")
    return value


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise TalkingCraftError(f"{label} must be a positive integer")
    return value


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str) and item}


def _object_list(value: object, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise TalkingCraftError(f"{label} must be an array of objects")
    return value


def _require_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TalkingCraftError(f"{label} must be a JSON object")
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate semantic motion plans")
    parser.add_argument("storyboard", type=Path)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--function-map", type=Path)
    parser.add_argument("--reference-storyboard", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = validate_motion_plan(
            args.storyboard,
            args.registry,
            args.function_map,
            args.reference_storyboard,
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
