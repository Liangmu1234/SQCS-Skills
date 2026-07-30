#!/usr/bin/env python3
"""Build a one-slide editable PPTX from an image reconstruction manifest.

The script intentionally uses only stdlib plus Pillow. It writes a small OpenXML
PPTX with native text boxes, shapes, and cropped picture objects.
"""

from __future__ import annotations

import argparse
import json
import math
import posixpath
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image

EMU_PER_INCH = 914400
PT_TO_EMU = 12700

NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_DC = "http://purl.org/dc/elements/1.1/"
NS_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NS_DCTERMS = "http://purl.org/dc/terms/"
NS_DCMITYPE = "http://purl.org/dc/dcmitype/"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"


@dataclass
class MediaItem:
    rid: str
    source_path: Path
    target_name: str


def xml(text: Any) -> str:
    return escape(str(text), {'"': "&quot;"})


def slug(value: str, fallback: str = "asset") -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-._")
    return value or fallback


def resolve_path(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    p = Path(value)
    return p if p.is_absolute() else (base / p).resolve()


def normalize_color(value: Any, default: str | None = None) -> str | None:
    if value is None:
        return default
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.lower() in {"none", "transparent", "no", "null"}:
            return None
        if cleaned.startswith("#"):
            cleaned = cleaned[1:]
        if re.fullmatch(r"[0-9a-fA-F]{3}", cleaned):
            cleaned = "".join(ch * 2 for ch in cleaned)
        if re.fullmatch(r"[0-9a-fA-F]{6}", cleaned):
            return cleaned.upper()
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return "".join(f"{max(0, min(255, int(c))):02X}" for c in value[:3])
    raise ValueError(f"Invalid color value: {value!r}")


def solid_fill(color: str | None, opacity: float | None = None) -> str:
    if color is None:
        return "<a:noFill/>"
    alpha = ""
    if opacity is not None and opacity < 1:
        alpha_val = max(0, min(100000, int(round(opacity * 100000))))
        alpha = f"<a:alpha val=\"{alpha_val}\"/>"
    return f"<a:solidFill><a:srgbClr val=\"{color}\">{alpha}</a:srgbClr></a:solidFill>"


def line_xml(color: str | None, width_pt: float | None = None, opacity: float | None = None) -> str:
    if color is None:
        return "<a:ln><a:noFill/></a:ln>"
    width = int(round((width_pt if width_pt is not None else 1) * PT_TO_EMU))
    return f"<a:ln w=\"{width}\">{solid_fill(color, opacity)}</a:ln>"


def get_bbox(el: dict[str, Any]) -> tuple[float, float, float, float]:
    if "bbox" in el:
        x, y, w, h = el["bbox"]
        return float(x), float(y), float(w), float(h)
    if "bbox_px" in el:
        x, y, w, h = el["bbox_px"]
        return float(x), float(y), float(w), float(h)
    if "bbox_xyxy" in el:
        x1, y1, x2, y2 = el["bbox_xyxy"]
        return float(x1), float(y1), float(x2) - float(x1), float(y2) - float(y1)
    raise ValueError(f"Element is missing bbox: {el}")


def emu_bbox(
    bbox: tuple[float, float, float, float],
    scale_x: float,
    scale_y: float,
) -> tuple[int, int, int, int]:
    x, y, w, h = bbox
    return (
        int(round(x * scale_x)),
        int(round(y * scale_y)),
        int(round(w * scale_x)),
        int(round(h * scale_y)),
    )


def shape_preset(el: dict[str, Any]) -> str:
    raw = str(el.get("shape") or el.get("type") or "rect")
    mapping = {
        "rectangle": "rect",
        "rect": "rect",
        "box": "rect",
        "bar": "rect",
        "footer": "rect",
        "sidebar": "rect",
        "divider": "rect",
        "rounded_box": "roundRect",
        "rounded-rect": "roundRect",
        "roundrect": "roundRect",
        "roundRect": "roundRect",
        "rounded_rectangle": "roundRect",
        "ellipse": "ellipse",
        "oval": "ellipse",
        "circle": "ellipse",
        "line": "line",
    }
    return mapping.get(raw, raw)


def xfrm_xml(x: int, y: int, w: int, h: int) -> str:
    return f"<a:xfrm><a:off x=\"{x}\" y=\"{y}\"/><a:ext cx=\"{w}\" cy=\"{h}\"/></a:xfrm>"


def nonvisual_shape(shape_id: int, name: str, tx_box: bool = False) -> str:
    tx = " txBox=\"1\"" if tx_box else ""
    return (
        "<p:nvSpPr>"
        f"<p:cNvPr id=\"{shape_id}\" name=\"{xml(name)}\"/>"
        f"<p:cNvSpPr{tx}/>"
        "<p:nvPr/>"
        "</p:nvSpPr>"
    )


def shape_xml(shape_id: int, el: dict[str, Any], scale_x: float, scale_y: float) -> str:
    x, y, w, h = emu_bbox(get_bbox(el), scale_x, scale_y)
    name = str(el.get("name") or f"Shape {shape_id}")
    preset = shape_preset(el)
    fill = normalize_color(el.get("fill"), "#FFFFFF")
    stroke = normalize_color(el.get("stroke"), None)
    opacity = el.get("opacity")
    stroke_opacity = el.get("stroke_opacity")
    stroke_width = el.get("stroke_width")
    return (
        "<p:sp>"
        f"{nonvisual_shape(shape_id, name)}"
        "<p:spPr>"
        f"{xfrm_xml(x, y, max(w, 1), max(h, 1))}"
        f"<a:prstGeom prst=\"{xml(preset)}\"><a:avLst/></a:prstGeom>"
        f"{solid_fill(fill, float(opacity) if opacity is not None else None)}"
        f"{line_xml(stroke, float(stroke_width) if stroke_width is not None else None, float(stroke_opacity) if stroke_opacity is not None else None)}"
        "</p:spPr>"
        "</p:sp>"
    )


def text_body_xml(el: dict[str, Any]) -> str:
    text = str(el.get("text", ""))
    font = str(el.get("font") or el.get("font_family") or "Arial")
    font_size = float(el.get("font_size") or el.get("size") or 18)
    color = normalize_color(el.get("color"), "#000000")
    bold = bool(el.get("bold", False))
    italic = bool(el.get("italic", False))
    underline = bool(el.get("underline", False))
    align = str(el.get("align") or "left").lower()
    valign = str(el.get("valign") or el.get("vertical_align") or "top").lower()
    margin = el.get("margin", 2)
    if isinstance(margin, (int, float)):
        left = right = top = bottom = float(margin)
    else:
        left, top, right, bottom = [float(v) for v in margin]

    align_map = {"left": "l", "center": "ctr", "centre": "ctr", "right": "r", "justify": "just"}
    valign_map = {"top": "t", "middle": "mid", "center": "mid", "mid": "mid", "bottom": "b"}
    p_align = align_map.get(align, "l")
    anchor = valign_map.get(valign, "t")
    r_attrs = [f"lang=\"en-US\"", f"sz=\"{int(round(font_size * 100))}\""]
    if bold:
        r_attrs.append('b="1"')
    if italic:
        r_attrs.append('i="1"')
    if underline:
        r_attrs.append('u="sng"')
    rpr = (
        f"<a:rPr {' '.join(r_attrs)}>"
        f"{solid_fill(color)}"
        f"<a:latin typeface=\"{xml(font)}\"/>"
        f"<a:ea typeface=\"{xml(font)}\"/>"
        f"<a:cs typeface=\"{xml(font)}\"/>"
        "</a:rPr>"
    )

    paras = []
    for para in text.splitlines() or [""]:
        paras.append(
            f"<a:p><a:pPr algn=\"{p_align}\"/>"
            f"<a:r>{rpr}<a:t>{xml(para)}</a:t></a:r>"
            "</a:p>"
        )
    body_pr = (
        f"<a:bodyPr wrap=\"square\" anchor=\"{anchor}\" "
        f"lIns=\"{int(round(left * PT_TO_EMU))}\" "
        f"tIns=\"{int(round(top * PT_TO_EMU))}\" "
        f"rIns=\"{int(round(right * PT_TO_EMU))}\" "
        f"bIns=\"{int(round(bottom * PT_TO_EMU))}\"/>"
    )
    return f"<p:txBody>{body_pr}<a:lstStyle/>{''.join(paras)}</p:txBody>"


def text_xml(shape_id: int, el: dict[str, Any], scale_x: float, scale_y: float) -> str:
    x, y, w, h = emu_bbox(get_bbox(el), scale_x, scale_y)
    name = str(el.get("name") or f"Text {shape_id}")
    preset = shape_preset(el) if ("shape" in el or "fill" in el or "stroke" in el) else "rect"
    fill = normalize_color(el.get("fill"), None)
    stroke = normalize_color(el.get("stroke"), None)
    opacity = el.get("opacity")
    stroke_width = el.get("stroke_width")
    return (
        "<p:sp>"
        f"{nonvisual_shape(shape_id, name, tx_box=True)}"
        "<p:spPr>"
        f"{xfrm_xml(x, y, max(w, 1), max(h, 1))}"
        f"<a:prstGeom prst=\"{xml(preset)}\"><a:avLst/></a:prstGeom>"
        f"{solid_fill(fill, float(opacity) if opacity is not None else None)}"
        f"{line_xml(stroke, float(stroke_width) if stroke_width is not None else None)}"
        "</p:spPr>"
        f"{text_body_xml(el)}"
        "</p:sp>"
    )


def crop_or_copy_image(
    manifest_dir: Path,
    source_image: Path,
    crop_dir: Path,
    el: dict[str, Any],
    index: int,
) -> Path:
    source = resolve_path(manifest_dir, el.get("source"))
    if source:
        if not source.exists():
            raise FileNotFoundError(source)
        out_name = slug(Path(str(el.get("crop_name") or el.get("name") or f"image-{index}")).stem) + ".png"
        out = crop_dir / out_name
        with Image.open(source) as img:
            img.save(out)
        return out

    crop_dir.mkdir(parents=True, exist_ok=True)
    x, y, w, h = get_bbox(el)
    left = math.floor(x)
    top = math.floor(y)
    right = math.ceil(x + w)
    bottom = math.ceil(y + h)
    out_name = slug(str(el.get("crop_name") or el.get("name") or f"crop-{index}"))
    if not out_name.lower().endswith(".png"):
        out_name += ".png"
    out = crop_dir / out_name
    with Image.open(source_image) as img:
        box = (
            max(0, left),
            max(0, top),
            min(img.width, right),
            min(img.height, bottom),
        )
        img.crop(box).save(out)
    return out


def picture_xml(shape_id: int, el: dict[str, Any], media: MediaItem, scale_x: float, scale_y: float) -> str:
    x, y, w, h = emu_bbox(get_bbox(el), scale_x, scale_y)
    name = str(el.get("name") or f"Picture {shape_id}")
    return (
        "<p:pic>"
        "<p:nvPicPr>"
        f"<p:cNvPr id=\"{shape_id}\" name=\"{xml(name)}\"/>"
        "<p:cNvPicPr><a:picLocks noChangeAspect=\"0\"/></p:cNvPicPr>"
        "<p:nvPr/>"
        "</p:nvPicPr>"
        "<p:blipFill>"
        f"<a:blip r:embed=\"{media.rid}\"/>"
        "<a:stretch><a:fillRect/></a:stretch>"
        "</p:blipFill>"
        "<p:spPr>"
        f"{xfrm_xml(x, y, max(w, 1), max(h, 1))}"
        "<a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>"
        "</p:spPr>"
        "</p:pic>"
    )


def group_shape_xml() -> str:
    return (
        "<p:nvGrpSpPr>"
        "<p:cNvPr id=\"1\" name=\"\"/>"
        "<p:cNvGrpSpPr/>"
        "<p:nvPr/>"
        "</p:nvGrpSpPr>"
        "<p:grpSpPr>"
        "<a:xfrm>"
        "<a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/>"
        "<a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/>"
        "</a:xfrm>"
        "</p:grpSpPr>"
    )


def slide_xml(slide_w: int, slide_h: int, bg: str | None, elements_xml: list[str]) -> str:
    bg_xml = ""
    if bg:
        bg_xml = f"<p:bg><p:bgPr>{solid_fill(bg)}</p:bgPr></p:bg>"
    return (
        f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<p:sld xmlns:a=\"{NS_A}\" xmlns:r=\"{NS_R}\" xmlns:p=\"{NS_P}\">"
        "<p:cSld>"
        f"{bg_xml}"
        f"<p:spTree>{group_shape_xml()}{''.join(elements_xml)}</p:spTree>"
        "</p:cSld>"
        "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>"
        "</p:sld>"
    )


def rels_xml(rels: list[tuple[str, str, str]]) -> str:
    items = [
        f"<Relationship Id=\"{xml(rid)}\" Type=\"{xml(rel_type)}\" Target=\"{xml(target)}\"/>"
        for rid, rel_type, target in rels
    ]
    return (
        f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<Relationships xmlns=\"{NS_REL}\">{''.join(items)}</Relationships>"
    )


def presentation_xml(slide_w: int, slide_h: int) -> str:
    return (
        f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<p:presentation xmlns:a=\"{NS_A}\" xmlns:r=\"{NS_R}\" xmlns:p=\"{NS_P}\">"
        "<p:sldMasterIdLst><p:sldMasterId id=\"2147483648\" r:id=\"rId1\"/></p:sldMasterIdLst>"
        "<p:sldIdLst><p:sldId id=\"256\" r:id=\"rId2\"/></p:sldIdLst>"
        f"<p:sldSz cx=\"{slide_w}\" cy=\"{slide_h}\" type=\"custom\"/>"
        "<p:notesSz cx=\"6858000\" cy=\"9144000\"/>"
        "</p:presentation>"
    )


def slide_master_xml() -> str:
    return (
        f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<p:sldMaster xmlns:a=\"{NS_A}\" xmlns:r=\"{NS_R}\" xmlns:p=\"{NS_P}\">"
        f"<p:cSld><p:spTree>{group_shape_xml()}</p:spTree></p:cSld>"
        "<p:clrMap bg1=\"lt1\" tx1=\"dk1\" bg2=\"lt2\" tx2=\"dk2\" accent1=\"accent1\" accent2=\"accent2\" accent3=\"accent3\" accent4=\"accent4\" accent5=\"accent5\" accent6=\"accent6\" hlink=\"hlink\" folHlink=\"folHlink\"/>"
        "<p:sldLayoutIdLst><p:sldLayoutId id=\"2147483649\" r:id=\"rId1\"/></p:sldLayoutIdLst>"
        "<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>"
        "</p:sldMaster>"
    )


def slide_layout_xml() -> str:
    return (
        f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<p:sldLayout xmlns:a=\"{NS_A}\" xmlns:r=\"{NS_R}\" xmlns:p=\"{NS_P}\" type=\"blank\" preserve=\"1\">"
        f"<p:cSld name=\"Blank\"><p:spTree>{group_shape_xml()}</p:spTree></p:cSld>"
        "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>"
        "</p:sldLayout>"
    )


def theme_xml() -> str:
    return (
        f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<a:theme xmlns:a=\"{NS_A}\" name=\"Office Theme\">"
        "<a:themeElements>"
        "<a:clrScheme name=\"Office\">"
        "<a:dk1><a:sysClr val=\"windowText\" lastClr=\"000000\"/></a:dk1>"
        "<a:lt1><a:sysClr val=\"window\" lastClr=\"FFFFFF\"/></a:lt1>"
        "<a:dk2><a:srgbClr val=\"1F2937\"/></a:dk2>"
        "<a:lt2><a:srgbClr val=\"F9FAFB\"/></a:lt2>"
        "<a:accent1><a:srgbClr val=\"2563EB\"/></a:accent1>"
        "<a:accent2><a:srgbClr val=\"10B981\"/></a:accent2>"
        "<a:accent3><a:srgbClr val=\"F59E0B\"/></a:accent3>"
        "<a:accent4><a:srgbClr val=\"EF4444\"/></a:accent4>"
        "<a:accent5><a:srgbClr val=\"8B5CF6\"/></a:accent5>"
        "<a:accent6><a:srgbClr val=\"06B6D4\"/></a:accent6>"
        "<a:hlink><a:srgbClr val=\"0000FF\"/></a:hlink>"
        "<a:folHlink><a:srgbClr val=\"800080\"/></a:folHlink>"
        "</a:clrScheme>"
        "<a:fontScheme name=\"Office\"><a:majorFont><a:latin typeface=\"Arial\"/></a:majorFont><a:minorFont><a:latin typeface=\"Arial\"/></a:minorFont></a:fontScheme>"
        "<a:fmtScheme name=\"Office\"><a:fillStyleLst><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w=\"9525\"><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>"
        "</a:themeElements>"
        "</a:theme>"
    )


def content_types_xml() -> str:
    return (
        f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<Types xmlns=\"{NS_CT}\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Default Extension=\"png\" ContentType=\"image/png\"/>"
        "<Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/>"
        "<Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>"
        "<Override PartName=\"/ppt/presentation.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml\"/>"
        "<Override PartName=\"/ppt/slides/slide1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slide+xml\"/>"
        "<Override PartName=\"/ppt/slideMasters/slideMaster1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml\"/>"
        "<Override PartName=\"/ppt/slideLayouts/slideLayout1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml\"/>"
        "<Override PartName=\"/ppt/theme/theme1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.theme+xml\"/>"
        "</Types>"
    )


def core_props_xml() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<cp:coreProperties xmlns:cp=\"{NS_CP}\" xmlns:dc=\"{NS_DC}\" xmlns:dcterms=\"{NS_DCTERMS}\" xmlns:dcmitype=\"{NS_DCMITYPE}\" xmlns:xsi=\"{NS_XSI}\">"
        "<dc:title>Editable image reconstruction</dc:title>"
        "<dc:creator>image-to-editable-ppt</dc:creator>"
        "<cp:lastModifiedBy>image-to-editable-ppt</cp:lastModifiedBy>"
        f"<dcterms:created xsi:type=\"dcterms:W3CDTF\">{now}</dcterms:created>"
        f"<dcterms:modified xsi:type=\"dcterms:W3CDTF\">{now}</dcterms:modified>"
        "</cp:coreProperties>"
    )


def app_props_xml() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\" xmlns:vt=\"http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes\">"
        "<Application>image-to-editable-ppt</Application>"
        "<PresentationFormat>Custom</PresentationFormat>"
        "<Slides>1</Slides>"
        "</Properties>"
    )


def build(manifest_path: Path) -> Path:
    manifest_path = manifest_path.resolve()
    manifest_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_image = resolve_path(manifest_dir, manifest.get("source_image"))
    if source_image is None or not source_image.exists():
        raise FileNotFoundError(f"source_image not found: {manifest.get('source_image')!r}")

    with Image.open(source_image) as img:
        image_w, image_h = img.size

    slide_px = manifest.get("slide_size_px") or manifest.get("canvas_px") or [image_w, image_h]
    coord_w, coord_h = float(slide_px[0]), float(slide_px[1])
    slide_in = manifest.get("slide_size_in")
    if slide_in:
        slide_w_in, slide_h_in = float(slide_in[0]), float(slide_in[1])
    elif abs((coord_w / coord_h) - (16 / 9)) < 0.02:
        slide_w_in, slide_h_in = 13.333333, 7.5
    else:
        slide_w_in = 10.0
        slide_h_in = 10.0 * coord_h / coord_w
    slide_w = int(round(slide_w_in * EMU_PER_INCH))
    slide_h = int(round(slide_h_in * EMU_PER_INCH))
    scale_x = slide_w / coord_w
    scale_y = slide_h / coord_h

    output = resolve_path(manifest_dir, manifest.get("output_pptx"))
    if output is None:
        output = manifest_dir / f"{source_image.stem}_rebuilt.pptx"
    output.parent.mkdir(parents=True, exist_ok=True)

    crop_dir = resolve_path(manifest_dir, manifest.get("crop_dir"))
    if crop_dir is None:
        crop_dir = manifest_dir / f"{source_image.stem}_crops"
    crop_dir.mkdir(parents=True, exist_ok=True)

    elements_xml: list[str] = []
    media_items: list[MediaItem] = []
    shape_id = 2
    media_index = 1

    image_types = {"image", "photo", "icon", "logo", "picture"}
    text_types = {"text", "number", "label"}
    shape_types = {"shape", "box", "rounded_box", "bar", "footer", "sidebar", "divider", "line"}

    for i, el in enumerate(manifest.get("elements", []), start=1):
        if el.get("visible") is False:
            continue
        el_type = str(el.get("type", "shape"))
        if el_type in image_types:
            cropped = crop_or_copy_image(manifest_dir, source_image, crop_dir, el, i)
            target_name = f"image{media_index}.png"
            media = MediaItem(rid=f"rId{media_index + 1}", source_path=cropped, target_name=target_name)
            media_items.append(media)
            elements_xml.append(picture_xml(shape_id, el, media, scale_x, scale_y))
            media_index += 1
        elif el_type in text_types:
            elements_xml.append(text_xml(shape_id, el, scale_x, scale_y))
        elif el_type in shape_types:
            elements_xml.append(shape_xml(shape_id, el, scale_x, scale_y))
        else:
            raise ValueError(f"Unsupported element type: {el_type}")
        shape_id += 1

    bg = normalize_color(manifest.get("background"), None)
    slide_rels = [("rId1", f"{NS_OFFICE_REL}/slideLayout", "../slideLayouts/slideLayout1.xml")]
    for media in media_items:
        slide_rels.append((media.rid, f"{NS_OFFICE_REL}/image", f"../media/{media.target_name}"))

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml())
        z.writestr("_rels/.rels", rels_xml([
            ("rId1", f"{NS_OFFICE_REL}/officeDocument", "ppt/presentation.xml"),
            ("rId2", f"{NS_OFFICE_REL}/extended-properties", "docProps/app.xml"),
            ("rId3", f"{NS_OFFICE_REL}/metadata/core-properties", "docProps/core.xml"),
        ]))
        z.writestr("docProps/core.xml", core_props_xml())
        z.writestr("docProps/app.xml", app_props_xml())
        z.writestr("ppt/presentation.xml", presentation_xml(slide_w, slide_h))
        z.writestr("ppt/_rels/presentation.xml.rels", rels_xml([
            ("rId1", f"{NS_OFFICE_REL}/slideMaster", "slideMasters/slideMaster1.xml"),
            ("rId2", f"{NS_OFFICE_REL}/slide", "slides/slide1.xml"),
        ]))
        z.writestr("ppt/slides/slide1.xml", slide_xml(slide_w, slide_h, bg, elements_xml))
        z.writestr("ppt/slides/_rels/slide1.xml.rels", rels_xml(slide_rels))
        z.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml())
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", rels_xml([
            ("rId1", f"{NS_OFFICE_REL}/slideLayout", "../slideLayouts/slideLayout1.xml"),
            ("rId2", f"{NS_OFFICE_REL}/theme", "../theme/theme1.xml"),
        ]))
        z.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml())
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", rels_xml([
            ("rId1", f"{NS_OFFICE_REL}/slideMaster", "../slideMasters/slideMaster1.xml"),
        ]))
        z.writestr("ppt/theme/theme1.xml", theme_xml())
        for media in media_items:
            z.write(media.source_path, posixpath.join("ppt/media", media.target_name))

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build editable PPTX from an image reconstruction manifest.")
    parser.add_argument("manifest", type=Path, help="Path to reconstruction manifest JSON.")
    args = parser.parse_args()
    output = build(args.manifest)
    print(output)


if __name__ == "__main__":
    main()
