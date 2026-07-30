---
name: academic-image-to-vba
description: Convert uploaded PPT/page/academic images or screenshots into editable PowerPoint/Office VBA reconstruction outputs. Use when the user asks to turn a reference slide, paper figure, UI screenshot, academic poster, or PPT image into editable PPT, VBA, or a hybrid editable slide. Recreate text, boxes, lines, arrows, simple icons, charts, and tables as editable Office shapes; preserve complex photos/screenshots/logos as cropped PNG assets. Do not use for ordinary text-to-PPT generation, PSD editing, or pure image enhancement.
metadata:
  short-description: Rebuild reference images as editable PPT/VBA hybrid slides
---

# Academic Image to VBA / Editable PPT Reconstruction

## Goal
Convert a static image into an editable PowerPoint reconstruction with high visual fidelity.

Default output is a **hybrid editable version**:
- Editable: text, headings, cards, labels, lines, arrows, tables, charts, simple geometric graphics.
- Bitmap fallback: complex photos, screenshots, dense UI panels, logos, icons that would lose fidelity if redrawn.

Never claim that every element is editable if cropped assets were used. State clearly which parts are editable and which are inserted as images.

## Trigger examples
Use this skill when the user says things like:
- “把这页 PPT 拆成可编辑元素”
- “图片转可编辑 PPT / VBA”
- “根据这张图生成 Office VBA 形状重建代码”
- “保留图片部分，文字和形状做成可编辑”
- “混合版 PPTX / 可编辑版 PPT / Academic Image to VBA”

Do not use this skill when the user only wants a newly designed deck from an outline, unless they specifically ask to reconstruct a reference image or make it editable.

## Reconstruction principle
1. **Fidelity first, editability second.** Preserve the visual look before over-redrawing difficult assets.
2. **Semantic grouping.** Rebuild obvious components as named shapes/groups: title, section tabs, cards, charts, captions, table blocks, footer, logo area.
3. **Use bitmap fallback aggressively for complex visuals.** Crop and insert exact image regions for photos, screenshots, dense icons, and decorative textures.
4. **Text must be real Office text when legible.** Recreate text boxes with font, size, color, alignment, and hierarchy.
5. **Charts/tables:** Prefer editable Office shapes/tables if the data can be read. Otherwise insert the chart/table as a cropped image and optionally add editable labels above it.
6. **Verify by rendering a preview.** Compare screenshot/reference against output and fix scale, alignment, font hierarchy, and asset placement.

## Expected deliverables
When reconstructing a single image, produce this folder structure:

```text
output/
  reconstructed.pptx          # hybrid editable PPTX
  reconstruction_macro.bas    # VBA macro that rebuilds the slide
  layout.json                 # canonical layout specification
  preview.png                 # rendered preview if possible
  assets/
    cropped_*.png             # image fallbacks used inside the slide
```

For multi-page tasks, use one layout JSON per slide or a `slides` array in a single JSON file.

## Workflow

### 1. Inspect image and set canvas
- Determine aspect ratio and intended slide size.
- Default to 16:9 widescreen, 13.333 x 7.5 inches, unless the user provides another size.
- Use the reference image dimensions to map all element coordinates proportionally.

### 2. Segment elements
Classify each visual region as one of:
- `text`: headings, labels, callouts, numbers, captions.
- `rect`: filled panels, cards, badges, background blocks.
- `line`: rules, connectors, dividers, axes.
- `image`: cropped asset fallback.
- `table`: editable table where structure is clear.
- `group`: conceptual group, implemented as multiple Office shapes.

### 3. Build `layout.json`
Use the schema documented in `references/layout_schema.md`.
Coordinates are in inches by default, relative to the slide canvas.

### 4. Generate outputs
Prefer scripts over handwritten macro code:

```bash
python scripts/layout_to_vba.py output/layout.json --out output/reconstruction_macro.bas
python scripts/build_pptx.py output/layout.json --out output/reconstructed.pptx
```

If scripts cannot cover a shape, extend the script or add a clearly marked manual VBA block.

### 5. Quality pass
Check these before final delivery:
- Slide size matches the reference aspect ratio.
- Major blocks align with reference within a few pixels.
- Text is not stretched, garbled, or substituted with unrelated content.
- Chinese text uses a compatible font such as Microsoft YaHei, SimHei, or Source Han Sans.
- Cropped assets are sharp and not re-compressed excessively.
- Output includes both PPTX and `.bas` when the user asks for VBA or “skill” style reconstruction.

## Style rules for Chinese PPT reconstruction
- Preserve user-provided copy exactly. Do not invent, paraphrase, or “beautify” text unless asked.
- Avoid changing colors when the user asks for 1:1 restoration.
- If a logo/icon is inaccurate when redrawn, crop it as PNG instead.
- Do not stretch text horizontally to force a match; adjust font size, line breaks, or text box width instead.
- Keep consistent font family for same-level headings.

## Failure handling
If exact reconstruction is not possible, still produce a useful hybrid result:
- Explain which parts are editable.
- Explain which parts were inserted as cropped images.
- Provide a clear next-step list for improving editability.

## Prompt pattern to follow internally
When working on a user image:

```text
I will reconstruct the image as a hybrid editable PowerPoint:
1. Set canvas and coordinate scale.
2. Recreate layout/text/shapes as editable Office elements.
3. Crop complex regions as assets.
4. Generate layout.json, PPTX, and VBA macro.
5. Render preview and revise alignment.
```
