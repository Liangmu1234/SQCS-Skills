---
name: ai-visual-ppt-composer
description: Build high-end editable PowerPoint decks by combining AI-generated no-text visual backgrounds, precise HTML/CSS/SVG layout previews, and PPTXGenJS native editable reconstruction. Use for Codex + Image 2 PPT workflows, canvas-to-PPT, image-style-to-editable-PPT, advanced PPT beautification, pitch decks, academic decks, and competition roadshow slides. Do not use for simple document summarization or plain text outlines without visual design requirements.
---

# AI Visual PPT Composer

## Core principle

Use this skill when the user wants a PPT that is both visually high-end and structurally editable.

The workflow is not “turn a finished image into PPT by guessing every pixel.” The workflow is layered composition:

1. **Background layer**: AI image model or existing visual assets generate only no-text background, atmosphere, lighting, illustration, texture, and decorative structure.
2. **Layout layer**: HTML/CSS/SVG controls exact placement, hierarchy, spacing, typography, data blocks, diagrams, and visual rhythm.
3. **PPTX layer**: PPTXGenJS rebuilds the slide with native editable PowerPoint text, shapes, tables, charts, and images.
4. **Preview layer**: Generate PNG/HTML previews for visual inspection, but do not use preview screenshots as the final editable slide unless the user explicitly accepts image-only output.

The target result is: **AI visual quality + code-level accuracy + PPT native editability**.

## When to use

Use this skill for requests like:

- “用 Codex + Image2 做高级 PPT”
- “把图片风格变成可编辑 PPT”
- “用 canvas / html 画页面，再转 PPT”
- “先生成高级背景，再把文字精准叠上去”
- “做竞赛路演 PPT / 学术汇报 PPT / 思政汇报 PPT / 商业计划书 PPT”
- “文字必须准确，画面要高级，最后输出 pptx”
- “不要 AI 乱码文字，背景交给生图模型，文字交给代码”

Do not use this as a naive OCR/image-to-PPT converter. If the user provides a finished slide image, use it as a style/reference image, then reconstruct with layered editable elements.

## Required output discipline

Always separate the slide into these layers:

- `background`: full-bleed raster image or gradient/solid background. It must contain no readable text, no fake labels, no numbers, no logo, no watermark.
- `decorative_shapes`: SVG/PPT shapes, glow blocks, transparent cards, lines, badges, dividers, ornaments.
- `editable_text`: all meaningful titles, subtitles, body text, footnotes, numbers, labels, and page markers.
- `editable_diagrams`: timelines, process flows, quadrant charts, matrices, architecture diagrams, tables, and data visuals.
- `raster_images`: photos, generated illustrations, icons, product images, screenshots, and texture assets.

Never flatten important text into the background. Text can be rasterized only when the user explicitly requests a decorative title PNG, and even then you should also include an editable hidden or nearby text backup when practical.

## Default deck specification

Use 16:9 widescreen unless the user specifies another ratio.

Default coordinate system:

- PowerPoint units: inches.
- Wide slide size: `13.333 x 7.5`.
- Preview size: `1920 x 1080`.
- Safe margin: `0.45-0.65 in`.
- Main title size: normally `28-48 pt`, depending on deck style.
- Section title size: normally `24-36 pt`.
- Body size: normally `12-20 pt`.
- Caption/footnote size: normally `8-11 pt`.

Use Chinese-friendly fonts by default:

- Preferred Chinese font: `Microsoft YaHei`, `PingFang SC`, `Source Han Sans SC`, or `Noto Sans CJK SC`.
- Formal policy/academic deck: `Microsoft YaHei`, `Source Han Sans SC`, `Noto Serif CJK SC` for selected title accents.
- Tech/commercial deck: `HarmonyOS Sans SC`, `Microsoft YaHei UI`, `DIN`, `Aptos`, `Inter`.

## Workflow

### Step 1 — Understand the job

Before writing code, identify:

- deck type: academic, roadshow, course report, commercial product, tutorial, government/policy, cute education, etc.
- source: outline, existing PPT, reference image, image PPT, markdown, document, or rough notes.
- desired output: `.pptx`, previews `.png`, both, or scaffold only.
- visual direction: premium tech, red-gold policy, clean academic, cute education, e-commerce, etc.
- editability requirements: which parts must be editable and which can remain raster.

If information is missing, make a practical assumption and proceed. Do not block unless the missing information prevents generation.

### Step 2 — Create a slide plan

Create a slide-by-slide plan with:

- one message per slide
- visual hierarchy
- content blocks
- background intent
- layout grid
- key editable elements
- possible AI background prompt

Use `references/prompt-templates.md` for background prompts and negative prompts.

### Step 3 — Generate or collect backgrounds

For each slide, background assets must avoid text.

Background prompt rules:

- Include scene, palette, lighting, texture, depth, and composition.
- Ask for empty content regions where text will be placed.
- Explicitly forbid readable text, letters, numbers, charts, logos, watermark, UI labels, pseudo-glyphs, and fake diagrams.
- Prefer “visual atmosphere” over “wireframe.”

If no image-generation tool is available in the environment, create clear prompts and placeholder background paths in `deck.json`. The user can generate backgrounds externally and place them into the listed paths.

### Step 4 — Build a structured deck JSON

Use `references/deck.schema.json` as the data contract.

Each slide should contain:

- `id`
- `title`
- `background`
- `elements`
- optional `notes`
- optional `background_prompt`

Use native elements for all meaningful text and shapes.

### Step 5 — Render preview and PPTX

Preferred implementation:

1. Create a working project with `scripts/avpc_init_project.py`.
2. Fill `deck.json`.
3. Install dependencies with `npm install`.
4. Run `npm run build` or `node scripts/avpc_build.mjs deck.json output`.
5. Inspect `output/deck_preview.html`, `output/*.pptx`, and optional screenshots.
6. Fix layout collisions and rerun.

### Step 6 — Quality check

Before finalizing, verify:

- no AI-generated乱码 appears in backgrounds.
- all meaningful text is editable in PPT.
- slide titles are visually consistent but not mechanically identical.
- text boxes stay inside safe margins.
- hierarchy is clear: title > subtitle > block title > body > caption.
- content density is readable on screen.
- images are not stretched unnaturally.
- backgrounds do not overpower text.
- exported PPTX opens without dependency errors.

## Script usage

This skill includes helper scripts.

### Scaffold a project

```bash
python scripts/avpc_init_project.py --target ./my-ppt-project --title "AI Visual PPT"
cd my-ppt-project
npm install
npm run build
```

### Build an existing deck JSON

```bash
node scripts/avpc_build.mjs deck.json output
```

### Validate deck JSON before build

```bash
python scripts/avpc_validate_deck.py deck.json
```

## Final response format when using this skill

When you finish a task, report:

- where the `.pptx` is located
- where preview files are located
- which elements are editable
- which background/image assets remain raster
- any limitations or user-side steps, especially if backgrounds need to be generated externally

Do not over-explain the internal process unless the user asks.

## Important implementation rule

When asked to create a Codex-compatible skill, preserve this folder structure:

```text
ai-visual-ppt-composer/
  SKILL.md
  scripts/
  references/
  assets/
```

The folder itself is the installable skill package.
