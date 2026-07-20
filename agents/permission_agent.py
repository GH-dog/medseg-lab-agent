# -*- coding: utf-8 -*-
"""权限 Agent：老师管理组内代码目录 ACL。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from a2a.protocol import AgentMessage, AgentSkill
from agents.base import BaseAgent
from config import ROOT, load_config

PERM_FILE = ROOT / "data" / "permissions.json"


def _load() -> dict:
    if not PERM_FILE.exists():
        return {"users": {}}
    return json.loads(PERM_FILE.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    PERM_FILE.parent.mkdir(parents=True, exist_ok=True)
    PERM_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def check_access(user: str, rel_path: str, need: str = "r") -> bool:
    """need: r 或 rw。teacher 全通；* 通配。"""
    data = _load()
    users = data.get("users") or {}
    u = users.get(user)
    if not u:
        return False
    if u.get("role") == "teacher":
        return True
    paths = u.get("paths") or {}
    rel = rel_path.replace("\\", "/").lstrip("/")
    best = None
    for prefix, mode in paths.items():
        p = prefix.replace("\\", "/")
        if p == "*" or rel == p.rstrip("/") or rel.startswith(p):
            best = mode
            if p == "*":
                break
    if best is None:
        return False
    if need == "r":
        return best in ("r", "rw")
    return best == "rw"


class PermissionAgent(BaseAgent):
    name = "permission-agent"
    description = "老师管理课题组代码目录读写权限（grant/revoke/list/check）"
    skills = [
        AgentSkill("grant", "授予用户路径权限"),
        AgentSkill("revoke", "撤销用户路径权限"),
        AgentSkill("list", "列出权限表"),
        AgentSkill("check", "检查用户对路径的权限"),
    ]

    def __init__(self):
        cfg = load_config()
        self.port = cfg["ports"]["permission"]

    def handle(self, message: AgentMessage, metadata: dict) -> AgentMessage:
        text = message.text().strip()
        actor = metadata.get("user") or "anonymous"
        data = _load()
        users = data.setdefault("users", {})

        # 命令解析
        m = re.match(
            r"^(grant|revoke|list|check)\b(.*)$",
            text,
            flags=re.I,
        )
        if not m:
            reply = (
                "用法：\n"
                "  grant <user> <path> <r|rw>\n"
                "  revoke <user> <path>\n"
                "  list\n"
                "  check <user> <path>\n"
                "仅 teacher 可 grant/revoke。"
            )
            return AgentMessage.agent_text(reply, message.context_id)

        cmd = m.group(1).lower()
        rest = (m.group(2) or "").strip()

        if cmd == "list":
            return AgentMessage.agent_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                message.context_id,
            )

        actor_info = users.get(actor) or {}
        is_teacher = actor_info.get("role") == "teacher"

        if cmd == "check":
            parts = rest.split()
            if len(parts) < 2:
                return AgentMessage.agent_text("用法: check <user> <path>", message.context_id)
            u, path = parts[0], parts[1]
            r_ok = check_access(u, path, "r")
            w_ok = check_access(u, path, "rw")
            return AgentMessage.agent_text(
                f"user={u} path={path} read={r_ok} write={w_ok}",
                message.context_id,
            )

        if not is_teacher:
            return AgentMessage.agent_text("拒绝：仅 teacher 可修改权限。", message.context_id)

        if cmd == "grant":
            parts = rest.split()
            if len(parts) < 3:
                return AgentMessage.agent_text("用法: grant <user> <path> <r|rw>", message.context_id)
            u, path, mode = parts[0], parts[1], parts[2].lower()
            if mode not in ("r", "rw"):
                return AgentMessage.agent_text("mode 必须是 r 或 rw", message.context_id)
            users.setdefault(u, {"role": "student", "paths": {}})
            users[u].setdefault("paths", {})[path] = mode
            _save(data)
            return AgentMessage.agent_text(f"已授权 {u} -> {path} ({mode})", message.context_id)

        if cmd == "revoke":
            parts = rest.split()
            if len(parts) < 2:
                return AgentMessage.agent_text("用法: revoke <user> <path>", message.context_id)
            u, path = parts[0], parts[1]
            if u in users and path in (users[u].get("paths") or {}):
                del users[u]["paths"][path]
                _save(data)
                return AgentMessage.agent_text(f"已撤销 {u} -> {path}", message.context_id)
            return AgentMessage.agent_text("未找到对应权限项", message.context_id)

        return AgentMessage.agent_text("未知命令", message.context_id)
