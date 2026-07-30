#!/usr/bin/env python3
"""Validate an AI Visual PPT Composer deck.json file.

This validator is intentionally lightweight: it checks structural mistakes,
missing local assets, unsafe background prompts, and common editability risks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REQUIRED_META = ["title"]
REQUIRED_ELEMENT_FIELDS = ["type", "x", "y", "w", "h"]
ALLOWED_TYPES = {"text", "shape", "image", "svg", "line", "table", "chart"}
NEGATIVE_TERMS = [
    "no readable text",
    "no letters",
    "no numbers",
    "no logo",
    "no watermark",
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"ERROR: failed to read JSON: {path}\n{exc}") from exc


def is_probably_hex_color(value: str) -> bool:
    return bool(re.fullmatch(r"#?[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", value or ""))


def validate(deck_path: Path) -> tuple[list[str], list[str]]:
    deck = load_json(deck_path)
    base = deck_path.parent
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(deck, dict):
        return ["root must be a JSON object"], []

    meta = deck.get("meta")
    if not isinstance(meta, dict):
        errors.append("missing meta object")
    else:
        for key in REQUIRED_META:
            if not meta.get(key):
                errors.append(f"meta.{key} is required")
        theme = meta.get("theme", {}) or {}
        for color_key in ["color", "backgroundColor"]:
            if color_key in theme and not is_probably_hex_color(str(theme[color_key])):
                warnings.append(f"meta.theme.{color_key} is not a 6-digit hex color: {theme[color_key]}")

    slides = deck.get("slides")
    if not isinstance(slides, list) or not slides:
        errors.append("slides must be a non-empty array")
        return errors, warnings

    seen_ids: set[str] = set()
    for si, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            errors.append(f"slides[{si}] must be an object")
            continue

        slide_id = slide.get("id") or f"slide_{si}"
        if slide_id in seen_ids:
            errors.append(f"duplicate slide id: {slide_id}")
        seen_ids.add(str(slide_id))

        bg = slide.get("background", {}) or {}
        if bg.get("image"):
            image_path = (base / str(bg["image"])).resolve()
            if not image_path.exists():
                warnings.append(f"slide {slide_id}: background.image not found: {bg['image']}")
        if bg.get("color") and not is_probably_hex_color(str(bg["color"])):
            warnings.append(f"slide {slide_id}: background.color is not a 6-digit hex color: {bg['color']}")

        prompt = str(slide.get("background_prompt", "")).lower()
        if prompt:
            missing_terms = [term for term in NEGATIVE_TERMS if term not in prompt]
            if missing_terms:
                warnings.append(
                    f"slide {slide_id}: background_prompt may be missing negative constraints: "
                    + ", ".join(missing_terms)
                )

        elements = slide.get("elements")
        if not isinstance(elements, list):
            errors.append(f"slide {slide_id}: elements must be an array")
            continue

        for ei, el in enumerate(elements, start=1):
            if not isinstance(el, dict):
                errors.append(f"slide {slide_id} element {ei}: must be object")
                continue
            for field in REQUIRED_ELEMENT_FIELDS:
                if field not in el:
                    errors.append(f"slide {slide_id} element {ei}: missing {field}")
            el_type = el.get("type")
            if el_type not in ALLOWED_TYPES:
                errors.append(f"slide {slide_id} element {ei}: invalid type {el_type}")

            for field in ["x", "y", "w", "h"]:
                if field in el:
                    try:
                        float(el[field])
                    except Exception:
                        errors.append(f"slide {slide_id} element {ei}: {field} must be numeric")

            if el_type == "text" and "text" not in el:
                errors.append(f"slide {slide_id} element {ei}: text element missing text")
            if el_type == "image" and not el.get("path"):
                errors.append(f"slide {slide_id} element {ei}: image element missing path")
            if el_type == "image" and el.get("path"):
                image_path = (base / str(el["path"])).resolve()
                if not image_path.exists():
                    warnings.append(f"slide {slide_id} element {ei}: image path not found: {el['path']}")
            if el_type == "svg" and not el.get("path") and not el.get("svg"):
                errors.append(f"slide {slide_id} element {ei}: svg element requires path or svg")
            if el_type == "svg" and el.get("path"):
                svg_path = (base / str(el["path"])).resolve()
                if not svg_path.exists():
                    warnings.append(f"slide {slide_id} element {ei}: svg path not found: {el['path']}")

            # Common editability risk: large text-like raster image.
            if el_type == "image" and any(token in str(el.get("name", "")).lower() for token in ["title", "text", "label"]):
                warnings.append(
                    f"slide {slide_id} element {ei}: image name suggests text-like raster; "
                    "ensure meaningful text also exists as native PPT text."
                )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AVPC deck.json")
    parser.add_argument("deck", type=Path, help="Path to deck.json")
    args = parser.parse_args()

    errors, warnings = validate(args.deck)
    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"- {warning}")
    if errors:
        print("ERRORS:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("OK: deck structure is valid enough to build.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
