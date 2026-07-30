#!/usr/bin/env python3
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = "https://api.0029.org"
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "1024x1024"
FALLBACK_API_KEY = "sk-26d6edd6ef7e05ce9647fb3635dd9d0f7f6d1cf3be186bfa4b4ce772e975a73c"
ASSET_CACHE_SCRIPT = Path(r"C:\Users\w33938\.codex\skills\asset-cache\scripts\cache_asset.py")


def post_json(url: str, api_key: str, payload: dict, timeout: int) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a PNG via the image-yq API.")
    parser.add_argument("--prompt", required=True, help="Image prompt.")
    parser.add_argument("--output", default="image-yq-output.png", help="Output PNG path.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Image model.")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="Requested image size.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL.")
    parser.add_argument("--api-key", default=os.environ.get("IMAGE_YQ_API_KEY") or FALLBACK_API_KEY, help=argparse.SUPPRESS)
    parser.add_argument("--timeout", type=int, default=180, help="Request timeout in seconds.")
    parser.add_argument("--asset-type", choices=["background", "icon", "image"], help="Also copy the output into the shared asset cache.")
    args = parser.parse_args()

    endpoint = args.base_url.rstrip("/") + "/v1/images/generations"
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
        "n": 1,
    }

    try:
        result = post_json(endpoint, args.api_key, payload, args.timeout)
        item = (result.get("data") or [{}])[0]
        b64_png = item.get("b64_json")
        if not b64_png:
            raise RuntimeError("Response did not include data[0].b64_json")

        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(b64_png))
        cached_path = None
        if args.asset_type:
            import subprocess

            cache_cmd = [
                sys.executable,
                str(ASSET_CACHE_SCRIPT),
                "--source",
                str(output),
                "--asset-type",
                args.asset_type,
                "--provider",
                "image-yq",
                "--prompt",
                args.prompt,
                "--model",
                result.get("model") or args.model,
            ]
            cache_result = subprocess.run(cache_cmd, check=True, capture_output=True, text=True, encoding="utf-8")
            cached_path = json.loads(cache_result.stdout)["cached_path"]

        print(json.dumps({
            "ok": True,
            "output": str(output),
            "cached_path": cached_path,
            "requested_model": args.model,
            "response_model": result.get("model"),
            "size": result.get("size"),
            "output_format": result.get("output_format"),
            "bytes": output.stat().st_size,
            "revised_prompt": item.get("revised_prompt"),
            "usage_total_tokens": (result.get("usage") or {}).get("total_tokens"),
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
