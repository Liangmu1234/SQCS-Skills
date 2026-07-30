---
name: image-to-editable-ppt
description: Convert screenshots, raster images, UI mockups, diagrams, posters, or other bitmap layouts into editable PowerPoint decks. Use when Codex must rebuild image text, numbers, rounded boxes, footers, sidebars, labels, callouts, bars, lines, and panels as editable PPT objects, crop photos and icons from the original image into separate picture objects, preserve all relative positions, and output one .pptx per input image.
---

# Image To Editable PPT

## Core Contract

Rebuild the image as native PowerPoint content. Text, numbers, rounded boxes, footer bars, sidebars, labels, callouts, rules, panels, and simple decorations must be editable PPT text/shapes. Photos and icons must be cropped out of the original image and reinserted as separate picture objects at their original positions.

Default to one one-slide `.pptx` per input image. Do not place the whole source image as a flattened slide background unless the user explicitly asks for a trace or comparison slide.

## Workflow

1. Create an output folder beside the input images, with one subfolder per source image for cropped picture assets and a manifest.
2. Measure the source image at original pixel size. Use its aspect ratio as the slide aspect ratio unless the user provides a target size.
3. Inventory every visible element in reading/z-order:
   - editable text and numbers, including font family guess, size, color, weight, alignment, and line breaks
   - editable shapes: rectangles, rounded rectangles, badges, bars, sidebars, bottom bars, dividers, strokes, fills, and shadows when material
   - separate picture objects: photos, screenshots, logos, icons, pictograms, and complex marks that should remain visually exact
4. Crop each photo/icon from the original image with the tight original bounding box. Keep each crop as its own image object. Use padding only when the visible asset includes that padding.
5. Recreate the slide from a manifest. Prefer the bundled helper script for precise placement: `scripts/build_editable_pptx.py`.
6. Render/inspect the PPTX with the Presentations skill or available PowerPoint tooling. Compare with the source image for position, scale, order, and text accuracy. Iterate until differences are intentional.

## Manifest Method

Use `references/reconstruction-manifest.md` when preparing a manifest or using the helper script.

Minimal run pattern:

```bash
python scripts/build_editable_pptx.py path/to/manifest.json
```

The manifest uses pixel coordinates from the source image. The script maps them to slide coordinates, creates native shapes/text, crops image/icon assets from the source image, and emits a one-slide `.pptx`.

## Reconstruction Rules

- Preserve relative positions first, then visual styling. Pixel-accurate geometry matters more than choosing the exact original font.
- Keep text editable. OCR output must be proofread against the image; do not leave OCR guesses unreviewed.
- Keep numbers editable unless they are part of a cropped icon/logo/photo.
- Rebuild rounded boxes as editable rounded-rectangle shapes. Put editable text/number objects above them rather than baking text into the shape image.
- Rebuild bottom bars and sidebars as editable rectangles or rounded rectangles, then layer text/icons over them.
- Crop logos/icons/photos as independent pictures from the original image. If an icon is simple enough to rebuild as an editable shape and the user requested full editability, ask or make a clearly noted judgment call.
- Maintain z-order by appending background shapes first, then photos/icons, then overlays, labels, and foreground text.
- Use the original image only as source material and QA reference. The final slide should not depend on a full-slide screenshot layer.
- For multiple input images, create separate manifests and separate `.pptx` outputs. Name outputs from the source filename, for example `source-name_rebuilt.pptx`.

## Verification Checklist

- One `.pptx` exists for each input image.
- The slide size matches the source aspect ratio or requested target.
- Text, numbers, boxes, bars, sidebars, and dividers are editable PPT objects.
- Photos and icons are separate cropped picture objects, not part of a full-slide raster.
- Relative positions and z-order match the original image.
- Rendered preview has no clipped text, unexpected wrapping, missing crops, or shifted elements.
