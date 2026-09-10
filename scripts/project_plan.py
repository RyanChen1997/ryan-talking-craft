"""Version-2 authoritative plan, review generation, and approval gates."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from common import TalkingCraftError, write_json

STAGES = ("INTAKE", "CONTENT_REVIEW", "ACQUIRING_ASSETS", "VISUAL_REVIEW", "BUILDING", "PREVIEW_REVIEW", "FINAL_RENDER", "DONE")


@dataclass
class Project:
    plan: dict
    assets: dict
    state: dict

    def to_dict(self) -> dict:
        return {"plan": self.plan, "assets": self.assets, "state": self.state}

    @classmethod
    def from_dict(cls, value: dict) -> Project:
        return cls(value["plan"], value["assets"], value["state"])


def initialize(directory: Path, slug: str, title: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "project.yaml").exists():
        raise TalkingCraftError("Legacy spec: do not silently migrate; use a new slug or legacy workflow")
    defaults = {
        "plan": {"schema_version": 2, "slug": slug, "title": title, "output": {"width": 1920, "height": 1080}, "fps": 30, "duration_frames": None, "captions": True, "background": "perspective-grid@1", "palette": None, "segments": []},
        "assets": {"schema_version": 2, "assets": []},
        "state": {"schema_version": 2, "status": "INTAKE", "approvals": {}, "blocking_reasons": []},
    }
    for name, value in defaults.items():
        if not (directory / f"{name}.json").exists():
            write_json(directory / f"{name}.json", value)
    (directory / "qa").mkdir(exist_ok=True)


def load_project(directory: Path) -> Project:
    try:
        value = {name: json.loads((directory / f"{name}.json").read_text()) for name in ("plan", "assets", "state")}
        if any(item.get("schema_version") != 2 for item in value.values()):
            raise TalkingCraftError("Expected schema_version 2; legacy specs are not converted automatically")
        return Project.from_dict(value)
    except (OSError, ValueError, AttributeError) as error:
        raise TalkingCraftError(f"Invalid spec: {error}") from error


def validate(project: Project, visual: bool = False) -> list[str]:
    errors: list[str] = []
    segments = project.plan.get("segments", [])
    assets = project.assets.get("assets", [])
    ids = [a.get("id") for a in assets]
    if len(set(ids)) != len(ids) or any(not value for value in ids):
        errors.append("Asset IDs must be present and unique")
    if not segments:
        errors.append("At least one content segment is required")
    end = 0
    segment_ids: set[str] = set()
    for segment in segments:
        sid = segment.get("id")
        if not sid or sid in segment_ids:
            errors.append("Segment IDs must be present and unique")
        segment_ids.add(sid)
        start, stop = segment.get("from"), segment.get("to")
        if not isinstance(start, int) or not isinstance(stop, int) or start != end or stop <= start:
            errors.append(f"{sid}: invalid/gapped frame range")
        end = stop
        if not segment.get("meaning") or not isinstance(segment.get("screen_text"), list):
            errors.append(f"{sid}: meaning and screen_text list required (empty text allowed)")
        for asset_id in segment.get("asset_ids", []):
            if asset_id not in ids:
                errors.append(f"{sid}: unknown asset {asset_id}")
        if visual and not segment.get("visual", {}).get("layout"):
            errors.append(f"{sid}: layout required")
        if visual:
            clip_ids = {c.get("asset_id") for c in segment.get("visual", {}).get("clips", [])}
            for asset in assets:
                if asset.get("id") in segment.get("asset_ids", []) and asset.get("kind") == "user_recording" and asset["id"] not in clip_ids:
                    errors.append(f"{sid}: user recording requires an explicit clip entry")
        for clip in segment.get("visual", {}).get("clips", []):
            asset = next((a for a in assets if a.get("id") == clip.get("asset_id")), None)
            if asset is None:
                errors.append(f"{sid}: unknown clip asset")
                continue
            if asset.get("kind") == "user_recording":
                if clip.get("fit", "contain") != "contain" or clip.get("crop") or clip.get("zoom", 1) != 1:
                    errors.append(f"{sid}: user recording must remain uncropped, contain, zoom=1")
            source_in, source_out = clip.get("source_in"), clip.get("source_out")
            if not isinstance(source_in, (int, float)) or not isinstance(source_out, (int, float)) or source_in < 0 or source_out <= source_in:
                errors.append(f"{sid}: invalid source seconds")
            elif asset.get("duration_seconds") is not None and source_out > asset["duration_seconds"]:
                errors.append(f"{sid}: source range exceeds asset")
    if visual and (not isinstance(project.plan.get("duration_frames"), int) or end != project.plan["duration_frames"]):
        errors.append("Timeline must cover final narration duration_frames")
    if visual:
        output = project.plan.get("output", {})
        width, height = output.get("width"), output.get("height")
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            errors.append("output.width and output.height must be positive integers")
    if visual and not project.plan.get("background"):
        errors.append("background required")
    if visual and not project.plan.get("palette"):
        errors.append("palette required")
    for asset in assets:
        if asset.get("provider") == "user" and asset.get("kind") == "user_recording" and asset.get("status") != "ready":
            request = asset.get("recording_request", {})
            if not request.get("content") or not isinstance(request.get("record_seconds"), (int, float)) or request.get("record_seconds", 0) <= 0 or not isinstance(request.get("use_seconds"), (int, float)) or request.get("use_seconds", 0) <= 0:
                errors.append(f"{asset.get('id')}: recording content, record_seconds and use_seconds required")
        if visual and asset.get("required", True) and asset.get("status") != "ready":
            errors.append(f"{asset.get('id')}: required asset not ready")
    return errors


def export_reviews(directory: Path) -> None:
    project = load_project(directory)
    content = ["# 视觉内容确认稿（生成视图，请修改 plan.json / assets.json）", "", "| 帧范围 | 核心意思 | 上屏文字 | 素材 |", "|---|---|---|---|"]
    visual = [
        "# 画面确认稿（生成视图）",
        "",
        f"- 画幅：{_cell(_output_label(project.plan))}",
        f"- 背景：{_cell(project.plan.get('background', ''))}",
        f"- 配色：{_cell(project.plan.get('palette', ''))}",
        "",
        "| 段落 | 布局 | 模板 | 关键展开顺序 |",
        "|---|---|---|---|",
    ]
    for s in project.plan["segments"]:
        content.append(f"| {s.get('from')}–{s.get('to')} | {_cell(s.get('meaning', ''))} | {_cell(' / '.join(s.get('screen_text', [])))} | {_cell(', '.join(s.get('asset_ids', [])))} |")
        v = s.get("visual", {})
        visual.append(f"| {_cell(s.get('id', ''))} | {_cell(v.get('layout', ''))} | {_cell(v.get('template', '静态'))} | {_cell(v.get('beats', ''))} |")
    content.extend(["", "## 素材与录制需求", ""])
    for a in project.assets["assets"]:
        r = a.get("recording_request", {})
        content.append(f"- {_cell(a['id'])}：{_cell(a.get('purpose', ''))}；责任：{a.get('provider', '')}；状态：{a.get('status', '')}")
        if r:
            content.append(f"  - 录制：{_cell(r.get('content', ''))}；建议录 {r.get('record_seconds')} 秒；成片使用约 {r.get('use_seconds')} 秒。")
    for name, lines in (("content-review", content), ("visual-review", visual)):
        (directory / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _output_label(plan: dict) -> str:
    output = plan.get("output", {})
    width, height = output.get("width"), output.get("height")
    if width == 1920 and height == 1080:
        return "1920×1080（16:9，默认）"
    if isinstance(width, int) and isinstance(height, int):
        return f"{width}×{height}（用户指定）"
    return "未设置"


def advance(directory: Path, target: str, user_message: str = "") -> None:
    project = load_project(directory)
    current = project.state["status"]
    if target not in STAGES or STAGES.index(target) != STAGES.index(current) + 1:
        raise TalkingCraftError(f"Invalid transition {current} → {target}")
    errors = validate(project, visual=STAGES.index(target) >= STAGES.index("VISUAL_REVIEW"))
    approvals = project.state["approvals"]
    if target in ("ACQUIRING_ASSETS", "BUILDING", "FINAL_RENDER"):
        if not user_message.strip():
            errors.append("Explicit user confirmation required; pass the original user message")
    if STAGES.index(target) >= STAGES.index("VISUAL_REVIEW") and approvals.get("content", {}).get("hash") != _fingerprint(project, "content"):
        errors.append("Content changed since approval; reset to INTAKE and reconfirm")
    if STAGES.index(target) > STAGES.index("BUILDING") and approvals.get("visual", {}).get("hash") != _fingerprint(project, "visual"):
        errors.append("Visual plan changed since approval; reset to ACQUIRING_ASSETS and reconfirm")
    if target in ("PREVIEW_REVIEW", "DONE"):
        report_name = "production" if target == "PREVIEW_REVIEW" else "delivery"
        report_path = directory / "qa" / f"{report_name}.json"
        if not report_path.exists():
            errors.append(f"Missing {report_path.name}")
        else:
            report = json.loads(report_path.read_text())
            if report.get("passed") is not True or report.get("plan_hash") != _fingerprint(project, "visual"):
                errors.append("QA report failed or does not match current plan")
    if errors:
        raise TalkingCraftError("; ".join(errors))
    for next_stage, scope in (("ACQUIRING_ASSETS", "content"), ("BUILDING", "visual"), ("FINAL_RENDER", "preview")):
        if target == next_stage:
            approvals[scope] = {"user_message": user_message, "hash": _fingerprint(project, "content" if scope == "content" else "visual")}
    project.state["status"] = target
    write_json(directory / "state.json", project.state)
    export_reviews(directory)


def _fingerprint(project: Project, scope: str) -> str:
    if scope == "content":
        value = {
            "segments": [{k: s.get(k) for k in ("id", "from", "to", "meaning", "screen_text", "asset_ids")} for s in project.plan["segments"]],
            "assets": [{k: a.get(k) for k in ("id", "purpose", "provider", "required", "recording_request")} for a in project.assets["assets"]],
        }
    else:
        value = {"plan": project.plan, "assets": project.assets}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("action", choices=("reviews", "validate", "advance", "hash", "reset"))
    parser.add_argument("--target", choices=STAGES)
    parser.add_argument("--user-message", default="")
    parser.add_argument("--visual", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "reviews":
            export_reviews(args.directory)
        elif args.action == "advance":
            advance(args.directory, args.target, args.user_message)
        elif args.action == "reset":
            if args.target not in ("INTAKE", "ACQUIRING_ASSETS"):
                raise TalkingCraftError("Reset target must be INTAKE or ACQUIRING_ASSETS")
            p = load_project(args.directory)
            if args.target == "ACQUIRING_ASSETS" and p.state["approvals"].get("content", {}).get("hash") != _fingerprint(p, "content"):
                raise TalkingCraftError("Content approval missing/stale; reset to INTAKE")
            p.state["status"] = args.target
            p.state["approvals"] = {} if args.target == "INTAKE" else {"content": p.state["approvals"]["content"]}
            write_json(args.directory / "state.json", p.state)
        elif args.action == "hash":
            print(_fingerprint(load_project(args.directory), "visual" if args.visual else "content"))
        else:
            errors = validate(load_project(args.directory), args.visual)
            if errors:
                raise TalkingCraftError("; ".join(errors))
    except (TalkingCraftError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
