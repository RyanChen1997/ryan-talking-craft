from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import TalkingCraftError, read_json, write_json

_MEDIA_ASSET_TYPES = {
    "screen_recording",
    "screenshot",
    "source_capture",
    "image",
    "b_roll",
}
_MEDIA_FITS = {"cover", "focus_crop", "contain", "native"}
_EMPTY_SPACE_STRATEGIES = {
    "none",
    "designed_matte",
    "adjacent_content",
    "blurred_backdrop",
}


@dataclass(frozen=True)
class DesignIssue:
    severity: str
    category: str
    message: str
    target_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "category": self.category,
            "target_id": self.target_id,
            "message": self.message,
        }


@dataclass(frozen=True)
class DesignReport:
    passed: bool
    function_count: int
    shot_count: int
    asset_count: int
    issues: tuple[DesignIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "function_count": self.function_count,
            "shot_count": self.shot_count,
            "asset_count": self.asset_count,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def validate_design(
    function_map_path: Path,
    storyboard_path: Path,
    asset_manifest_path: Path,
) -> DesignReport:
    """Cross-check function-map, storyboard, and asset-manifest references."""
    function_map = _require_object(read_json(function_map_path), "function map")
    storyboard = _require_object(read_json(storyboard_path), "storyboard")
    manifest = _require_object(read_json(asset_manifest_path), "asset manifest")
    modules = _object_list(function_map.get("modules"), "function_map.modules")
    shots = _object_list(storyboard.get("shots"), "storyboard.shots")
    assets = _asset_index(_object_list(manifest.get("assets"), "asset_manifest.assets"))
    issues: list[DesignIssue] = []

    _check_unique_ids(modules, "function_id", "function", issues)
    _check_unique_ids(shots, "shot_id", "shot", issues)
    _check_module_references(modules, shots, assets, issues)
    _check_shot_references(shots, modules, assets, issues)
    _check_media_layouts(shots, assets, issues)
    _check_required_asset_usage(storyboard, shots, assets, issues)

    return DesignReport(
        passed=not any(issue.severity == "blocked" for issue in issues),
        function_count=len(modules),
        shot_count=len(shots),
        asset_count=len(assets),
        issues=tuple(issues),
    )


def _check_unique_ids(
    entries: list[dict[str, Any]],
    field: str,
    label: str,
    issues: list[DesignIssue],
) -> None:
    seen: set[str] = set()
    for entry in entries:
        value = entry.get(field)
        target_id = str(value) if value is not None else None
        if not target_id:
            issues.append(DesignIssue("blocked", "schema", f"Missing {field}"))
        elif target_id in seen:
            issues.append(
                DesignIssue(
                    "blocked", "duplicate_id", f"Duplicate {label} ID", target_id
                )
            )
        else:
            seen.add(target_id)


def _check_module_references(
    modules: list[dict[str, Any]],
    shots: list[dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    issues: list[DesignIssue],
) -> None:
    for module in modules:
        function_id = _optional_id(module.get("function_id"))
        module_assets = _string_set(module.get("asset_ids"))
        related_shots = [shot for shot in shots if _entries_related(module, shot)]
        if not related_shots:
            issues.append(
                DesignIssue(
                    "blocked",
                    "function_without_shot",
                    "Function module is not represented by any storyboard shot",
                    function_id,
                )
            )
            continue
        related_assets = set().union(
            *(_string_set(shot.get("asset_ids")) for shot in related_shots)
        )
        for asset_id in module_assets:
            if asset_id not in assets:
                issues.append(
                    DesignIssue(
                        "blocked",
                        "unknown_asset",
                        f"Function references unknown asset {asset_id}",
                        function_id,
                    )
                )
            if asset_id not in related_assets and not _is_explicit_backup(
                module, asset_id
            ):
                issues.append(
                    DesignIssue(
                        "blocked",
                        "dangling_function_asset",
                        f"Function lists {asset_id}, but no related storyboard shot uses it or marks it backup",
                        function_id,
                    )
                )


def _check_shot_references(
    shots: list[dict[str, Any]],
    modules: list[dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    issues: list[DesignIssue],
) -> None:
    for shot in shots:
        shot_id = _optional_id(shot.get("shot_id"))
        if not any(_entries_related(module, shot) for module in modules):
            issues.append(
                DesignIssue(
                    "blocked",
                    "shot_without_function",
                    "Storyboard shot is not linked to a function module",
                    shot_id,
                )
            )
        for asset_id in _string_set(shot.get("asset_ids")):
            asset = assets.get(asset_id)
            if asset is None:
                issues.append(
                    DesignIssue(
                        "blocked",
                        "unknown_asset",
                        f"Shot references unknown asset {asset_id}",
                        shot_id,
                    )
                )
                continue
            if asset.get("status") != "ready":
                issues.append(
                    DesignIssue(
                        "blocked",
                        "asset_not_ready",
                        f"Shot uses asset {asset_id} with status {asset.get('status')!r}",
                        shot_id,
                    )
                )


def _check_media_layouts(
    shots: list[dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    issues: list[DesignIssue],
) -> None:
    for shot in shots:
        shot_id = _optional_id(shot.get("shot_id"))
        media_assets = [
            assets[asset_id]
            for asset_id in _string_set(shot.get("asset_ids"))
            if asset_id in assets and assets[asset_id].get("type") in _MEDIA_ASSET_TYPES
        ]
        if not media_assets:
            continue
        layout = shot.get("media_layout")
        if not isinstance(layout, dict):
            issues.append(
                DesignIssue(
                    "blocked",
                    "media_layout_missing",
                    "Media-led shot must define fit, empty-space strategy, and camera bounds",
                    shot_id,
                )
            )
            continue
        fit = layout.get("fit")
        strategy = layout.get("empty_space_strategy")
        if fit not in _MEDIA_FITS:
            issues.append(
                DesignIssue(
                    "blocked",
                    "media_layout_fit",
                    f"Unsupported media fit {fit!r}",
                    shot_id,
                )
            )
        if strategy not in _EMPTY_SPACE_STRATEGIES:
            issues.append(
                DesignIssue(
                    "blocked",
                    "media_layout_empty_space",
                    f"Unsupported empty-space strategy {strategy!r}",
                    shot_id,
                )
            )
        if fit == "contain":
            if strategy in {None, "none"}:
                issues.append(
                    DesignIssue(
                        "blocked",
                        "unplanned_letterbox",
                        "Contain cannot use an empty or none empty-space strategy",
                        shot_id,
                    )
                )
            if not _nonempty_string(layout.get("blank_space_reason")):
                issues.append(
                    DesignIssue(
                        "blocked",
                        "blank_space_reason",
                        "Contain requires a reason explaining why the full asset and remaining space are intentional",
                        shot_id,
                    )
                )
        if fit == "focus_crop" and not _valid_normalized_rect(
            layout.get("focal_region")
        ):
            issues.append(
                DesignIssue(
                    "blocked",
                    "focal_region",
                    "focus_crop requires a normalized focal_region inside the source",
                    shot_id,
                )
            )
        if fit in {"cover", "focus_crop"}:
            for asset in media_assets:
                if asset.get("allow_crop") is not True:
                    issues.append(
                        DesignIssue(
                            "blocked",
                            "crop_not_allowed",
                            f"Asset {asset.get('asset_id')} must explicitly allow crop for {fit}",
                            shot_id,
                        )
                    )
        evidence_types = {str(asset.get("type")) for asset in media_assets}
        if strategy == "blurred_backdrop" and evidence_types.intersection(
            {"screen_recording", "screenshot", "source_capture"}
        ):
            issues.append(
                DesignIssue(
                    "blocked",
                    "evidence_backdrop",
                    "Blurred backdrops are not allowed behind UI or evidence media",
                    shot_id,
                )
            )
        if shot.get("template") == "EvidenceFocusSequence@1" and layout.get(
            "camera_bounds_clamped"
        ) is not True:
            issues.append(
                DesignIssue(
                    "blocked",
                    "camera_bounds",
                    "Evidence focus camera must clamp translation to media bounds",
                    shot_id,
                )
            )


def _valid_normalized_rect(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    numbers = [value.get(key) for key in ("x", "y", "width", "height")]
    if not all(isinstance(number, (int, float)) for number in numbers):
        return False
    x, y, width, height = (float(number) for number in numbers)
    return (
        x >= 0
        and y >= 0
        and width > 0
        and height > 0
        and x + width <= 1
        and y + height <= 1
    )


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_required_asset_usage(
    storyboard: dict[str, Any],
    shots: list[dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    issues: list[DesignIssue],
) -> None:
    used_assets = set().union(*(_string_set(shot.get("asset_ids")) for shot in shots))
    audio = storyboard.get("audio")
    if isinstance(audio, dict) and isinstance(audio.get("asset_id"), str):
        used_assets.add(audio["asset_id"])
    for asset_id, asset in assets.items():
        if asset.get("required") is not True or asset_id in used_assets:
            continue
        if _asset_usage(asset) in {"backup", "reference_only", "not_used"}:
            continue
        issues.append(
            DesignIssue(
                "needs_review",
                "required_asset_unused",
                f"Required asset {asset_id} is not used by storyboard or audio and has no explicit usage status",
                asset_id,
            )
        )


def _entries_related(module: dict[str, Any], shot: dict[str, Any]) -> bool:
    module_segments = _string_set(module.get("segment_ids"))
    shot_segments = _string_set(shot.get("segment_ids"))
    if (
        module_segments
        and shot_segments
        and module_segments.intersection(shot_segments)
    ):
        return True
    module_start = _number_or_none(module.get("start_ms"))
    module_end = _number_or_none(module.get("end_ms"))
    shot_start = _number_or_none(shot.get("start_ms"))
    shot_end = _number_or_none(shot.get("end_ms"))
    if None in {module_start, module_end, shot_start, shot_end}:
        return False
    return bool(module_start < shot_end and shot_start < module_end)


def _is_explicit_backup(module: dict[str, Any], asset_id: str) -> bool:
    backup_assets = _string_set(module.get("backup_asset_ids"))
    optional_assets = _string_set(module.get("optional_asset_ids"))
    return asset_id in backup_assets or asset_id in optional_assets


def _asset_usage(asset: dict[str, Any]) -> str | None:
    for key in ("usage_status", "design_usage", "usage"):
        value = asset.get(key)
        if isinstance(value, str):
            return value
    return None


def _asset_index(values: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        asset_id = value.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            raise TalkingCraftError("Every asset must have a non-empty asset_id")
        if asset_id in result:
            raise TalkingCraftError(f"Duplicate asset_id: {asset_id}")
        result[asset_id] = value
    return result


def _object_list(value: object, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise TalkingCraftError(f"{label} must be an array")
    if not all(isinstance(item, dict) for item in value):
        raise TalkingCraftError(f"Every item in {label} must be an object")
    return value


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value if isinstance(item, str) and item}


def _optional_id(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _number_or_none(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _require_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TalkingCraftError(f"{label} must be a JSON object")
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cross-check talking-craft design artifacts"
    )
    parser.add_argument("function_map", type=Path)
    parser.add_argument("storyboard", type=Path)
    parser.add_argument("asset_manifest", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = validate_design(
            args.function_map, args.storyboard, args.asset_manifest
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
