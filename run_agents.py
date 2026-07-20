# -*- coding: utf-8 -*-
"""一键拉起全部 A2A Agent。"""
from __future__ import annotations

import signal
import sys
import time

from agents.coding_agent import CodingAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.orchestrator import OrchestratorAgent
from agents.paper_agent import PaperAgent
from agents.permission_agent import PermissionAgent


def main():
    agents = [
        PermissionAgent(),
        KnowledgeAgent(),
        PaperAgent(),
        CodingAgent(),
        OrchestratorAgent(),
    ]
    servers = []
    for a in agents:
        srv = a.serve(background=True)
        servers.append(srv)
        print(f"[up] {a.name} http://127.0.0.1:{a.port}  card=/.well-known/agent-card.json")

    print("\n编排入口: http://127.0.0.1:8000")
    print("另开终端运行: python cli.py")
    print("Ctrl+C 退出\n")

    def _stop(*_):
        for s in servers:
            s.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
