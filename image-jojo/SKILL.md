---
name: image-jojo
description: Generate images through the JOJO Code OpenAI-compatible image API. Use when the user asks to use image jojo, JOJO Code, or gpt-image-2 scene image generation, and provides or needs an image prompt, output size, and local output filename.
---

# Image Jojo

## Overview

Use JOJO Code's OpenAI-compatible API to generate a local image file from a text prompt. The default endpoint is `https://api2.jojocode.com/v1`, the default model is `gpt-image-2`, and the bundled script saves the generated image to disk before reporting the absolute path.

## Quick Start

Run the bundled script from this skill directory or pass its absolute path:

```powershell
python "C:\Users\w33938\.codex\skills\image-jojo\scripts\generate_image.py" `
  --prompt "A cinematic futuristic city at sunrise, ultra detailed" `
  --size "1024x1024" `
  --output "D:\path\to\city.png"
```

Always tell the user the saved absolute file path after generation.

## Inputs

- `--prompt`: Required image description. Preserve the user's wording unless they ask for prompt improvement.
- `--size`: Optional image size, default `1024x1024`. Pass user-provided sizes such as `1024x1024`, `1536x1024`, or `1024x1536`.
- `--output`: Required output file name or path. If the user gives a relative name, resolve it relative to the current workspace before running the script.
- `--model`: Optional override, default `gpt-image-2`.
- `--asset-type`: Optional cache category, `background`, `icon`, or `image`. Use `background` for PPT/background assets, `icon` for icons or icon sheets, and `image` for everything else. When set, the script also copies the image into `D:\文档\05-开发\02-AI工具\03-本地缓存库`.
- `--api-key`: Optional override. Prefer `JOJO_API_KEY` if the user wants to avoid putting keys on the command line.
- `--base-url`: Optional override, default `https://api2.jojocode.com/v1`.

## Workflow

1. Search the shared cache first with `C:\Users\w33938\.codex\skills\asset-cache\scripts\search_cache.py` using the intended subject and `--asset-type background`, `icon`, or `image`.
2. Reuse a suitable cached asset if one exists.
3. Collect or infer the prompt, size, and output filename.
4. Resolve the output path to an absolute local path and create parent directories if needed. Use `--asset-type background` for reusable backgrounds, `--asset-type icon` for reusable icons or icon sheets, and `--asset-type image` for all other pictures.
5. Run `scripts/generate_image.py`.
6. If the API returns `b64_json`, decode and save it. If it returns a URL, the script downloads and saves it.
7. Report the saved image path to the user.

## Defaults

The script includes the JOJO Code API key supplied by the user for this local skill. It can be overridden with the `JOJO_API_KEY` environment variable or `--api-key`.
