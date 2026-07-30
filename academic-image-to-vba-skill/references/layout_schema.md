# Layout JSON Schema

Coordinates use inches by default. Default slide size is 13.333 x 7.5 inches.

## Minimal example

```json
{
  "slide": {"width": 13.333, "height": 7.5, "unit": "in"},
  "theme": {"font": "Microsoft YaHei", "background": "#FFFFFF"},
  "elements": [
    {
      "type": "rect",
      "name": "top_bar",
      "x": 0,
      "y": 0,
      "w": 13.333,
      "h": 0.7,
      "fill": "#101828",
      "line": "#101828"
    },
    {
      "type": "text",
      "name": "title",
      "x": 0.45,
      "y": 0.18,
      "w": 8,
      "h": 0.35,
      "text": "Editable PPT Reconstruction",
      "font": "Microsoft YaHei",
      "font_size": 18,
      "bold": true,
      "color": "#FFFFFF",
      "align": "left"
    }
  ]
}
```

## Supported element types

### `rect`
```json
{
  "type": "rect",
  "name": "card_1",
  "x": 1.0,
  "y": 1.0,
  "w": 4.0,
  "h": 2.0,
  "fill": "#FFFFFF",
  "line": "#D0D5DD",
  "line_width": 1,
  "radius": 0.12,
  "opacity": 1.0
}
```

### `text`
```json
{
  "type": "text",
  "name": "caption",
  "x": 1.2,
  "y": 1.25,
  "w": 3.5,
  "h": 0.5,
  "text": "标题文本",
  "font": "Microsoft YaHei",
  "font_size": 16,
  "bold": true,
  "italic": false,
  "color": "#101828",
  "align": "center",
  "valign": "middle"
}
```

### `line`
```json
{
  "type": "line",
  "name": "divider",
  "x1": 1.0,
  "y1": 2.0,
  "x2": 6.0,
  "y2": 2.0,
  "color": "#98A2B3",
  "width": 1.5
}
```

### `image`
```json
{
  "type": "image",
  "name": "cropped_chart",
  "path": "assets/cropped_chart.png",
  "x": 0.8,
  "y": 1.1,
  "w": 5.2,
  "h": 2.8
}
```

### `table`
```json
{
  "type": "table",
  "name": "data_table",
  "x": 0.8,
  "y": 1.1,
  "w": 5.2,
  "h": 2.8,
  "rows": 3,
  "cols": 3,
  "data": [["A", "B", "C"], ["1", "2", "3"], ["4", "5", "6"]],
  "font_size": 10,
  "border": "#D0D5DD",
  "fill": "#FFFFFF",
  "text_color": "#101828"
}
```
