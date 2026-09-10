from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import TalkingCraftError, read_json, write_json


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def intersects(self, other: Rect, *, tolerance: float = 1.0) -> bool:
        return not (
            self.right <= other.x + tolerance
            or other.right <= self.x + tolerance
            or self.bottom <= other.y + tolerance
            or other.bottom <= self.y + tolerance
        )


@dataclass(frozen=True)
class VisualIssue:
    severity: str
    category: str
    frame: int
    element_id: str
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "category": self.category,
            "frame": self.frame,
            "element_id": self.element_id,
            "message": self.message,
        }


@dataclass(frozen=True)
class VisualReport:
    passed: bool
    checked_frames: int
    checked_elements: int
    issues: tuple[VisualIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "checked_frames": self.checked_frames,
            "checked_elements": self.checked_elements,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def run_visual_qa(
    snapshot_path: Path, *, min_font_size_1080: float = 24
) -> VisualReport:
    """Validate a browser-collected QA layout snapshot."""
    payload = _require_object(read_json(snapshot_path), "snapshot")
    canvas = _require_object(payload.get("canvas"), "snapshot.canvas")
    canvas_width = _positive_number(canvas.get("width"), "canvas.width")
    canvas_height = _positive_number(canvas.get("height"), "canvas.height")
    frames = payload.get("frames")
    if not isinstance(frames, list) or not frames:
        raise TalkingCraftError("snapshot.frames must be a non-empty array")

    issues: list[VisualIssue] = []
    checked_elements = 0
    minimum_font_size = min_font_size_1080 * canvas_height / 1080
    for raw_frame in frames:
        frame_entry = _require_object(raw_frame, "frame entry")
        frame_number = _integer(frame_entry.get("frame"), "frame.frame")
        raw_elements = frame_entry.get("elements", [])
        if not isinstance(raw_elements, list):
            raise TalkingCraftError("frame.elements must be an array")
        elements = [_parse_element(raw, frame_number) for raw in raw_elements]
        checked_elements += len(elements)
        _check_elements(
            elements,
            frame_number,
            canvas_width,
            canvas_height,
            minimum_font_size,
            issues,
        )

    return VisualReport(
        passed=not any(issue.severity == "blocked" for issue in issues),
        checked_frames=len(frames),
        checked_elements=checked_elements,
        issues=tuple(issues),
    )


def _check_elements(
    elements: list[dict[str, Any]],
    frame: int,
    canvas_width: float,
    canvas_height: float,
    minimum_font_size: float,
    issues: list[VisualIssue],
) -> None:
    for element in elements:
        element_id = element["id"]
        rect = element["rect"]
        if (
            rect.x < -1
            or rect.y < -1
            or rect.right > canvas_width + 1
            or rect.bottom > canvas_height + 1
        ):
            issues.append(
                VisualIssue(
                    "blocked",
                    "outside_canvas",
                    frame,
                    element_id,
                    "Element exceeds canvas bounds",
                )
            )
        if (
            element["scroll_width"] > element["client_width"] + 1
            or element["scroll_height"] > element["client_height"] + 1
        ):
            issues.append(
                VisualIssue(
                    "blocked",
                    "text_overflow",
                    frame,
                    element_id,
                    "Element content overflows its box",
                )
            )
        if element["role"] in {"title", "body", "caption", "source"}:
            font_size = element["font_size"]
            if font_size is not None and font_size < minimum_font_size:
                issues.append(
                    VisualIssue(
                        "blocked",
                        "font_size",
                        frame,
                        element_id,
                        f"Font {font_size:.1f}px is below {minimum_font_size:.1f}px",
                    )
                )
            contrast = element["contrast_ratio"]
            threshold = (
                3.0
                if font_size is not None and font_size >= minimum_font_size * 1.5
                else 4.5
            )
            if contrast is not None and contrast < threshold:
                issues.append(
                    VisualIssue(
                        "blocked",
                        "contrast",
                        frame,
                        element_id,
                        f"Contrast {contrast:.2f}:1 is below {threshold:.1f}:1",
                    )
                )
        if element["role"] == "main-media":
            _check_media_layout(element, frame, issues)
        avoid_roles = element["avoid_roles"]
        for other in elements:
            if other is element or other["role"] not in avoid_roles:
                continue
            if rect.intersects(other["rect"]):
                issues.append(
                    VisualIssue(
                        "blocked",
                        "layout_collision",
                        frame,
                        element_id,
                        f"Intersects {other['role']} element {other['id']}",
                    )
                )


def _parse_element(raw: object, frame: int) -> dict[str, Any]:
    item = _require_object(raw, f"element at frame {frame}")
    rect_raw = _require_object(item.get("rect"), "element.rect")
    element_id = str(item.get("id") or "unknown")
    role = str(item.get("role") or "unknown")
    avoid_raw = item.get("avoid_roles", [])
    avoid_roles = (
        {str(value) for value in avoid_raw} if isinstance(avoid_raw, list) else set()
    )
    return {
        "id": element_id,
        "role": role,
        "rect": Rect(
            x=_number(rect_raw.get("x"), "rect.x"),
            y=_number(rect_raw.get("y"), "rect.y"),
            width=_number(rect_raw.get("width"), "rect.width"),
            height=_number(rect_raw.get("height"), "rect.height"),
        ),
        "scroll_width": _number(
            item.get("scroll_width", rect_raw.get("width")), "scroll_width"
        ),
        "scroll_height": _number(
            item.get("scroll_height", rect_raw.get("height")), "scroll_height"
        ),
        "client_width": _number(
            item.get("client_width", rect_raw.get("width")), "client_width"
        ),
        "client_height": _number(
            item.get("client_height", rect_raw.get("height")), "client_height"
        ),
        "font_size": _optional_number(item.get("font_size")),
        "contrast_ratio": _optional_number(item.get("contrast_ratio")),
        "avoid_roles": avoid_roles,
        "media_fit": _optional_string(item.get("media_fit")),
        "empty_space_strategy": _optional_string(
            item.get("empty_space_strategy")
        ),
        "camera_bounds_clamped": _optional_bool(
            item.get("camera_bounds_clamped")
        ),
        "intrinsic_width": _optional_number(item.get("intrinsic_width")),
        "intrinsic_height": _optional_number(item.get("intrinsic_height")),
    }


def _check_media_layout(
    element: dict[str, Any],
    frame: int,
    issues: list[VisualIssue],
) -> None:
    element_id = element["id"]
    fit = element["media_fit"]
    strategy = element["empty_space_strategy"]
    if fit == "contain" and strategy in {None, "none"}:
        issues.append(
            VisualIssue(
                "blocked",
                "unplanned_letterbox",
                frame,
                element_id,
                "Contain media needs a designed matte, adjacent content, or approved backdrop",
            )
        )
    if element["camera_bounds_clamped"] is False:
        issues.append(
            VisualIssue(
                "blocked",
                "camera_canvas_exposure",
                frame,
                element_id,
                "Camera translation is not clamped to media bounds",
            )
        )
    intrinsic_width = element["intrinsic_width"]
    intrinsic_height = element["intrinsic_height"]
    rect = element["rect"]
    if (
        fit == "contain"
        and intrinsic_width
        and intrinsic_height
        and rect.width > 0
        and rect.height > 0
    ):
        media_ratio = intrinsic_width / intrinsic_height
        box_ratio = rect.width / rect.height
        coverage = (
            box_ratio / media_ratio if media_ratio > box_ratio else media_ratio / box_ratio
        )
        unused = max(0.0, 1 - coverage)
        if unused > 0.25:
            issues.append(
                VisualIssue(
                    "needs_review",
                    "large_letterbox_area",
                    frame,
                    element_id,
                    f"Contain leaves about {unused:.0%} of the media viewport unused",
                )
            )


def _require_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TalkingCraftError(f"{label} must be an object")
    return value


def _positive_number(value: object, label: str) -> float:
    number = _number(value, label)
    if number <= 0:
        raise TalkingCraftError(f"{label} must be positive")
    return number


def _number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)):
        raise TalkingCraftError(f"{label} must be a number")
    return float(value)


def _optional_number(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _integer(value: object, label: str) -> int:
    if not isinstance(value, int):
        raise TalkingCraftError(f"{label} must be an integer")
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate browser-collected visual layout data"
    )
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--min-font-size-1080", type=float, default=24)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = run_visual_qa(
            args.snapshot, min_font_size_1080=args.min_font_size_1080
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
