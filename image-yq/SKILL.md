---
name: image-yq
description: Generate or test PNG images through the YQ OpenAI-compatible image API at api.0029.org. Use when the user asks to use image-yq, YQ image generation, api.0029.org, 0029 image API, gpt-image-2 through this key, or wants a local image file generated from a prompt with this provider.
---

# Image YQ

## Overview

Use this skill to generate PNG images through the YQ OpenAI-compatible image endpoint. Prefer the bundled script so requests are consistent, base64 output is decoded directly, and large raw responses are not printed.

## Defaults

- Base URL: `https://api.0029.org`
- Endpoint: `/v1/images/generations`
- Default model: `gpt-image-2`
- Observed response model: `gpt-image-2-codex`
- Default size: `1024x1024`
- Output format: PNG
- API key: `sk-26d6edd6ef7e05ce9647fb3635dd9d0f7f6d1cf3be186bfa4b4ce772e975a73c`

The key was provided in chat. Do not print it in final answers or logs. If the user plans to share outputs or repo contents, recommend rotating the key and moving it to an environment variable.

## Quick Start

Run:

```powershell
python "C:\Users\w33938\.codex\skills\image-yq\scripts\generate_image.py" `
  --prompt "A clean product-style image of a glass teacup on a white background" `
  --output "C:\tmp\image-yq-test.png"
```

The script prints compact JSON with success status, model, output path, revised prompt, and token usage.

## Parameters

- `--prompt`: Required text prompt.
- `--output`: Optional PNG path. Defaults to `image-yq-output.png` in the current directory.
- `--model`: Optional model. Defaults to `gpt-image-2`.
- `--size`: Optional size. Defaults to `1024x1024`.
- `--base-url`: Optional API base. Defaults to `https://api.0029.org`.
- `--asset-type`: Optional cache category, `background`, `icon`, or `image`. Use `background` for PPT/background assets, `icon` for icons or icon sheets, and `image` for everything else. When set, the script also copies the image into `D:\文档\05-开发\02-AI工具\03-本地缓存库`.
- `--api-key`: Optional key override. If omitted, the script uses `IMAGE_YQ_API_KEY`, then the bundled fallback key.

## Workflow

1. Search the shared cache first with `C:\Users\w33938\.codex\skills\asset-cache\scripts\search_cache.py` using the intended subject and `--asset-type background`, `icon`, or `image`.
2. Reuse a suitable cached asset if one exists.
3. Clarify the desired image only if the prompt is too ambiguous to produce a useful result.
4. Run the bundled script with a concise, visual prompt and a clear local output path. Use `--asset-type background` for reusable backgrounds, `--asset-type icon` for reusable icons or icon sheets, and `--asset-type image` for all other pictures.
3. Inspect the resulting file when quality matters, using local image viewing tools if available.
4. In the final response, provide the saved file path and summarize key generation details. Do not include raw base64.

## Notes

- The provider returns OpenAI-compatible JSON with `data[0].b64_json`.
- The service may map requested `gpt-image-2` to response model `gpt-image-2-codex`; this is expected.
- Avoid logging request headers or the API key.
