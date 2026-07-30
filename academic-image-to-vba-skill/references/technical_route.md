# Technical Route

This skill uses a hybrid reconstruction pipeline:

```text
Input image / screenshot
        ↓
Visual inspection + coordinate mapping
        ↓
Semantic decomposition
        ↓
layout.json
        ↓                    ↓
PPTX builder             VBA macro generator
        ↓                    ↓
Hybrid editable PPTX     Office macro reconstruction code
```

## Why hybrid reconstruction
Fully editable reconstruction is slow and often inaccurate for photos, dense screenshots, small icons, and decorative textures. A hybrid approach is more reliable:

- Redraw layout, text, cards, simple charts, tables, arrows, and labels.
- Crop complex regions as PNG assets.
- Keep all assets positioned inside PowerPoint so the slide remains easy to edit.

## Recommended quality levels

### Level 1: Fast mixed version
- Editable text and main blocks.
- Complex charts/screenshots inserted as cropped assets.
- Best for tutorials and quick deliverables.

### Level 2: High-editability version
- Rebuild charts, tables, axes, legends, and icons as editable shapes.
- Use cropped image only for photos/logos.
- Best for client PPT revisions.

### Level 3: Near-1:1 restoration
- Manual shape tuning.
- Font and spacing adjustments.
- Render preview and compare repeatedly.
- Best when user demands strict fidelity.

## Practical limitation
No OCR/layout method is perfect. For Chinese text and dense screenshots, always verify copied text manually.
