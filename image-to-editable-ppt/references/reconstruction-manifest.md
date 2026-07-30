# Reconstruction Manifest

Use this schema with `scripts/build_editable_pptx.py` to convert one raster image into one editable PowerPoint slide.

## Top-Level Fields

```json
{
  "source_image": "input.png",
  "output_pptx": "input_rebuilt.pptx",
  "slide_size_px": [1440, 810],
  "slide_size_in": [13.333333, 7.5],
  "crop_dir": "input_crops",
  "background": "#FFFFFF",
  "elements": []
}
```

- `source_image`: Required. Path to the original image. Relative paths resolve from the manifest folder.
- `output_pptx`: Optional. Defaults to `<source stem>_rebuilt.pptx` beside the manifest.
- `slide_size_px`: Optional. Pixel coordinate space used by element bboxes. Defaults to the source image dimensions.
- `slide_size_in`: Optional. PowerPoint slide size. Defaults to 13.333333 x 7.5 for 16:9 images; otherwise width 10 inches with height scaled to the source aspect ratio.
- `crop_dir`: Optional. Where cropped photo/icon assets are written. Defaults to `<source stem>_crops`.
- `background`: Optional color for the slide background. Use hex RGB such as `#F7F7F7`.
- `elements`: Required list. Elements are inserted in list order; earlier elements sit behind later elements.

## Coordinates

Use either `bbox` or `bbox_xyxy`.

```json
{ "bbox": [x, y, width, height] }
{ "bbox_xyxy": [left, top, right, bottom] }
```

Coordinates are in source pixels unless `slide_size_px` defines a different coordinate space. Keep boxes tight to the visible element.

## Editable Shapes

```json
{
  "type": "shape",
  "name": "bottom bar",
  "shape": "rect",
  "bbox": [0, 728, 1440, 82],
  "fill": "#111827",
  "stroke": "none",
  "opacity": 1
}
```

Supported shapes: `rect`, `roundRect`, `ellipse`, `line`.

Useful aliases for `type`: `box`, `rounded_box`, `bar`, `footer`, `sidebar`, `divider`. These are all emitted as editable native shapes.

Use `stroke_width` in points. Use `fill: "none"` or `stroke: "none"` for no fill/line.

## Editable Text And Numbers

```json
{
  "type": "text",
  "name": "title",
  "bbox": [80, 72, 760, 72],
  "text": "Rebuilt headline",
  "font": "Arial",
  "font_size": 34,
  "bold": true,
  "color": "#111111",
  "align": "left",
  "valign": "top",
  "margin": 0
}
```

Useful aliases for `type`: `number`, `label`.

Text elements can also include `fill`, `stroke`, and `shape` when the text itself needs an editable colored box, but prefer separate shape and text elements for precise layering.

Alignment values:

- `align`: `left`, `center`, `right`, `justify`
- `valign`: `top`, `mid`, `bottom`

## Cropped Picture Objects

```json
{
  "type": "image",
  "name": "hero photo",
  "bbox": [860, 88, 420, 280],
  "crop": true
}
```

Useful aliases for `type`: `photo`, `icon`, `logo`, `picture`.

When `source` is omitted, the script crops this element from `source_image` using the element bbox and inserts the crop as a separate picture object. When `source` is present, that file is inserted instead.

Use `crop_name` when stable asset filenames matter:

```json
{
  "type": "icon",
  "name": "warning icon",
  "bbox": [1220, 742, 32, 32],
  "crop_name": "warning-icon.png"
}
```

## Example

```json
{
  "source_image": "example.png",
  "output_pptx": "example_rebuilt.pptx",
  "background": "#FFFFFF",
  "elements": [
    {
      "type": "sidebar",
      "name": "left rail",
      "bbox": [0, 0, 104, 810],
      "fill": "#1F2937",
      "stroke": "none"
    },
    {
      "type": "rounded_box",
      "name": "number badge",
      "shape": "roundRect",
      "bbox": [132, 96, 64, 64],
      "fill": "#2563EB",
      "stroke": "none"
    },
    {
      "type": "number",
      "name": "badge number",
      "bbox": [132, 101, 64, 52],
      "text": "01",
      "font": "Arial",
      "font_size": 26,
      "bold": true,
      "color": "#FFFFFF",
      "align": "center",
      "valign": "mid",
      "margin": 0
    },
    {
      "type": "text",
      "name": "heading",
      "bbox": [220, 92, 620, 72],
      "text": "Editable PPT reconstruction",
      "font": "Arial",
      "font_size": 32,
      "bold": true,
      "color": "#111827"
    },
    {
      "type": "photo",
      "name": "source photo crop",
      "bbox": [930, 96, 380, 240],
      "crop": true
    },
    {
      "type": "footer",
      "name": "bottom bar",
      "bbox": [104, 742, 1336, 68],
      "fill": "#F3F4F6",
      "stroke": "none"
    }
  ]
}
```
