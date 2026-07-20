# -*- coding: utf-8 -*-
"""A2A HTTP 服务：AgentCard + JSON-RPC message/send。"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import urlparse

from a2a.protocol import (
    MESSAGE_SEND,
    TASK_GET,
    AgentCard,
    AgentMessage,
    jsonrpc_err,
    jsonrpc_ok,
)

# Handler 工厂用
MessageHandler = Callable[[AgentMessage, dict], AgentMessage]


def make_handler(card: AgentCard, on_message: MessageHandler, tasks: dict):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # 安静一点，避免刷屏
            pass

        def _send(self, code: int, body: dict | list | bytes, content_type: str = "application/json"):
            raw = body if isinstance(body, (bytes, bytearray)) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/.well-known/agent-card.json", "/agent-card.json"):
                self._send(200, card.to_dict())
                return
            self._send(404, {"error": "not found"})

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                req = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._send(400, jsonrpc_err(None, -32700, "Parse error"))
                return

            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params") or {}

            if method == MESSAGE_SEND:
                msg = AgentMessage.from_dict(params.get("message") or {})
                # 透传元数据：user / 权限相关字段
                meta = params.get("metadata") or {}
                try:
                    reply = on_message(msg, meta)
                except Exception as e:
                    self._send(200, jsonrpc_err(req_id, -32000, str(e)))
                    return
                task_id = reply.message_id
                tasks[task_id] = reply.to_dict()
                self._send(200, jsonrpc_ok(req_id, reply.to_dict()))
                return

            if method == TASK_GET:
                tid = (params.get("id") or params.get("taskId") or "")
                if tid in tasks:
                    self._send(200, jsonrpc_ok(req_id, tasks[tid]))
                else:
                    self._send(200, jsonrpc_err(req_id, -32001, f"task not found: {tid}"))
                return

            self._send(200, jsonrpc_err(req_id, -32601, f"Method not found: {method}"))

    return Handler


class A2AServer:
    """线程化 HTTP A2A 服务。"""

    def __init__(self, card: AgentCard, on_message: MessageHandler, host: str = "127.0.0.1", port: int = 8000):
        self.card = card
        self.on_message = on_message
        self.host = host
        self.port = port
        self.tasks: dict = {}
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self, background: bool = True):
        handler = make_handler(self.card, self.on_message, self.tasks)
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        if background:
            self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
            self._thread.start()
        else:
            self._httpd.serve_forever()

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
