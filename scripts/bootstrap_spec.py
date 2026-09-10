from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from common import TalkingCraftError, write_json


@dataclass(frozen=True)
class BootstrapConfig:
    root: Path
    slug: str
    title: str
    legacy: bool = False


@dataclass(frozen=True)
class BootstrapResult:
    spec_dir: Path
    slug: str
    created: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "spec_dir": str(self.spec_dir),
            "slug": self.slug,
            "created": self.created,
        }


def bootstrap_spec(config: BootstrapConfig) -> BootstrapResult:
    """Create or reuse a talking-craft specification directory."""
    root = config.root.expanduser().resolve()
    _validate_remotion_root(root)
    slug = _normalize_slug(config.slug)
    spec_root = root / "spec"
    spec_root.mkdir(parents=True, exist_ok=True)
    spec_dir, created = _resolve_spec_dir(spec_root, slug, config.title)
    if config.legacy:
        if (spec_dir / "plan.json").exists():
            raise TalkingCraftError("Cannot create legacy files inside a v2 spec")
        _create_directories(spec_dir)
        _write_initial_files(spec_dir, spec_dir.name, config.title)
    else:
        from project_plan import initialize

        initialize(spec_dir, spec_dir.name, config.title)
    return BootstrapResult(spec_dir=spec_dir, slug=spec_dir.name, created=created)


def _validate_remotion_root(root: Path) -> None:
    package_path = root / "package.json"
    if not package_path.is_file():
        raise TalkingCraftError(f"Not a project root: missing {package_path}")
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TalkingCraftError(f"Cannot read {package_path}: {error}") from error
    serialized = json.dumps(package)
    if "remotion" not in serialized.lower():
        raise TalkingCraftError(
            f"package.json does not appear to contain Remotion dependencies: {package_path}"
        )


def _normalize_slug(value: str) -> str:
    slug = value.strip().lower().replace("_", " ")
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    if not slug:
        raise TalkingCraftError("The derived slug is empty after normalization")
    if len(slug) > 64:
        slug = slug[:64].rstrip("-")
    return slug


def _resolve_spec_dir(spec_root: Path, slug: str, title: str) -> tuple[Path, bool]:
    direct = spec_root / slug
    if not direct.exists():
        return direct, True
    if _same_project(direct, title):
        return direct, False

    dated = spec_root / f"{slug}-{datetime.now(tz=UTC):%Y%m%d}"
    if not dated.exists():
        return dated, True
    if _same_project(dated, title):
        return dated, False

    suffix = 2
    while True:
        candidate = spec_root / f"{slug}-{suffix:02d}"
        if not candidate.exists():
            return candidate, True
        if _same_project(candidate, title):
            return candidate, False
        suffix += 1


def _same_project(spec_dir: Path, title: str) -> bool:
    plan_path = spec_dir / "plan.json"
    if plan_path.is_file():
        try:
            return json.loads(plan_path.read_text(encoding="utf-8")).get("title") == title
        except (OSError, ValueError):
            return False
    project_path = spec_dir / "project.yaml"
    if not project_path.is_file():
        return False
    try:
        project_text = project_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return f'title: "{_escape_yaml(title)}"' in project_text


def _create_directories(spec_dir: Path) -> None:
    relative_directories = (
        "01-input",
        "02-analysis/representative-frames",
        "03-design",
        "04-assets",
        "05-timeline",
        "06-approvals",
        "07-qa/motion-preview-qa",
        "decisions",
    )
    for relative in relative_directories:
        (spec_dir / relative).mkdir(parents=True, exist_ok=True)


def _write_initial_files(spec_dir: Path, slug: str, title: str) -> None:
    now = datetime.now(tz=UTC).isoformat()
    project_path = spec_dir / "project.yaml"
    if not project_path.exists():
        project_path.write_text(
            "\n".join(
                (
                    "schema_version: 1",
                    f"slug: {slug}",
                    f'title: "{_escape_yaml(title)}"',
                    "status: INTAKE",
                    "composition_id: null",
                    "output:",
                    "  width: null",
                    "  height: null",
                    "  fps: null",
                    "captions:",
                    "  render: true",
                    "  default_policy: on_unless_explicit_opt_out",
                    "  source: null",
                    "motion_library:",
                    "  version: null",
                    "",
                )
            ),
            encoding="utf-8",
        )

    _write_if_missing(
        spec_dir / "state.json",
        {
            "schema_version": 1,
            "slug": slug,
            "status": "INTAKE",
            "updated_at": now,
            "completed_steps": [],
            "blocking_reasons": [],
            "next_action": "inspect_inputs",
        },
    )
    _write_if_missing(
        spec_dir / "01-input/input-manifest.json",
        {"schema_version": 1, "inputs": []},
    )
    _write_if_missing(
        spec_dir / "04-assets/asset-manifest.json",
        {"schema_version": 1, "assets": []},
    )
    _write_if_missing(
        spec_dir / "04-assets/provenance.json",
        {"schema_version": 1, "sources": []},
    )
    for approval_name in ("design", "assets", "preview"):
        _write_if_missing(
            spec_dir / f"06-approvals/{approval_name}-approval.json",
            {
                "approved": False,
                "approved_at": None,
                "scope": approval_name,
                "user_message": None,
                "exceptions": [],
            },
        )

    markdown_defaults = {
        "01-input/original-request.md": "# 原始需求\n\n",
        "01-input/production-requirements.md": "# 制作要求\n\n",
        "04-assets/acquisition-log.md": "# 自动素材获取记录\n\n",
        "04-assets/privacy-review.md": "# 隐私审查\n\n",
        "07-qa/test-plan.md": "# 测试计划\n\n",
        "07-qa/resolution-log.md": "# QA 修复记录\n\n",
        "decisions/decision-log.md": "# 制作决策记录\n\n",
    }
    for relative, content in markdown_defaults.items():
        path = spec_dir / relative
        if not path.exists():
            path.write_text(content, encoding="utf-8")


def _write_if_missing(path: Path, value: object) -> None:
    if not path.exists():
        write_json(path, value)


def _escape_yaml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _parse_args() -> BootstrapConfig:
    parser = argparse.ArgumentParser(
        description="Bootstrap a Ryan Talking Craft spec directory"
    )
    parser.add_argument(
        "--root", required=True, type=Path, help="Remotion project root"
    )
    parser.add_argument("--slug", required=True, help="Agent-derived kebab-case slug")
    parser.add_argument("--title", required=True, help="Human-readable video title")
    parser.add_argument("--legacy", action="store_true", help="Explicitly create the old v1 spec layout")
    args = parser.parse_args()
    return BootstrapConfig(root=args.root, slug=args.slug, title=args.title, legacy=args.legacy)


def main() -> int:
    try:
        result = bootstrap_spec(_parse_args())
    except TalkingCraftError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, **result.to_dict()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
