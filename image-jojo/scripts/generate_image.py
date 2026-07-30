#!/usr/bin/env python3
"""Generate an image with the JOJO Code OpenAI-compatible image API."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError


DEFAULT_BASE_URL = "https://api2.jojocode.com/v1"
DEFAULT_API_KEY = "sk-TV2tGWvH0fVO18lRxbFVPolX10dyYC5LlMCKL9UnOJj9xc1T"
DEFAULT_MODEL = "gpt-image-2"
ASSET_CACHE_SCRIPT = Path(r"C:\Users\w33938\.codex\skills\asset-cache\scripts\cache_asset.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an image via the JOJO Code OpenAI-compatible API."
    )
    parser.add_argument("--prompt", required=True, help="Image description prompt.")
    parser.add_argument(
        "--size",
        default="1024x1024",
        help="Image size, for example 1024x1024, 1536x1024, or 1024x1536.",
    )
    parser.add_argument("--output", required=True, help="Output image file path.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Image model name.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("JOJO_BASE_URL", DEFAULT_BASE_URL),
        help="OpenAI-compatible API base URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("JOJO_API_KEY", DEFAULT_API_KEY),
        help="API key. Defaults to JOJO_API_KEY or the local skill default.",
    )
    parser.add_argument(
        "--asset-type",
        choices=["background", "icon", "image"],
        help="Also copy the output into the shared asset cache.",
    )
    return parser.parse_args()


def post_json(url: str, api_key: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"API request failed: HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise SystemExit(f"API request failed: {exc.reason}") from exc


def download_url(url: str) -> bytes:
    try:
        with request.urlopen(url, timeout=180) as resp:
            return resp.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Image download failed: HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise SystemExit(f"Image download failed: {exc.reason}") from exc


def image_bytes_from_response(response: dict) -> bytes:
    data = response.get("data")
    if not isinstance(data, list) or not data:
        raise SystemExit(f"Unexpected image response: {json.dumps(response, ensure_ascii=False)}")

    first = data[0]
    if not isinstance(first, dict):
        raise SystemExit(f"Unexpected image item: {json.dumps(first, ensure_ascii=False)}")

    b64_json = first.get("b64_json")
    if isinstance(b64_json, str) and b64_json:
        return base64.b64decode(b64_json)

    url = first.get("url")
    if isinstance(url, str) and url:
        return download_url(url)

    raise SystemExit(f"No b64_json or url found in image item: {json.dumps(first, ensure_ascii=False)}")


def main() -> None:
    args = parse_args()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    endpoint = args.base_url.rstrip("/") + "/images/generations"
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
        "n": 1,
        "response_format": "b64_json",
    }

    response = post_json(endpoint, args.api_key, payload)
    output.write_bytes(image_bytes_from_response(response))
    if args.asset_type:
        import subprocess
        import sys

        cache_result = subprocess.run(
            [
                sys.executable,
                str(ASSET_CACHE_SCRIPT),
                "--source",
                str(output),
                "--asset-type",
                args.asset_type,
                "--provider",
                "image-jojo",
                "--prompt",
                args.prompt,
                "--model",
                args.model,
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print(cache_result.stdout)
    else:
        print(str(output))


if __name__ == "__main__":
    main()
