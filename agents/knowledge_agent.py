# -*- coding: utf-8 -*-
"""知识问答 Agent：RAG + 联网搜索 function-call。"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from a2a.protocol import AgentMessage, AgentSkill
from agents.base import BaseAgent
from agents.llm import chat
from config import load_config
from knowledge.rag import MedSegRAG

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "联网搜索医学图像分割相关资料",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
            },
            "required": ["query"],
        },
    },
}


def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo HTML 轻量搜索（ponytail: 无额外 SDK）。"""
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MedSegLabAgent/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"搜索失败: {e}"

    # 粗提取结果标题与链接
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, flags=re.S)
    links = re.findall(r'class="result__a"[^>]*href="([^"]+)"', html)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)', html, flags=re.S)
    lines = []
    for i in range(min(max_results, len(titles), len(links))):
        t = re.sub(r"<[^>]+>", "", titles[i]).strip()
        s = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
        lines.append(f"- {t}\n  {links[i]}\n  {s}")
    return "\n".join(lines) if lines else "未找到结果"


class KnowledgeAgent(BaseAgent):
    name = "knowledge-agent"
    description = "新生医学图像分割知识问答（CNN/UNet/Transformer，RAG+联网搜索）"
    skills = [
        AgentSkill("rag_qa", "基于知识库回答"),
        AgentSkill("web_search", "联网补充检索"),
    ]

    def __init__(self):
        cfg = load_config()
        self.port = cfg["ports"]["knowledge"]
        self.rag = MedSegRAG()

    def handle(self, message: AgentMessage, metadata: dict) -> AgentMessage:
        q = message.text().strip()
        context = self.rag.build_context(q, top_k=3)
        system = (
            "你是医学图像分割课题组助教。优先依据【知识库检索结果】回答 CNN、U-Net、"
            "nnU-Net、Transformer 等基础问题。若知识库不足，可调用 web_search。"
            "回答用中文，简洁准确。"
        )
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"【知识库检索结果】\n{context}\n\n【问题】\n{q}",
            },
        ]
        first = chat(messages, tools=[WEB_SEARCH_TOOL])
        if first["tool_calls"]:
            for tc in first["tool_calls"]:
                if tc["name"] == "web_search":
                    try:
                        args = json.loads(tc["arguments"] or "{}")
                    except json.JSONDecodeError:
                        args = {"query": q}
                    result = web_search(args.get("query", q))
                    messages.append(
                        {
                            "role": "assistant",
                            "content": first["content"] or None,
                            "tool_calls": [
                                {
                                    "id": tc["id"],
                                    "type": "function",
                                    "function": {
                                        "name": tc["name"],
                                        "arguments": tc["arguments"],
                                    },
                                }
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        }
                    )
            second = chat(messages)
            return AgentMessage.agent_text(second["content"] or "(空回复)", message.context_id)

        # 无 LLM key 时，直接返回 RAG 片段
        content = first["content"]
        if content.startswith("[未配置") and context:
            content = f"{content}\n\n【知识库摘录】\n{context}"
        return AgentMessage.agent_text(content, message.context_id)
