#!/usr/bin/env python3
"""Generate a PowerPoint VBA macro from layout.json."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def q(s: str) -> str:
    return '"' + str(s).replace('"', '""') + '"'


def clean_hex(value: str | None, default: str = "#000000") -> str:
    if not value:
        value = default
    value = str(value).strip()
    if not value.startswith("#"):
        value = "#" + value
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        value = default
    return value.upper()


def vba_rgb(value: str | None, default: str = "#000000") -> str:
    value = clean_hex(value, default).lstrip("#")
    r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    return f"RGB({r}, {g}, {b})"


def in_to_pt(v: float) -> str:
    return f"{float(v) * 72:.3f}"


def shape_name(name: str | None, fallback: str) -> str:
    if not name:
        return fallback
    safe = re.sub(r"[^A-Za-z0-9_\-\u4e00-\u9fff]", "_", str(name))[:80]
    return safe or fallback


def generate_vba(layout: dict) -> str:
    slide = layout.get("slide", {})
    width = float(slide.get("width", 13.333))
    height = float(slide.get("height", 7.5))
    theme = layout.get("theme", {})
    default_font = theme.get("font", "Microsoft YaHei")
    bg = clean_hex(theme.get("background", "#FFFFFF"), "#FFFFFF")

    lines: list[str] = []
    lines.extend([
        "Option Explicit",
        "",
        "Sub Rebuild_Image_As_Editable_Slide()",
        "    Dim pres As Presentation",
        "    Dim sld As Slide",
        "    Dim shp As Shape",
        "    Dim tbl As Table",
        "    Set pres = ActivePresentation",
        f"    pres.PageSetup.SlideWidth = {in_to_pt(width)}",
        f"    pres.PageSetup.SlideHeight = {in_to_pt(height)}",
        "    Set sld = pres.Slides.Add(pres.Slides.Count + 1, ppLayoutBlank)",
        "",
        "    ' Background",
        f"    Set shp = sld.Shapes.AddShape(msoShapeRectangle, 0, 0, {in_to_pt(width)}, {in_to_pt(height)})",
        "    shp.Name = \"background\"",
        f"    shp.Fill.ForeColor.RGB = {vba_rgb(bg)}",
        "    shp.Line.Visible = msoFalse",
        "",
    ])

    for idx, el in enumerate(layout.get("elements", []), start=1):
        etype = el.get("type")
        name = shape_name(el.get("name"), f"shape_{idx}")
        lines.append(f"    ' {idx}. {etype}: {name}")

        if etype == "rect":
            x, y, w, h = map(lambda k: float(el.get(k, 0)), ["x", "y", "w", "h"])
            radius = float(el.get("radius", 0) or 0)
            shape_type = "msoShapeRoundedRectangle" if radius > 0 else "msoShapeRectangle"
            lines.append(f"    Set shp = sld.Shapes.AddShape({shape_type}, {in_to_pt(x)}, {in_to_pt(y)}, {in_to_pt(w)}, {in_to_pt(h)})")
            lines.append(f"    shp.Name = {q(name)}")
            fill = el.get("fill")
            if fill and str(fill).lower() != "none":
                lines.append("    shp.Fill.Visible = msoTrue")
                lines.append(f"    shp.Fill.ForeColor.RGB = {vba_rgb(fill, '#FFFFFF')}")
                opacity = float(el.get("opacity", 1) or 1)
                if opacity < 1:
                    lines.append(f"    shp.Fill.Transparency = {1 - opacity:.3f}")
            else:
                lines.append("    shp.Fill.Visible = msoFalse")
            line = el.get("line")
            if line and str(line).lower() != "none":
                lines.append("    shp.Line.Visible = msoTrue")
                lines.append(f"    shp.Line.ForeColor.RGB = {vba_rgb(line, '#D0D5DD')}")
                lines.append(f"    shp.Line.Weight = {float(el.get('line_width', 1) or 1):.2f}")
            else:
                lines.append("    shp.Line.Visible = msoFalse")

        elif etype == "text":
            x, y, w, h = map(lambda k: float(el.get(k, 0)), ["x", "y", "w", "h"])
            text = el.get("text", "")
            lines.append(f"    Set shp = sld.Shapes.AddTextbox(msoTextOrientationHorizontal, {in_to_pt(x)}, {in_to_pt(y)}, {in_to_pt(w)}, {in_to_pt(h)})")
            lines.append(f"    shp.Name = {q(name)}")
            lines.append(f"    shp.TextFrame.TextRange.Text = {q(text)}")
            lines.append("    shp.TextFrame.MarginLeft = 0")
            lines.append("    shp.TextFrame.MarginRight = 0")
            lines.append("    shp.TextFrame.MarginTop = 0")
            lines.append("    shp.TextFrame.MarginBottom = 0")
            lines.append(f"    shp.TextFrame.TextRange.Font.Name = {q(el.get('font', default_font))}")
            lines.append(f"    shp.TextFrame.TextRange.Font.Size = {float(el.get('font_size', 12) or 12):.1f}")
            lines.append(f"    shp.TextFrame.TextRange.Font.Bold = {'msoTrue' if el.get('bold') else 'msoFalse'}")
            lines.append(f"    shp.TextFrame.TextRange.Font.Italic = {'msoTrue' if el.get('italic') else 'msoFalse'}")
            lines.append(f"    shp.TextFrame.TextRange.Font.Color.RGB = {vba_rgb(el.get('color', '#000000'))}")
            align = str(el.get("align", "left")).lower()
            align_map = {"left": "ppAlignLeft", "center": "ppAlignCenter", "right": "ppAlignRight", "justify": "ppAlignJustify"}
            lines.append(f"    shp.TextFrame.TextRange.ParagraphFormat.Alignment = {align_map.get(align, 'ppAlignLeft')}")
            valign = str(el.get("valign", "top")).lower()
            valign_map = {"top": "msoAnchorTop", "middle": "msoAnchorMiddle", "center": "msoAnchorMiddle", "bottom": "msoAnchorBottom"}
            lines.append(f"    shp.TextFrame.VerticalAnchor = {valign_map.get(valign, 'msoAnchorTop')}")

        elif etype == "line":
            x1, y1, x2, y2 = map(lambda k: float(el.get(k, 0)), ["x1", "y1", "x2", "y2"])
            lines.append(f"    Set shp = sld.Shapes.AddLine({in_to_pt(x1)}, {in_to_pt(y1)}, {in_to_pt(x2)}, {in_to_pt(y2)})")
            lines.append(f"    shp.Name = {q(name)}")
            lines.append(f"    shp.Line.ForeColor.RGB = {vba_rgb(el.get('color', '#000000'))}")
            lines.append(f"    shp.Line.Weight = {float(el.get('width', 1) or 1):.2f}")

        elif etype == "image":
            x, y, w, h = map(lambda k: float(el.get(k, 0)), ["x", "y", "w", "h"])
            path = el.get("path", "")
            lines.append(f"    Set shp = sld.Shapes.AddPicture({q(path)}, msoFalse, msoTrue, {in_to_pt(x)}, {in_to_pt(y)}, {in_to_pt(w)}, {in_to_pt(h)})")
            lines.append(f"    shp.Name = {q(name)}")

        elif etype == "table":
            x, y, w, h = map(lambda k: float(el.get(k, 0)), ["x", "y", "w", "h"])
            data = el.get("data", [])
            rows = int(el.get("rows", len(data) or 1))
            cols = int(el.get("cols", max((len(r) for r in data), default=1)))
            lines.append(f"    Set shp = sld.Shapes.AddTable({rows}, {cols}, {in_to_pt(x)}, {in_to_pt(y)}, {in_to_pt(w)}, {in_to_pt(h)})")
            lines.append(f"    shp.Name = {q(name)}")
            lines.append("    Set tbl = shp.Table")
            for r in range(rows):
                for c in range(cols):
                    value = ""
                    if r < len(data) and c < len(data[r]):
                        value = data[r][c]
                    lines.append(f"    tbl.Cell({r+1}, {c+1}).Shape.TextFrame.TextRange.Text = {q(value)}")
                    lines.append(f"    tbl.Cell({r+1}, {c+1}).Shape.TextFrame.TextRange.Font.Name = {q(default_font)}")
                    lines.append(f"    tbl.Cell({r+1}, {c+1}).Shape.TextFrame.TextRange.Font.Size = {float(el.get('font_size', 10) or 10):.1f}")
                    lines.append(f"    tbl.Cell({r+1}, {c+1}).Shape.TextFrame.TextRange.Font.Color.RGB = {vba_rgb(el.get('text_color', '#101828'))}")
        else:
            lines.append("    ' Unsupported element type; skipped.")
        lines.append("")

    lines.extend([
        "    MsgBox \"Reconstruction completed. Review alignment and cropped assets.\", vbInformation",
        "End Sub",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("layout", type=Path)
    parser.add_argument("--out", type=Path, default=Path("reconstruction_macro.bas"))
    args = parser.parse_args()
    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(generate_vba(layout), encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
