# -*- coding: utf-8 -*-
"""OpenAI 兼容 LLM 调用。"""
from __future__ import annotations

from typing import Any

from config import llm_api_key, load_config


def get_client():
    from openai import OpenAI

    cfg = load_config()
    key = llm_api_key(cfg)
    if not key:
        return None
    return OpenAI(api_key=key, base_url=cfg["llm"]["base_url"])


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    tools: list[dict] | None = None,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """返回 {content, tool_calls}。无 key 时走本地占位回复。"""
    cfg = load_config()
    client = get_client()
    model = model or cfg["llm"]["model"]
    if client is None:
        # ponytail: 无 key 时返回提示，避免整套系统不可用
        user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return {
            "content": f"[未配置 LLM_API_KEY，本地占位回复]\n收到问题：{user[:200]}\n请在 .env 中配置 API Key 后获得完整回答。",
            "tool_calls": [],
        }
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    resp = client.chat.completions.create(**kwargs)
    msg = resp.choices[0].message
    tool_calls = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            tool_calls.append(
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
            )
    return {"content": msg.content or "", "tool_calls": tool_calls}
