# Codex Task Prompts

## Invoke the skill explicitly

```text
Use $ai-visual-ppt-composer. 根据我给你的大纲，走“AI无字背景 + HTML/CSS/SVG精准排版 + PPTXGenJS可编辑重建”的路线，生成可编辑PPTX和预览PNG/HTML。所有正文、标题、图表标签必须是PPT原生可编辑文本；背景只允许无文字视觉氛围图。请先建立deck.json，再运行脚本输出pptx。
```

## When user already has background images

```text
Use $ai-visual-ppt-composer. 我已经有每页背景图，请不要把背景文字识别成PPT内容，只把这些图当作无字视觉背景使用。根据我的内容重新叠加可编辑标题、正文、图形和图表，输出pptx。
```

## When user provides a reference style image

```text
Use $ai-visual-ppt-composer. 参考这张图的视觉风格、构图逻辑、色彩和标题层级，但不要复制其中无关文字。请重建成可编辑PPT：背景可为图片，所有真实内容必须用PPT原生文字和形状。
```

## When user wants high-end beautification

```text
Use $ai-visual-ppt-composer. 不要套死板模板，不要只统一主色。请按每页内容重新设计视觉重心、层级、留白、标题效果和卡片结构。需要高级感，但文字准确和可编辑优先。
```
