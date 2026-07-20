# -*- coding: utf-8 -*-
"""编排器：意图路由到各专业 Agent。"""
from __future__ import annotations

import re

from a2a.client import A2AClient
from a2a.protocol import AgentMessage, AgentSkill
from agents.base import BaseAgent
from config import load_config


def route_intent(text: str) -> str:
    """返回 permission|knowledge|paper|coding。"""
    t = text.strip().lower()
    if re.match(r"^(grant|revoke|list|check)\b", t):
        return "permission"
    if re.search(r"(权限|授权|grant|revoke)", text, flags=re.I):
        return "permission"
    if re.match(r"^(paper|论文|arxiv|期刊|journal)[:：\s]", text, flags=re.I):
        return "paper"
    if re.search(r"(论文|arxiv|miccai|tmi|分割.*前沿|最新.*论文)", text, flags=re.I):
        return "paper"
    if re.match(r"^(ls|read|code|写代码|编程)\b", t) or re.search(
        r"(写代码|实现|refactor|codex|unet.*代码|训练脚本)", text, flags=re.I
    ):
        return "coding"
    return "knowledge"


class OrchestratorAgent(BaseAgent):
    name = "orchestrator"
    description = "医学图像分割课题组总控：路由权限/知识/论文/编程 Agent"
    skills = [
        AgentSkill("route", "按意图委派子 Agent"),
    ]

    def __init__(self):
        cfg = load_config()
        self.port = cfg["ports"]["orchestrator"]
        ports = cfg["ports"]
        self.clients = {
            "permission": A2AClient(f"http://127.0.0.1:{ports['permission']}"),
            "knowledge": A2AClient(f"http://127.0.0.1:{ports['knowledge']}"),
            "paper": A2AClient(f"http://127.0.0.1:{ports['paper']}"),
            "coding": A2AClient(f"http://127.0.0.1:{ports['coding']}"),
        }

    def handle(self, message: AgentMessage, metadata: dict) -> AgentMessage:
        text = message.text()
        # 显式指定：@permission / @knowledge / @paper / @coding
        m = re.match(r"^@(permission|knowledge|paper|coding)\s+([\s\S]+)$", text, flags=re.I)
        if m:
            target = m.group(1).lower()
            inner = AgentMessage.user_text(m.group(2), message.context_id)
        else:
            target = route_intent(text)
            inner = message

        try:
            reply = self.clients[target].send(inner, metadata=metadata)
        except Exception as e:
            return AgentMessage.agent_text(
                f"调用 {target} 失败: {e}\n请先运行 python run_agents.py",
                message.context_id,
            )
        # 标注路由
        body = f"[routed -> {target}]\n{reply.text()}"
        return AgentMessage.agent_text(body, message.context_id)
