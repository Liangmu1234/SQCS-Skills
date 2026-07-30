---
name: ppt-gen
description: Convert a user-provided slide image, screenshot, or reference PNG/JPG into a polished editable PowerPoint PPTX in the same dark enterprise AI report style used for the "下半年工作规划：AI+流程智能化深化落地" slide. Use when the user asks to turn an image into a final downloadable .pptx, preserve the reference layout/background feeling, use Microsoft YaHei, choose matching icons from the local asset cache first regardless of which provider created them, generate missing high-quality assets only when cache candidates are unsuitable, and export through Presentations/artifact-tool by default with editable text, shapes, panels, and diagrams.
---

# PPT Gen

## Contract

Create one editable `.pptx` per input image. Rebuild all meaningful text, labels, bars, cards, dividers, arrows, and diagram structure as native PowerPoint objects. Use raster images only for generated backgrounds, generated icons, complex illustrations, or source crops that are not practical to rebuild.

Use this visual target unless the user overrides it: dark navy technology background, cyan/blue/purple glow accents, rounded translucent panels, clear hierarchy, Microsoft YaHei typography, high-quality local-cache or generated icons, and a final rendered preview that looks like a finished executive/report slide rather than a rough trace.

Do not make the final slide a flattened full-slide screenshot. The source image is a reference and QA target, not the final editable layer.

## Required Tools

- Use Presentations `@oai/artifact-tool` as the default and preferred final deck exporter. Export with `PresentationFile.exportPptx(presentation)` and use PowerPoint COM only as a fallback renderer/exporter when artifact-tool cannot complete the requested PPTX.
- When using artifact-tool, create the deck with `Presentation.create()`, add slides with `presentation.slides.add()`, set the viewport with `slide.setViewportSize(width, height)`, add editable text/shapes/images through artifact-tool objects, then write `Buffer.from(artifactBlob.data)` to the `.pptx`.
- For artifact-tool image insertion, prefer embedding local PNG/JPG assets as base64 `dataUrl` values instead of only passing filesystem paths. Verify the exported PPTX has no zero-byte `ppt/media/*` entries.
- Use `@oai/artifact-tool/presentation-jsx` helpers when useful for fill, stroke, and text style parsing.
- Use the built-in `image_gen` tool first for generated no-text backgrounds and any missing icon assets. If `image_gen` is unavailable or fails to produce usable output, fall back to the `$image-jojo` skill. If `$image-jojo` is unavailable or fails, use `$image-yq` as the final image-generation fallback.
- Use local image tooling such as `System.Drawing`, Pillow, or equivalent for dimensions, contact sheets, chroma-key removal validation, and cropping.
- Use `System.IO.Compression.FileSystem` or equivalent zip inspection to verify PPTX package contents.
- Use `$asset-cache` / `C:\Users\w33938\.codex\skills\asset-cache\scripts\search_cache.py` before generating or selecting any image asset. For icons, search the local cache first and choose by visual/semantic fit without distinguishing whether the asset came from image-gen, image-jojo, image-yq, or manual sources.
- Use `$asset-cache` / `C:\Users\w33938\.codex\skills\asset-cache\scripts\cache_asset.py` to store generated backgrounds, icons, and other reusable pictures in `D:\文档\05-开发\02-AI工具\03-本地缓存库`.
- When using the Codex bundled runtime, call `load_workspace_dependencies` first and display the resolved Node.js executable, Node.js packages path, Python executable, and Python packages path in the working notes or QA file. If `@oai/artifact-tool` cannot be resolved by plain `node`, set `NODE_PATH` to the bundled Node.js packages path before running export scripts.

Practical notes:
- Prefer `image-jojo` directly when built-in `image_gen` is unavailable. If `image-jojo` is unavailable or fails, use `image-yq` as the final option. Generate one clean background and one icon sprite sheet, then crop the sprite sheet locally into transparent PNG icons.
- For transparent icon sheets, use a flat chroma-key background and run `remove_chroma_key.py` before cropping.
- On Windows with Chinese paths, prefer passing absolute paths through environment variables or UTF-8-aware scripts. Avoid brittle `Invoke-Expression` chains that re-encode paths or punctuation.
- If `@oai/artifact-tool` export is unstable for blank presentation construction in the current runtime, use PowerPoint COM as a fallback exporter, but record the fallback and verify the PPTX zip contents afterwards. Even when COM is used for preview rendering, keep artifact-tool as the preferred PPTX authoring/export path.

## Known Local Tool Paths

On this Windows Codex desktop host, these paths were verified on 2026-06-17. Prefer `load_workspace_dependencies` when available, but use these known paths directly if discovery fails or time is short:

- Node.js executable: `C:\Users\w33938\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`
- Node.js packages path / `NODE_PATH`: `C:\Users\w33938\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules`
- Python executable: `C:\Users\w33938\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
- Python packages path: `C:\Users\w33938\.cache\codex-runtimes\codex-primary-runtime\dependencies\python`
- Native binaries path: `C:\Users\w33938\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin`
- Chroma-key script: `C:\Users\w33938\.codex\skills\.system\imagegen\scripts\remove_chroma_key.py`
- Built-in imagegen skill file: `C:\Users\w33938\.codex\skills\.system\imagegen\SKILL.md`
- Image-jojo fallback skill file: `C:\Users\w33938\.codex\skills\image-jojo\SKILL.md`
- Image-yq final fallback skill file: `C:\Users\w33938\.codex\skills\image-yq\SKILL.md`
- Shared asset cache skill file: `C:\Users\w33938\.codex\skills\asset-cache\SKILL.md`

Verified available dependencies:

- Node packages: `@oai/artifact-tool`, `@oai/artifact-tool/presentation-jsx`, `pptxgenjs`, `sharp`.
- Python packages: `PIL` / Pillow, `numpy`.
- Windows/.NET: `System.Drawing`, `System.IO.Compression.FileSystem`.
- PowerPoint COM automation is available as a fallback exporter.

Known missing or not directly exposed:

- Node package `canvas` is not installed; use `sharp`, Pillow, or `System.Drawing` instead.
- Python packages `cv2` and `pptx` are not installed; avoid depending on OpenCV or python-pptx.
- A directly callable `image_gen` tool was not exposed in the current tool list; use `$image-jojo` when image generation is required and `image_gen` is unavailable, then `$image-yq` if `$image-jojo` is unavailable or fails.

## Workflow

1. **Set paths and workspace**
   - Work in the user's provided directory.
   - Create a task asset folder beside the output, for example `<stem>_ppt_gen_assets/`.
   - Put selected local-cache icons under `manual_icons/` or `cache_icons/`, newly generated icons under `imagegen_icons/`, previews under `preview/`, layouts under `layout/`, and QA notes under `qa/`.
   - Name the final file clearly in Chinese when the source is Chinese, for example `<主题>_可编辑版.pptx`.
   - Write the resolved runtime and output paths to `qa/paths.txt`: source image, asset folder, final PPTX, preview PNG, Node.js executable, Node.js packages path, Python executable, and Python packages path.
   - Search the shared cache before generating backgrounds, icon sheets, or other picture assets. Reuse suitable cached assets when they match the requested style and semantics.
   - For artifact-tool projects, add a small `image()` helper that reads local files and embeds them as `data:image/png;base64,...` or `data:image/jpeg;base64,...` so exported PPT media files are valid.

2. **Inspect the source image**
   - Measure exact pixel dimensions and use them as the artifact-tool slide size.
   - Inventory the reference by layers: background, logos, title/subtitle, narrative bar, main panels, process/timeline, bottom support/value cards, footer.
   - OCR manually and proofread Chinese text against the image. Preserve line breaks where they affect layout.

3. **Generate a clean background**
   - Use built-in `image_gen` first to create a no-text background matching the source style. If it is unavailable or the output is unusable, use `$image-jojo` instead. If `$image-jojo` is unavailable or fails, use `$image-yq` as the final option.
   - Prompt for: full-bleed 16:9 or source-ratio dark navy technology background, cyan glows, subtle particle wave, bottom light grid, empty regions for editable content.
   - Explicitly forbid readable text, letters, numbers, logos, UI labels, watermarks, fake glyphs, charts, and panels.
   - Copy the generated background from `$CODEX_HOME/generated_images/...`, the `$image-jojo` output path, the `$image-yq` output path, or the tool-reported local path into the task asset folder. Do not delete the original generated file.
   - Also copy the selected generated background into `D:\文档\05-开发\02-AI工具\03-本地缓存库\01-背景\<provider>\` and append metadata through the asset-cache helper.

4. **Select or generate icons**
   - Search `D:\文档\05-开发\02-AI工具\03-本地缓存库\02-图标\` first, including `manual\`, `image-gen\`, `image-jojo\`, and `image-yq\`. Pick icons by semantic match, visual style, transparency quality, and similarity to the source slide, not by provider.
   - If the best cached icons are black/dark SVG or PNG glyphs but semantically closer to the reference, recolor them locally to cyan/blue transparent PNGs and use those task-local derivatives.
   - Copy selected reusable cached icons into the task asset folder (`manual_icons/` or `cache_icons/`) and build a contact sheet for visual QA.
   - Only generate new icons when the local cache has no suitable visual/semantic match.
   - When generation is needed, generate a sprite sheet rather than many one-off icon calls when the slide needs many icons.
   - If `image_gen` is unavailable, use `image-jojo` for the sprite sheet. If `image-jojo` is also unavailable or fails, use `image-yq` for the sprite sheet. Then remove the chroma key locally and crop the alpha sheet into individual PNGs.
   - Recommended prompt: a `4 x 4` grid of premium enterprise AI workflow icons on a perfectly flat solid `#00ff00` chroma-key background, no labels, no logo, no watermark, no text except exact `AI` if an AI cube icon is required.
   - Use subjects that match the slide semantics: target, growth chart, AI cube, cycle/check, document, robot, layers/support, gear/rule engine, cloud/platform, template document, shield/quality, cubes/standard pattern, people/efficiency, process nodes, approval stamp, method library.
   - Run `$CODEX_HOME/skills/.system/imagegen/scripts/remove_chroma_key.py` with `--auto-key border --soft-matte --despill`.
   - Crop the alpha sheet into individual transparent PNG icons. Trim transparent edges using an alpha threshold, then resize onto a square canvas so icons fill the box without clipping glow.
   - Build a dark contact sheet and visually check that icons have clean edges and readable scale.
   - Copy newly generated sprite sheets and final cropped reusable icons into `D:\文档\05-开发\02-AI工具\03-本地缓存库\02-图标\<provider>\` and append metadata through the asset-cache helper.
   - Copy any generated or reusable non-background, non-icon pictures into `D:\文档\05-开发\02-AI工具\03-本地缓存库\03-图片\<provider>\` and append metadata through the asset-cache helper.

5. **Reconstruct the slide**
   - Use pixel coordinates directly from the source image.
   - Add background image first.
   - Add editable rounded panels, bars, dividers, arrows, bullets, and footer shapes next.
   - Add selected local-cache or generated PNG icons as separate image objects.
   - Add all text as native editable text boxes using `Microsoft YaHei`.
   - Use cyan for primary titles, white for body text, purple for AI/automation emphasis, and transparent dark fills for panels.
   - Keep all text inside its containers; use `autoFit: "shrinkText"` only as a safety net, not as a substitute for correct sizing.

6. **Render and iterate**
   - Export `preview/slide-01.png`, `preview/deck-montage.webp`, and `layout/slide-01.layout.json`.
   - Inspect the preview at full size. Fix any clipped text, icon scale issues, panel misalignment, weak contrast, or accidental overlap.
   - Prefer moving/resizing objects over changing the source text.
   - If any icon still shows fringe, crop residue, poor contrast, broken rendering, or weak similarity to the source image, replace only that icon asset and re-export before touching the slide layout.

7. **Export and verify**
   - Export the final `.pptx` through `PresentationFile.exportPptx`.
   - Verify the file exists and is non-empty.
   - Inspect the PPTX as a zip:
     - `ppt/presentation.xml` exists
     - `ppt/slides/slide1.xml` exists
     - expected media files exist
     - no `ppt/media/*` entries are zero bytes
     - `Microsoft YaHei` appears in slide XML
     - expected Chinese title text appears in slide XML
     - count text boxes, shapes, and picture objects
   - Write `qa/visual-qa.txt` summarizing what is editable, what remains raster, and any caveats.
   - Keep `qa/paths.txt` and `qa/verify.json` beside the deck so the runtime, asset locations, and structural checks are always recoverable.

## Image Generation Prompt Templates

### Clean Background

```text
Use case: productivity-visual
Asset type: editable PowerPoint slide background
Primary request: create a clean no-text background matching the provided reference slide's dark navy futuristic technology style.
Scene/backdrop: full-bleed presentation background, deep midnight blue with subtle cyan glows, faint grid/particle wave in the upper right, delicate horizontal light traces near the bottom, and a slim cyan vertical accent line at the far left.
Composition/framing: leave the center and lower regions clean enough for editable PowerPoint text boxes and rounded panels to be placed on top.
Constraints: no readable text, no letters, no numbers, no logo, no watermark, no icons, no charts, no UI panels, no fake glyphs.
```

### Icon Sprite Sheet

```text
Use case: productivity-visual
Asset type: PowerPoint icon sprite sheet for cropping
Primary request: Create a 4 by 4 grid of premium enterprise AI workflow icons, each icon centered in its own invisible square cell with generous padding. No labels.
Style/medium: high-resolution glossy 3D plus clean vector-like technology icons, blue/cyan neon glow with subtle violet accents, suitable for a dark navy corporate AI presentation.
Background extraction requirement: place the icons on a perfectly flat solid #00ff00 chroma-key background for background removal. The background must be one uniform color with no shadows, gradients, texture, reflections, floor plane, or lighting variation.
Constraints: No readable text except exact "AI" on the AI cube icon only. Do not use #00ff00 anywhere in the icons. No logo, no watermark, no extra words, no numbers, no fake glyphs.
```

## Quality Bar

Before final response, confirm:

- The final `.pptx` path is provided.
- A preview PNG path is available and visually checked.
- `qa/paths.txt` includes the resolved runtime paths and output paths.
- Text is editable and uses Microsoft YaHei.
- Major layout shapes are editable PowerPoint objects.
- Icons are selected from the local asset cache first regardless of provider; newly generated transparent PNG image objects are used only when cached icons are unsuitable.
- Any SVG or black glyph icon selected from cache is converted/recolored into a task-local PNG before insertion when needed for artifact-tool compatibility or dark-slide contrast.
- Generated backgrounds, icons, and other reusable pictures are copied into the shared local asset cache.
- The background is raster and intentionally used only as an atmosphere layer.
- The final answer mentions any caveat, especially if the generated no-text background preserves style rather than exactly removing original foreground content.
