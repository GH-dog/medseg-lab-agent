# -*- coding: utf-8 -*-
"""Codex 风格 AI-Coding Agent：在 ACL 允许路径下读写代码。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from a2a.protocol import AgentMessage, AgentSkill
from agents.base import BaseAgent
from agents.llm import chat
from agents.permission_agent import check_access
from config import load_config, workspace_root

CODING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "列出工作区相对路径下的文件",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取工作区文件",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入工作区文件（覆盖）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
]


class CodingAgent(BaseAgent):
    name = "coding-agent"
    description = "基于 Codex 兼容模型的组内代码辅助（受权限控制）"
    skills = [
        AgentSkill("code", "读写并生成代码"),
    ]

    def __init__(self):
        cfg = load_config()
        self.port = cfg["ports"]["coding"]
        self.cfg = cfg
        self.root = workspace_root(cfg)

    def _resolve(self, rel: str) -> Path:
        rel = rel.replace("\\", "/").lstrip("/")
        path = (self.root / rel).resolve()
        if not str(path).startswith(str(self.root.resolve())):
            raise PermissionError("路径越界")
        return path

    def _tool(self, name: str, args: dict, user: str) -> str:
        rel = (args.get("path") or ".").replace("\\", "/")
        if name == "list_dir":
            # ponytail: 列出目录不强制 ACL，读写才校验
            p = self._resolve("." if rel in (".", "") else rel)
            if not p.exists():
                return f"不存在: {rel}"
            if p.is_file():
                return rel
            names = sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir())
            return "\n".join(names) or "(空目录)"

        if name == "read_file":
            if not check_access(user, rel, "r"):
                return f"拒绝读取：用户 {user} 对 {rel} 无读权限"
            p = self._resolve(rel)
            if not p.exists():
                return f"文件不存在: {rel}"
            return p.read_text(encoding="utf-8")

        if name == "write_file":
            if not check_access(user, rel, "rw"):
                return f"拒绝写入：用户 {user} 对 {rel} 无写权限（联系老师 grant）"
            p = self._resolve(rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            content = args.get("content", "")
            p.write_text(content, encoding="utf-8")
            return f"已写入 {rel} ({len(content)} chars)"

        return f"未知工具: {name}"

    def handle(self, message: AgentMessage, metadata: dict) -> AgentMessage:
        user = metadata.get("user") or "student_demo"
        q = message.text().strip()
        cfg = self.cfg
        model = cfg["llm"].get("coding_model") or cfg["llm"]["model"]

        # 快捷命令：无需 LLM
        m = re.match(r"^read\s+(\S+)$", q, flags=re.I)
        if m:
            return AgentMessage.agent_text(self._tool("read_file", {"path": m.group(1)}, user), message.context_id)
        m = re.match(r"^ls(?:\s+(\S+))?$", q, flags=re.I)
        if m:
            return AgentMessage.agent_text(self._tool("list_dir", {"path": m.group(1) or "."}, user), message.context_id)

        system = (
            "你是课题组 Codex 编程助手，工作区根目录为 workspace/。"
            "可用工具 list_dir/read_file/write_file。写文件前确认路径合理。"
            "医学图像分割相关代码优先清晰可运行。用中文说明改动。"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": q},
        ]

        # 最多两轮工具
        final_text = ""
        for _ in range(3):
            out = chat(messages, model=model, tools=CODING_TOOLS)
            if not out["tool_calls"]:
                final_text = out["content"] or "(空)"
                break
            # assistant tool_calls
            messages.append(
                {
                    "role": "assistant",
                    "content": out["content"] or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]},
                        }
                        for tc in out["tool_calls"]
                    ],
                }
            )
            for tc in out["tool_calls"]:
                try:
                    args = json.loads(tc["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self._tool(tc["name"], args, user)
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
        else:
            final_text = out.get("content") or "工具调用结束"

        if final_text.startswith("[未配置"):
            final_text += (
                "\n\n可用本地命令：ls [path] / read <path>\n"
                "写入需配置 LLM_API_KEY，并由老师授予 rw 权限。"
            )
        return AgentMessage.agent_text(final_text, message.context_id)
