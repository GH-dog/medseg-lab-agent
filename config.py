# -*- coding: utf-8 -*-
"""加载项目配置。"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    # ponytail: 无 python-dotenv 时手动读 .env
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

_DEFAULT = {
    "llm": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "LLM_API_KEY",
        "model": "qwen-plus",
        "coding_model": "qwen-coder-plus",
    },
    "ports": {
        "orchestrator": 8000,
        "permission": 8001,
        "knowledge": 8002,
        "paper": 8003,
        "coding": 8004,
    },
    "workspace": {"root": "workspace"},
    "papers": {
        "arxiv_categories": ["eess.IV", "cs.CV"],
        "default_query": "medical image segmentation",
        "max_results": 10,
        "journals": [],
    },
    "proxy": "",
}


def load_config() -> dict:
    """从 config.json 读取，不存在则用 example 或内置默认。"""
    cfg_path = ROOT / "config.json"
    example = ROOT / "config.example.json"
    if cfg_path.exists():
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    elif example.exists():
        data = json.loads(example.read_text(encoding="utf-8"))
    else:
        data = {}
    # 浅合并默认
    out = dict(_DEFAULT)
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            merged = dict(out[k])
            merged.update(v)
            out[k] = merged
        else:
            out[k] = v
    return out


def llm_api_key(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    env_name = cfg["llm"].get("api_key_env", "LLM_API_KEY")
    return os.environ.get(env_name) or os.environ.get("OPENAI_API_KEY") or ""


def workspace_root(cfg: dict | None = None) -> Path:
    cfg = cfg or load_config()
    p = Path(cfg["workspace"]["root"])
    if not p.is_absolute():
        p = ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p
