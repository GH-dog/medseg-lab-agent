# -*- coding: utf-8 -*-
"""交互 CLI：对接编排器 A2A。"""
from __future__ import annotations

import argparse
import sys

from a2a.client import A2AClient
from a2a.protocol import AgentMessage
from config import load_config


HELP = """
命令提示：
  /user <name>     切换当前用户（默认 student_demo；老师用 teacher）
  /card            查看编排器 AgentCard
  /help            帮助
  /quit            退出

示例：
  U-Net 和 Transformer 分割有什么区别？
  论文: medical image segmentation Swin
  grant student_demo experiments/ rw
  @coding 在 tutorials/ 写一个最小 dice loss
"""


def main():
    parser = argparse.ArgumentParser(description="MedSeg Lab Agent CLI")
    parser.add_argument("--user", default="student_demo", help="当前用户名")
    parser.add_argument("--url", default="", help="编排器 URL")
    args = parser.parse_args()

    cfg = load_config()
    url = args.url or f"http://127.0.0.1:{cfg['ports']['orchestrator']}"
    client = A2AClient(url)
    user = args.user
    ctx = "cli-session"

    print("医学图像分割课题组 AI-Agent CLI")
    print(f"连接: {url}  用户: {user}")
    print(HELP)

    while True:
        try:
            line = input(f"[{user}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("/quit", "/exit", "quit", "exit"):
            break
        if line == "/help":
            print(HELP)
            continue
        if line.startswith("/user "):
            user = line.split(None, 1)[1].strip()
            print(f"当前用户: {user}")
            continue
        if line == "/card":
            try:
                print(client.get_agent_card())
            except Exception as e:
                print(f"失败: {e}\n请先 python run_agents.py")
            continue

        try:
            reply = client.send(
                AgentMessage.user_text(line, ctx),
                metadata={"user": user},
            )
            print(reply.text())
            print()
        except Exception as e:
            print(f"错误: {e}")
            print("请确认已启动: python run_agents.py")


if __name__ == "__main__":
    main()
