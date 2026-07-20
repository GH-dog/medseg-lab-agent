# -*- coding: utf-8 -*-
"""A2A HTTP 客户端。"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from a2a.protocol import MESSAGE_SEND, AgentMessage


class A2AClient:
    def __init__(self, base_url: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_agent_card(self) -> dict:
        return self._get("/.well-known/agent-card.json")

    def send(self, message: AgentMessage, metadata: dict | None = None) -> AgentMessage:
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": MESSAGE_SEND,
            "params": {
                "message": message.to_dict(),
                "metadata": metadata or {},
            },
        }
        resp = self._post("/", payload)
        if "error" in resp:
            raise RuntimeError(resp["error"].get("message", str(resp["error"])))
        return AgentMessage.from_dict(resp["result"])

    def send_text(self, text: str, context_id: str = "", metadata: dict | None = None) -> str:
        reply = self.send(AgentMessage.user_text(text, context_id), metadata=metadata)
        return reply.text()

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(self.base_url + path, method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _post(self, path: str, body: dict) -> dict:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {raw}") from e
