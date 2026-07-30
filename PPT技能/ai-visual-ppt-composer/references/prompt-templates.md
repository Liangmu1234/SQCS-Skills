# Prompt Templates for AI Visual PPT Backgrounds

## Universal no-text negative prompt

Use this on every background prompt:

```text
No readable text, no letters, no numbers, no logo, no watermark, no QR code, no pseudo UI labels, no fake charts, no fake document text, no random glyphs. Leave clean empty areas for later editable text overlay. Background and decorative visual elements only.
```

## Universal background prompt structure

```text
Create a 16:9 high-end presentation slide background for [deck type].
Visual mood: [premium / academic / cinematic / red-gold policy / tech / cute education].
Scene concept: [visual metaphor].
Composition: leave a clean empty area on [left/right/top/center] for title and content overlay; keep the visual focus on [region].
Palette: [colors].
Lighting: [soft glow / cinematic rim light / clean daylight / subtle gradient].
Texture: [glassmorphism / paper grain / metallic / soft illustration / minimal].
Depth: [layered panels / subtle perspective / floating elements].
No readable text, no letters, no numbers, no logo, no watermark, no QR code, no pseudo UI labels, no fake charts, no fake document text, no random glyphs.
```

## Red-gold policy deck background

```text
16:9 premium Chinese policy presentation background, elegant red and warm gold palette, subtle silk texture, soft golden light beams, abstract national development motif, refined layered geometry, dignified and modern, clean empty title area on the left, subtle decorative arc and particle glow on the right, no readable text, no letters, no numbers, no logo, no watermark, no pseudo glyphs.
```

## Tech roadshow background

```text
16:9 premium technology pitch deck background, deep navy and electric blue palette, cinematic gradient, abstract AI network particles, glassmorphism panels, subtle spatial depth, clean empty content area in the center-left, high-end startup roadshow visual style, no readable text, no letters, no numbers, no logo, no watermark, no fake UI labels.
```

## Academic report background

```text
16:9 clean academic presentation background, light neutral base, subtle grid texture, transparent research diagram atmosphere, soft blue-gray accents, restrained professional style, clean empty areas for title and body text, no readable text, no letters, no numbers, no fake charts, no watermark.
```

## Cute education deck background

```text
16:9 cute kindergarten education presentation background, soft pastel color palette, warm paper-cut illustration style, rounded shapes, gentle lighting, playful but clean, leave large empty areas for editable text and activity steps, no readable text, no letters, no numbers, no watermark.
```

## E-commerce/product feature background

```text
16:9 premium product feature presentation background, clean studio lighting, soft gradient, product display atmosphere, subtle floating feature-card placeholders without text, modern commercial design, leave space for exact editable selling points, no readable text, no letters, no numbers, no logo, no watermark, no pseudo labels.
```

## Decorative title PNG prompt

Only use when the user explicitly asks for a title to be rasterized as a visual effect. Keep a native PPT text duplicate for editability.

```text
Create a transparent PNG title typography effect for the exact text: “[TEXT]”.
Style: [glowing / metallic / red-gold / cyber / glass].
High clarity, sharp edges, no extra words, no misspellings, transparent background.
```

Important: title PNG generation is risky for Chinese text. Prefer native PPT text plus glow/shadow effects whenever possible.
