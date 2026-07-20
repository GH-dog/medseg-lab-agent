# -*- coding: utf-8 -*-
"""Agent 基类。"""
from __future__ import annotations

from a2a.protocol import AgentCard, AgentMessage, AgentSkill
from a2a.server import A2AServer


class BaseAgent:
    name: str = "base"
    description: str = ""
    port: int = 0
    skills: list[AgentSkill] = []

    def handle(self, message: AgentMessage, metadata: dict) -> AgentMessage:
        raise NotImplementedError

    def card(self, host: str = "127.0.0.1") -> AgentCard:
        return AgentCard(
            name=self.name,
            description=self.description,
            url=f"http://{host}:{self.port}",
            skills=self.skills,
        )

    def serve(self, host: str = "127.0.0.1", background: bool = True) -> A2AServer:
        server = A2AServer(self.card(host), self.handle, host=host, port=self.port)
        server.start(background=background)
        return server
