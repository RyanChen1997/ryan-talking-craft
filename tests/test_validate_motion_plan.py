from __future__ import annotations

import json
from pathlib import Path

from validate_motion_plan import validate_motion_plan


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _registry(tmp_path: Path) -> Path:
    return _write(
        tmp_path / "registry.json",
        {
            "templates": [
                {
                    "id": "EntranceCard@1",
                    "supportedIntents": ["claim"],
                    "motionMode": "entrance_only",
                },
                {
                    "id": "StateTransition@1",
                    "supportedIntents": ["claim", "contrast"],
                    "motionMode": "semantic_sequence",
                    "motionRoles": ["transform", "bad_to_better", "before_to_after"],
                },
            ]
        },
    )


def _function_map(tmp_path: Path, intent: str = "claim") -> Path:
    return _write(
        tmp_path / "function-map.json",
        {"modules": [{"segment_ids": ["S01"], "primary_intent": intent}]},
    )


def test_semantic_sequence_with_meaningful_beats_passes(tmp_path: Path) -> None:
    storyboard = _write(
        tmp_path / "storyboard.json",
        {
            "composition": {"fps": 30},
            "shots": [
                {
                    "shot_id": "SH01",
                    "segment_ids": ["S01"],
                    "duration_in_frames": 240,
                    "presenter_mode": "HIDDEN",
                    "template": "StateTransition@1",
                    "motion_plan": {
                        "role": "bad_to_better",
                        "initial_state": "扁平图片",
                        "trigger": {"text": "变成", "at_frame": 90},
                        "beats": [
                            {"at_frame": 30, "action": "标出问题", "purpose": "建立旧状态"},
                            {"at_frame": 100, "action": "展开图层", "purpose": "展示结构变化"},
                        ],
                        "final_state": "可编辑图层",
                        "removal_cost": "观众无法看见扁平内容如何获得可编辑结构",
                        "hold_frames": 60,
                    },
                }
            ],
        },
    )

    report = validate_motion_plan(storyboard, _registry(tmp_path), _function_map(tmp_path))

    assert report.passed is True
    assert report.issues == ()


def test_timeline_segments_can_be_validated_after_build(tmp_path: Path) -> None:
    timeline = _write(
        tmp_path / "timeline-final.json",
        {
            "composition": {"fps": 30},
            "segments": [
                {
                    "shot_id": "SH01",
                    "segment_id": "S01",
                    "duration_in_frames": 240,
                    "presenter_mode": "HIDDEN",
                    "template": "StateTransition@1",
                    "motion_plan": {
                        "role": "bad_to_better",
                        "initial_state": "旧状态",
                        "trigger": {"text": "变成", "at_frame": 90},
                        "beats": [
                            {"at_frame": 30, "action": "建立旧态", "purpose": "说明问题"},
                            {"at_frame": 100, "action": "替换新态", "purpose": "说明改善"},
                        ],
                        "final_state": "新状态",
                        "removal_cost": "无法看见改善过程",
                        "hold_frames": 60,
                    },
                }
            ],
        },
    )

    report = validate_motion_plan(timeline, _registry(tmp_path), _function_map(tmp_path))

    assert report.passed is True


def test_built_timeline_cannot_drop_approved_motion_plan(tmp_path: Path) -> None:
    approved = _write(
        tmp_path / "storyboard.json",
        {
            "shots": [
                {
                    "shot_id": "SH01",
                    "duration_in_frames": 180,
                    "template": "EntranceCard@1",
                    "motion_plan": {
                        "role": "reading_hold",
                        "beats": [],
                        "hold_frames": 150,
                        "static_hold_reason": "需要阅读来源",
                    },
                }
            ]
        },
    )
    timeline = _write(
        tmp_path / "timeline-final.json",
        {
            "segments": [
                {
                    "shot_id": "SH01",
                    "segment_id": "S01",
                    "duration_in_frames": 180,
                    "presenter_mode": "MEDIUM",
                    "template": "EntranceCard@1",
                }
            ]
        },
    )

    report = validate_motion_plan(
        timeline,
        _registry(tmp_path),
        reference_storyboard_path=approved,
    )

    assert report.passed is False
    assert any(issue.category == "motion_plan_not_propagated" for issue in report.issues)


def test_built_timeline_cannot_drop_approved_media_layout(tmp_path: Path) -> None:
    approved = _write(
        tmp_path / "storyboard.json",
        {
            "shots": [
                {
                    "shot_id": "SH01",
                    "duration_in_frames": 180,
                    "template": "EntranceCard@1",
                    "media_layout": {
                        "fit": "focus_crop",
                        "empty_space_strategy": "none",
                        "camera_bounds_clamped": True,
                    },
                }
            ]
        },
    )
    timeline = _write(
        tmp_path / "timeline-final.json",
        {
            "segments": [
                {
                    "shot_id": "SH01",
                    "segment_id": "S01",
                    "duration_in_frames": 180,
                    "presenter_mode": "MEDIUM",
                    "template": "EntranceCard@1",
                }
            ]
        },
    )

    report = validate_motion_plan(
        timeline,
        _registry(tmp_path),
        reference_storyboard_path=approved,
    )

    assert report.passed is False
    assert any(issue.category == "media_layout_not_propagated" for issue in report.issues)


def test_long_hidden_entrance_only_shot_is_blocked(tmp_path: Path) -> None:
    storyboard = _write(
        tmp_path / "storyboard.json",
        {
            "composition": {"fps": 30},
            "shots": [
                {
                    "shot_id": "SH01",
                    "segment_ids": ["S01"],
                    "duration_in_frames": 320,
                    "presenter_mode": "HIDDEN",
                    "template": "EntranceCard@1",
                }
            ],
        },
    )

    report = validate_motion_plan(storyboard, _registry(tmp_path), _function_map(tmp_path))

    assert report.passed is False
    assert any(issue.category == "unexplained_static_hold" for issue in report.issues)


def test_entrance_only_template_cannot_claim_semantic_transform(tmp_path: Path) -> None:
    storyboard = _write(
        tmp_path / "storyboard.json",
        {
            "shots": [
                {
                    "shot_id": "SH01",
                    "segment_ids": ["S01"],
                    "duration_in_frames": 180,
                    "presenter_mode": "HIDDEN",
                    "template": "EntranceCard@1",
                    "motion_plan": {
                        "role": "transform",
                        "initial_state": "旧",
                        "beats": [
                            {"at_frame": 20, "action": "显示旧态", "purpose": "建立问题"},
                            {"at_frame": 80, "action": "替换新态", "purpose": "展示改变"},
                        ],
                        "final_state": "新",
                        "removal_cost": "观众无法看见升级过程",
                        "hold_frames": 40,
                    },
                }
            ]
        },
    )

    report = validate_motion_plan(storyboard, _registry(tmp_path), _function_map(tmp_path))

    assert report.passed is False
    assert any(issue.category == "template_motion_mismatch" for issue in report.issues)


def test_semantic_sequence_requires_narration_trigger(tmp_path: Path) -> None:
    storyboard = _write(
        tmp_path / "storyboard.json",
        {
            "shots": [
                {
                    "shot_id": "SH01",
                    "segment_ids": ["S01"],
                    "duration_in_frames": 180,
                    "presenter_mode": "HIDDEN",
                    "template": "StateTransition@1",
                    "motion_plan": {
                        "role": "bad_to_better",
                        "initial_state": "旧状态",
                        "beats": [
                            {"at_frame": 20, "action": "建立旧态", "purpose": "显示问题"},
                            {"at_frame": 80, "action": "替换新态", "purpose": "显示改善"},
                        ],
                        "final_state": "新状态",
                        "removal_cost": "看不见改善过程",
                        "hold_frames": 40,
                    },
                }
            ]
        },
    )

    report = validate_motion_plan(storyboard, _registry(tmp_path), _function_map(tmp_path))

    assert report.passed is False
    assert any(issue.category == "missing_trigger" for issue in report.issues)


def test_registered_semantic_template_must_support_motion_role(tmp_path: Path) -> None:
    storyboard = _write(
        tmp_path / "storyboard.json",
        {
            "shots": [
                {
                    "shot_id": "SH01",
                    "segment_ids": ["S01"],
                    "duration_in_frames": 180,
                    "presenter_mode": "HIDDEN",
                    "template": "StateTransition@1",
                    "motion_plan": {
                        "role": "draw",
                        "initial_state": "空坐标系",
                        "beats": [
                            {"at_frame": 20, "action": "画第一条线", "purpose": "建立基准"},
                            {"at_frame": 80, "action": "画第二条线", "purpose": "建立对比"},
                        ],
                        "final_state": "双线图",
                        "removal_cost": "观众无法看见两条线的先后关系",
                        "hold_frames": 40,
                    },
                }
            ]
        },
    )

    report = validate_motion_plan(storyboard, _registry(tmp_path), _function_map(tmp_path))

    assert report.passed is False
    assert any(issue.category == "motion_role_mismatch" for issue in report.issues)


def test_explicit_custom_semantic_motion_can_pass_design_validation(tmp_path: Path) -> None:
    storyboard = _write(
        tmp_path / "storyboard.json",
        {
            "shots": [
                {
                    "shot_id": "SH01",
                    "segment_ids": ["S01"],
                    "duration_in_frames": 180,
                    "presenter_mode": "HIDDEN",
                    "template": "custom-animation-required",
                    "motion_plan": {
                        "role": "aggregate",
                        "initial_state": "六个金额点",
                        "trigger": {"text": "加起来", "at_frame": 80},
                        "beats": [
                            {"at_frame": 25, "action": "金额点逐个出现", "purpose": "建立分项"},
                            {"at_frame": 90, "action": "点聚合为总量", "purpose": "演出求和"},
                        ],
                        "final_state": "一个总量球",
                        "removal_cost": "观众需要自行心算总量",
                        "hold_frames": 60,
                        "custom_animation_required": True,
                    },
                }
            ]
        },
    )

    report = validate_motion_plan(storyboard, _registry(tmp_path), _function_map(tmp_path))

    assert report.passed is True


def test_static_hold_rejects_string_trigger(tmp_path: Path) -> None:
    storyboard = _write(
        tmp_path / "storyboard.json",
        {
            "shots": [
                {
                    "shot_id": "SH01",
                    "segment_ids": ["S01"],
                    "duration_in_frames": 180,
                    "presenter_mode": "HIDDEN",
                    "template": "EntranceCard@1",
                    "motion_plan": {
                        "role": "reading_hold",
                        "trigger": "读到来源",
                        "beats": [],
                        "hold_frames": 150,
                        "static_hold_reason": "需要阅读来源",
                    },
                }
            ]
        },
    )

    report = validate_motion_plan(storyboard, _registry(tmp_path), _function_map(tmp_path))

    assert report.passed is False
    assert any(issue.category == "invalid_trigger" for issue in report.issues)


def test_static_reading_hold_needs_reason(tmp_path: Path) -> None:
    storyboard = _write(
        tmp_path / "storyboard.json",
        {
            "shots": [
                {
                    "shot_id": "SH01",
                    "segment_ids": ["S01"],
                    "duration_in_frames": 180,
                    "presenter_mode": "HIDDEN",
                    "template": "EntranceCard@1",
                    "motion_plan": {"role": "reading_hold", "beats": [], "hold_frames": 150},
                }
            ]
        },
    )

    report = validate_motion_plan(storyboard, _registry(tmp_path), _function_map(tmp_path))

    assert report.passed is False
    assert any(issue.category == "missing_static_hold_reason" for issue in report.issues)
