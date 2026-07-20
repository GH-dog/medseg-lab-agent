# -*- coding: utf-8 -*-
"""A2A 协议最小模型：对齐 a2a-cpp-sdk 的 message/send 与 AgentCard。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


# 与 C++ A2AMethods 对齐
MESSAGE_SEND = "message/send"
MESSAGE_STREAM = "message/stream"
TASK_GET = "tasks/get"
TASK_CANCEL = "tasks/cancel"


@dataclass
class TextPart:
    text: str
    kind: str = "text"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "text": self.text}


@dataclass
class AgentMessage:
    role: str
    parts: list[TextPart]
    context_id: str = ""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def text(self) -> str:
        return "\n".join(p.text for p in self.parts if p.kind == "text")

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "contextId": self.context_id,
            "messageId": self.message_id,
            "parts": [p.to_dict() for p in self.parts],
        }

    @staticmethod
    def from_dict(d: dict) -> "AgentMessage":
        parts = []
        for p in d.get("parts") or []:
            if p.get("kind", "text") == "text":
                parts.append(TextPart(text=p.get("text", "")))
        return AgentMessage(
            role=d.get("role", "user"),
            parts=parts,
            context_id=d.get("contextId", ""),
            message_id=d.get("messageId", str(uuid.uuid4())),
        )

    @staticmethod
    def user_text(text: str, context_id: str = "") -> "AgentMessage":
        return AgentMessage(role="user", parts=[TextPart(text)], context_id=context_id)

    @staticmethod
    def agent_text(text: str, context_id: str = "") -> "AgentMessage":
        return AgentMessage(role="agent", parts=[TextPart(text)], context_id=context_id)


@dataclass
class AgentSkill:
    name: str
    description: str
    id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id or self.name,
            "name": self.name,
            "description": self.description,
        }


@dataclass
class AgentCard:
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    skills: list[AgentSkill] = field(default_factory=list)
    capabilities: dict = field(default_factory=lambda: {"streaming": False})

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": self.capabilities,
            "skills": [s.to_dict() for s in self.skills],
        }


def jsonrpc_ok(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def jsonrpc_err(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
