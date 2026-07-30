#!/usr/bin/env python3
"""Self-starting local controller client for the sqcsagent skill."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from settings import AGENT_PORT, API_HOST, API_PORT, SHARED_TOKEN


SCRIPT_DIR = Path(__file__).resolve().parent
STATE_DIR = Path.home() / ".sqcsagent"
API_URL = f"http://{API_HOST}:{API_PORT}"


def request(method: str, path: str, payload: dict | None = None, timeout: int = 320) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        API_URL + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {SHARED_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"ok": False, "error": body}
    except URLError as exc:
        return {"ok": False, "error": f"controller unavailable: {exc}"}


def controller_ready() -> bool:
    return bool(request("GET", "/agents", timeout=2).get("ok"))


def start_controller() -> bool:
    if controller_ready():
        return True
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    log = (STATE_DIR / "controller.log").open("ab")
    command = [
        sys.executable,
        str(SCRIPT_DIR / "controller.py"),
        "--host",
        "0.0.0.0",
        "--port",
        str(AGENT_PORT),
        "--api-host",
        API_HOST,
        "--api-port",
        str(API_PORT),
        "--no-interactive",
    ]
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": log, "cwd": str(SCRIPT_DIR)}
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(command, **kwargs)
    for _ in range(30):
        time.sleep(0.2)
        if controller_ready():
            return True
    return False


def print_result(result: dict) -> int:
    if "stdout" in result:
        print(result["stdout"], end="")
    if result.get("stderr"):
        print(result["stderr"], end="", file=sys.stderr)
    if "stdout" not in result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result.get("returncode", 0 if result.get("ok") else 1))


def main() -> int:
    parser = argparse.ArgumentParser(description="Control Linux servers through sqcsagent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("agents")

    p_exec = sub.add_parser("exec")
    p_exec.add_argument("shell_command")
    p_exec.add_argument("--agent", default="")
    p_exec.add_argument("--cwd", default="/tmp")
    p_exec.add_argument("--timeout", type=int, default=60)

    p_read = sub.add_parser("read")
    p_read.add_argument("path")
    p_read.add_argument("--agent", default="")
    p_read.add_argument("--max-bytes", type=int, default=1024 * 1024)

    p_write = sub.add_parser("write")
    p_write.add_argument("path")
    p_write.add_argument("content")
    p_write.add_argument("--agent", default="")
    p_write.add_argument("--append", action="store_true")

    p_upload = sub.add_parser("upload")
    p_upload.add_argument("local_path")
    p_upload.add_argument("remote_path")
    p_upload.add_argument("--agent", default="")
    args = parser.parse_args()

    if not start_controller():
        print(f"failed to start controller; see {STATE_DIR / 'controller.log'}", file=sys.stderr)
        return 1

    if args.command == "agents":
        result = request("GET", "/agents")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    if args.command == "exec":
        result = request(
            "POST",
            "/exec",
            {
                "agent": args.agent or None,
                "command": args.shell_command,
                "cwd": args.cwd,
                "timeout": args.timeout,
            },
        )
        return print_result(result)
    if args.command == "read":
        query = urlencode({"agent": args.agent, "path": args.path, "max_bytes": args.max_bytes})
        result = request("GET", f"/read?{query}")
        if result.get("ok"):
            sys.stdout.buffer.write(base64.b64decode(result["content"]))
            return 0
        return print_result(result)
    if args.command == "write":
        result = request(
            "POST",
            "/write",
            {
                "agent": args.agent or None,
                "path": args.path,
                "content": args.content,
                "mode": "append" if args.append else "write",
            },
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    if args.command == "upload":
        data = Path(args.local_path).read_bytes()
        if len(data) > 10 * 1024 * 1024:
            print("upload is limited to 10 MiB", file=sys.stderr)
            return 1
        result = request(
            "POST",
            "/write",
            {
                "agent": args.agent or None,
                "path": args.remote_path,
                "content": base64.b64encode(data).decode("ascii"),
                "encoding": "base64",
                "mode": "write",
            },
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
