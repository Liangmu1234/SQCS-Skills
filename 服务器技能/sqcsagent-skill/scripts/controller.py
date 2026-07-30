#!/usr/bin/env python3
"""
Controller for reverse_agent.py.

Run this on your computer, then run reverse_agent.py on the Linux server.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import queue
import socket
import socketserver
import sys
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    from settings import AGENT_PORT, API_PORT, SHARED_TOKEN
except ImportError:
    AGENT_PORT = 8766
    API_PORT = 8767
    SHARED_TOKEN = "0123456789abcdef0123456789abcdef"

AGENTS: dict[str, "AgentSession"] = {}
AGENTS_LOCK = threading.Lock()
TOKEN = ""
LOCAL_API_TOKEN = ""


def send_json(sock_file: Any, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sock_file.write(data + b"\n")
    sock_file.flush()


def recv_json(sock_file: Any) -> dict[str, Any] | None:
    line = sock_file.readline()
    if not line:
        return None
    return json.loads(line.decode("utf-8"))


@dataclass
class AgentSession:
    name: str
    address: str
    sock_file: Any
    lock: threading.Lock
    replies: dict[str, queue.Queue]
    connected_at: float

    def request(self, action: str, payload: dict[str, Any], timeout: int = 310) -> dict[str, Any]:
        req_id = f"{time.time_ns()}"
        reply_queue: queue.Queue = queue.Queue(maxsize=1)
        self.replies[req_id] = reply_queue
        with self.lock:
            send_json(self.sock_file, {"id": req_id, "action": action, "payload": payload})
        try:
            return reply_queue.get(timeout=timeout)
        finally:
            self.replies.pop(req_id, None)


class AgentTCPHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        sock_file = self.request.makefile("rwb")
        hello = recv_json(sock_file)
        if not hello or hello.get("type") != "hello" or hello.get("token") != TOKEN:
            send_json(sock_file, {"ok": False, "error": "unauthorized"})
            return

        name = str(hello.get("name") or self.client_address[0])
        session = AgentSession(
            name=name,
            address=f"{self.client_address[0]}:{self.client_address[1]}",
            sock_file=sock_file,
            lock=threading.Lock(),
            replies={},
            connected_at=time.time(),
        )
        with AGENTS_LOCK:
            AGENTS[name] = session
        send_json(sock_file, {"ok": True})
        print(f"\nagent connected: {name} from {session.address}")
        try:
            while True:
                try:
                    message = recv_json(sock_file)
                except (ConnectionError, OSError):
                    break
                if message is None:
                    break
                req_id = str(message.get("id"))
                reply_queue = session.replies.get(req_id)
                if reply_queue:
                    reply_queue.put(message.get("result", {}))
        finally:
            with AGENTS_LOCK:
                if AGENTS.get(name) is session:
                    AGENTS.pop(name, None)
            print(f"\nagent disconnected: {name}")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any] | None:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        json_response(handler, 400, {"ok": False, "error": f"invalid json: {exc}"})
        return None


def local_api_authorized(handler: BaseHTTPRequestHandler) -> bool:
    if not LOCAL_API_TOKEN:
        return True
    return handler.headers.get("Authorization", "") == f"Bearer {LOCAL_API_TOKEN}"


class LocalAPIHandler(BaseHTTPRequestHandler):
    server_version = "CodexAgentLocalAPI/0.1"

    def do_GET(self) -> None:
        if not local_api_authorized(self):
            json_response(self, 401, {"ok": False, "error": "unauthorized"})
            return
        parsed = urlparse(self.path)
        if parsed.path == "/agents":
            with AGENTS_LOCK:
                agents = [
                    {
                        "name": name,
                        "address": session.address,
                        "connected_seconds": int(time.time() - session.connected_at),
                    }
                    for name, session in AGENTS.items()
                ]
            json_response(self, 200, {"ok": True, "agents": agents})
            return
        if parsed.path == "/read":
            query = parse_qs(parsed.query)
            agent = get_agent(query.get("agent", [None])[0])
            if not agent:
                json_response(self, 404, {"ok": False, "error": "no agent selected or connected"})
                return
            result = agent.request(
                "read",
                {
                    "path": query.get("path", [""])[0],
                    "max_bytes": int(query.get("max_bytes", [1024 * 1024])[0]),
                },
            )
            json_response(self, 200, result)
            return
        json_response(self, 404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if not local_api_authorized(self):
            json_response(self, 401, {"ok": False, "error": "unauthorized"})
            return
        payload = read_json(self)
        if payload is None:
            return
        agent = get_agent(payload.get("agent"))
        if not agent:
            json_response(self, 404, {"ok": False, "error": "no agent selected or connected"})
            return
        if self.path == "/exec":
            result = agent.request(
                "exec",
                {
                    "command": payload.get("command", ""),
                    "cwd": payload.get("cwd", "/tmp"),
                    "timeout": int(payload.get("timeout", 60)),
                },
            )
            json_response(self, 200, result)
        elif self.path == "/write":
            result = agent.request(
                "write",
                {
                    "path": payload.get("path", ""),
                    "content": payload.get("content", ""),
                    "encoding": payload.get("encoding", "text"),
                    "mode": payload.get("mode", "write"),
                },
            )
            json_response(self, 200, result)
        else:
            json_response(self, 404, {"ok": False, "error": "not found"})

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def get_agent(name: str | None = None) -> AgentSession | None:
    with AGENTS_LOCK:
        if name:
            return AGENTS.get(name)
        if len(AGENTS) == 1:
            return next(iter(AGENTS.values()))
        return None


def print_result(result: dict[str, Any]) -> int:
    if "stdout" in result:
        print(result["stdout"], end="")
    if result.get("stderr"):
        print(result["stderr"], end="", file=sys.stderr)
    if "stdout" not in result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result.get("returncode", 0 if result.get("ok") else 1))


def interactive_loop() -> None:
    print("commands: agents | use <name> | exec <cmd> | read <path> | write <path> <text> | quit")
    selected: str | None = None
    while True:
        try:
            line = input("codex-agent> ").strip()
        except EOFError:
            return
        if not line:
            continue
        if line in {"quit", "exit"}:
            return
        if line == "agents":
            with AGENTS_LOCK:
                for name, session in AGENTS.items():
                    age = int(time.time() - session.connected_at)
                    marker = "*" if name == selected else " "
                    print(f"{marker} {name} {session.address} connected {age}s")
            continue
        if line.startswith("use "):
            selected = line[4:].strip()
            print(f"selected {selected}")
            continue
        agent = get_agent(selected)
        if not agent:
            print("no agent selected or connected")
            continue
        if line.startswith("exec "):
            result = agent.request("exec", {"command": line[5:], "cwd": "/tmp", "timeout": 60})
            print_result(result)
        elif line.startswith("read "):
            result = agent.request("read", {"path": line[5:].strip()})
            if result.get("ok"):
                sys.stdout.buffer.write(base64.b64decode(result["content"]))
                print()
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
        elif line.startswith("write "):
            parts = line.split(" ", 2)
            if len(parts) < 3:
                print("usage: write <path> <text>")
                continue
            path, text = parts[1], parts[2]
            result = agent.request("write", {"path": path, "content": text})
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            result = agent.request("exec", {"command": line, "cwd": "/tmp", "timeout": 60})
            print_result(result)


def run_server(host: str, port: int) -> ThreadedTCPServer:
    server = ThreadedTCPServer((host, port), AgentTCPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def run_local_api(host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), LocalAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Reverse agent controller")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=AGENT_PORT)
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=API_PORT)
    parser.add_argument("--token", default=os.environ.get("CODEX_AGENT_TOKEN", SHARED_TOKEN))
    parser.add_argument("--local-api-token", default=os.environ.get("CODEX_AGENT_LOCAL_TOKEN", SHARED_TOKEN))
    parser.add_argument("--no-interactive", action="store_true")
    args = parser.parse_args()

    if len(args.token) < 16:
        print("Set CODEX_AGENT_TOKEN or pass --token, at least 16 characters.", file=sys.stderr)
        return 2

    global TOKEN
    TOKEN = args.token
    global LOCAL_API_TOKEN
    LOCAL_API_TOKEN = args.local_api_token or args.token
    server = run_server(args.host, args.port)
    api_server = run_local_api(args.api_host, args.api_port)
    bound_host, bound_port = server.server_address
    print(f"controller listening on {bound_host}:{bound_port}")
    print(f"local api listening on {api_server.server_address[0]}:{api_server.server_address[1]}")
    try:
        if args.no_interactive:
            while True:
                time.sleep(3600)
        else:
            interactive_loop()
    finally:
        api_server.shutdown()
        api_server.server_close()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
