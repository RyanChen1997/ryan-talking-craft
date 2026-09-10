from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "assets/visual-kit"


def test_catalog_palettes_are_self_contained() -> None:
    catalog = json.loads((KIT / "catalog.json").read_text(encoding="utf-8"))
    palettes = [entry for entry in catalog["entries"] if entry.get("type") == "palette"]
    assert {entry["id"] for entry in palettes} == {
        "grid-hud-cyan@1",
        "grid-cinema-amber@1",
        "grid-neutral-gold@1",
        "paper-day@1",
    }
    for entry in palettes:
        assert entry["stage"] in {"dark", "light"}
        assert entry["accentFamily"] in {"cool", "warm", "neutral"}
        assert entry["cardTreatment"] in {"glass", "paper"}
        assert entry["compatibleBackgrounds"]
        assert (KIT / entry["readme"]).is_file()
        assert (KIT / entry["code"]).is_file()
        source = (KIT / entry["code"]).read_text(encoding="utf-8")
        assert f'id: "{entry["id"]}"' in source
        assert "primary:" in source and "onSurface:" in source


def test_grid_background_pairs_only_with_dark_palettes() -> None:
    catalog = json.loads((KIT / "catalog.json").read_text(encoding="utf-8"))
    grid = next(entry for entry in catalog["entries"] if entry["id"] == "perspective-grid@1")
    assert grid["stage"] == "dark"
    for entry in catalog["entries"]:
        if entry.get("type") != "palette":
            continue
        if "perspective-grid@1" in entry["compatibleBackgrounds"]:
            assert entry["stage"] == "dark"


def test_catalog_reviewed_templates_match_files() -> None:
    catalog = json.loads((KIT / "catalog.json").read_text(encoding="utf-8"))
    templates = [entry for entry in catalog["entries"] if entry.get("type") == "template"]
    assert templates
    assert {entry["id"] for entry in templates} >= {
        "ink-underline@1",
        "numbered-step-stack@1",
        "source-converge@1",
        "flying-words@1",
    }
    disk = {
        f"{path.parent.name}@1"
        for path in (KIT / "templates").glob("*/*/*/Template.tsx")
    }
    catalog_ids = {entry["id"] for entry in templates}
    assert catalog_ids == disk
    assert not (KIT / "templates/typography/ordered-steps").exists()
    assert not (KIT / "templates/typography/before-after").exists()
    for entry in templates:
        assert entry["status"] == "reviewed"
        assert entry["carrier"] in {"typography", "diagram"}
        assert entry["informationRelations"]
        assert (KIT / entry["readme"]).is_file()
        assert (KIT / entry["code"]).is_file()
        assert f'ID：{entry["id"]}' in (KIT / entry["readme"]).read_text(encoding="utf-8") or f"`{entry['id']}`" in (KIT / entry["readme"]).read_text(encoding="utf-8")


def test_catalog_reviewed_layouts_match_files() -> None:
    catalog = json.loads((KIT / "catalog.json").read_text(encoding="utf-8"))
    layouts = [entry for entry in catalog["entries"] if entry.get("type") == "layout"]
    assert {entry["id"] for entry in layouts} == {
        "whiteboard-pip-right@1",
        "whiteboard-pip-left@1",
        "screen-full@1",
        "screen-pip-right@1",
        "screen-pip-left@1",
    }
    assert not (KIT / "layouts/presenter").exists()
    readme = (KIT / "layouts/stage/README.md").read_text(encoding="utf-8")
    for entry in layouts:
        assert entry["status"] == "reviewed"
        assert entry["variant"] == entry["id"].removesuffix("@1")
        assert (KIT / entry["readme"]).is_file()
        assert (KIT / entry["code"]).is_file()
        assert f"`{entry['id']}`" in readme
