#!/usr/bin/env python3
"""Single-file, self-installing reverse agent for Linux."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


DEFAULT_CONTROLLER_HOST = "37iy356889.qicp.vip"
DEFAULT_CONTROLLER_PORT = 10856
SHARED_TOKEN = "0123456789abcdef0123456789abcdef"
INSTALL_DIR = Path("/opt/sqcsagent")
INSTALL_FILE = INSTALL_DIR / "sqcsagent.py"
CONFIG_FILE = Path("/etc/sqcsagent.json")
SERVICE_FILE = Path("/etc/systemd/system/sqcsagent.service")
SERVICE_NAME = "sqcsagent.service"
MAX_CONTENT_BYTES = 10 * 1024 * 1024


def send_json(sock_file: Any, payload: dict[str, Any]) -> None:
    sock_file.write(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")
    sock_file.flush()


def recv_json(sock_file: Any) -> dict[str, Any] | None:
    line = sock_file.readline()
    return json.loads(line.decode("utf-8")) if line else None


def run_command(payload: dict[str, Any]) -> dict[str, Any]:
    command = str(payload.get("command", "")).strip()
    if not command:
        return {"ok": False, "error": "empty command"}
    timeout = max(1, min(int(payload.get("timeout", 30)), 300))
    started = time.time()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(payload.get("cwd", "/tmp")),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            executable="/bin/bash",
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "elapsed_ms": int((time.time() - started) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": "command timed out",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def read_file(payload: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(payload.get("path", ""))).expanduser()
    max_bytes = max(1, min(int(payload.get("max_bytes", 1024 * 1024)), MAX_CONTENT_BYTES))
    with path.open("rb") as fh:
        data = fh.read(max_bytes)
    return {
        "ok": True,
        "path": str(path),
        "encoding": "base64",
        "content": base64.b64encode(data).decode("ascii"),
        "truncated": path.stat().st_size > len(data),
    }


def write_file(payload: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(payload.get("path", ""))).expanduser()
    content = payload.get("content", "")
    if payload.get("encoding", "text") == "base64":
        data = base64.b64decode(content)
    else:
        data = str(content).encode("utf-8")
    if len(data) > MAX_CONTENT_BYTES:
        return {"ok": False, "error": "content too large"}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab" if payload.get("mode") == "append" else "wb") as fh:
        fh.write(data)
    return {"ok": True, "path": str(path), "bytes": len(data)}


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    action = request.get("action")
    payload = request.get("payload", {})
    try:
        if action == "exec":
            result = run_command(payload)
        elif action == "read":
            result = read_file(payload)
        elif action == "write":
            result = write_file(payload)
        elif action == "ping":
            result = {"ok": True, "time": int(time.time())}
        else:
            result = {"ok": False, "error": f"unknown action: {action}"}
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    return {"id": request.get("id"), "result": result}


def connect_loop(config: dict[str, Any]) -> None:
    host = str(config["host"])
    port = int(config["port"])
    token = str(config["token"])
    name = str(config.get("name") or socket.gethostname())
    retry_seconds = max(1, int(config.get("retry_seconds", 5)))
    while True:
        try:
            with socket.create_connection((host, port), timeout=10) as sock:
                sock.settimeout(None)
                sock_file = sock.makefile("rwb")
                send_json(
                    sock_file,
                    {"type": "hello", "token": token, "name": name, "pid": os.getpid()},
                )
                hello = recv_json(sock_file)
                if not hello or not hello.get("ok"):
                    raise ConnectionError("controller rejected authentication")
                print(f"connected to {host}:{port} as {name}", flush=True)
                while True:
                    request = recv_json(sock_file)
                    if request is None:
                        break
                    send_json(sock_file, handle_request(request))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"connection lost: {exc}; retry in {retry_seconds}s", flush=True)
        time.sleep(retry_seconds)


def service_unit() -> str:
    return f"""[Unit]
Description=SQCS Remote Server Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 {INSTALL_FILE.as_posix()} run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


def require_root() -> None:
    if os.name != "posix" or os.geteuid() != 0:
        raise PermissionError("install/uninstall must be run with sudo on Linux")


def install(args: argparse.Namespace) -> int:
    config = {
        "host": args.host,
        "port": args.port,
        "token": SHARED_TOKEN,
        "name": args.name or socket.gethostname(),
        "retry_seconds": 5,
    }
    if args.dry_run:
        print(json.dumps({**config, "token": "***"}, indent=2))
        print(service_unit())
        return 0

    require_root()
    source = Path(__file__).resolve()
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, INSTALL_FILE)
    INSTALL_FILE.chmod(0o755)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    CONFIG_FILE.chmod(0o600)
    SERVICE_FILE.write_text(service_unit(), encoding="utf-8")
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", SERVICE_NAME], check=True)
    subprocess.run(["systemctl", "restart", SERVICE_NAME], check=True)
    print(f"installed and started: {SERVICE_NAME}")
    print(f"controller: {args.host}:{args.port}; agent name: {config['name']}")
    print(f"status: sudo python3 {INSTALL_FILE} status")
    return 0


def load_config() -> dict[str, Any]:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if len(str(config.get("token", ""))) < 16:
        raise ValueError(f"invalid token in {CONFIG_FILE}")
    return config


def uninstall() -> int:
    require_root()
    subprocess.run(["systemctl", "disable", "--now", SERVICE_NAME], check=False)
    SERVICE_FILE.unlink(missing_ok=True)
    CONFIG_FILE.unlink(missing_ok=True)
    INSTALL_FILE.unlink(missing_ok=True)
    try:
        INSTALL_DIR.rmdir()
    except OSError:
        pass
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    print("codex-agent uninstalled")
    return 0


def systemctl_command(*command: str) -> int:
    return subprocess.run([*command], check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Single-file Codex Linux server agent")
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="install and start as a systemd service")
    p_install.add_argument("host", nargs="?", default=DEFAULT_CONTROLLER_HOST)
    p_install.add_argument("port", nargs="?", type=int, default=DEFAULT_CONTROLLER_PORT)
    p_install.add_argument("--name", default="")
    p_install.add_argument("--dry-run", action="store_true")
    sub.add_parser("run", help="run using the installed config")
    sub.add_parser("status", help="show service status")
    sub.add_parser("logs", help="show recent service logs")
    sub.add_parser("uninstall", help="stop and remove the service")
    args = parser.parse_args()

    if args.command == "install":
        return install(args)
    if args.command == "run":
        connect_loop(load_config())
        return 0
    if args.command == "status":
        return systemctl_command("systemctl", "status", SERVICE_NAME, "--no-pager")
    if args.command == "logs":
        return systemctl_command("journalctl", "-u", SERVICE_NAME, "-n", "100", "--no-pager")
    if args.command == "uninstall":
        return uninstall()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
