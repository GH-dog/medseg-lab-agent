# -*- coding: utf-8 -*-
"""论文检索 Agent：arXiv + 机构期刊 Cookie/代理适配器。"""
from __future__ import annotations

import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from a2a.protocol import AgentMessage, AgentSkill
from agents.base import BaseAgent
from config import load_config

ARXIV_API = "http://export.arxiv.org/api/query"


def search_arxiv(query: str, max_results: int = 10, categories: list[str] | None = None) -> list[dict]:
    # 在标题/摘要中搜，避免 all+category 组合漂到无关最新稿
    q = query.strip()
    if ":" not in q:
        search_q = f'(ti:"{q}" OR abs:"{q}")'
    else:
        search_q = q
    cats = categories or []
    if cats:
        cat_q = " OR ".join(f"cat:{c}" for c in cats)
        search_q = f"({search_q}) AND ({cat_q})"
    params = urllib.parse.urlencode(
        {
            "search_query": search_q,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    url = f"{ARXIV_API}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "MedSegLabAgent/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        xml_data = r.read()
    root = ET.fromstring(xml_data)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    papers = []
    for entry in root.findall("a:entry", ns):
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        title = re.sub(r"\s+", " ", title)
        summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
        summary = re.sub(r"\s+", " ", summary)[:400]
        published = entry.findtext("a:published", default="", namespaces=ns) or ""
        link = ""
        for l in entry.findall("a:link", ns):
            if l.attrib.get("type") == "text/html" or l.attrib.get("rel") == "alternate":
                link = l.attrib.get("href", "")
                break
        papers.append(
            {
                "title": title,
                "published": published[:10],
                "summary": summary,
                "url": link,
                "source": "arXiv",
            }
        )
    return papers


def search_journal(journal: dict, query: str, proxy: str = "") -> dict:
    """用学校账号 Cookie + 可选代理访问期刊搜索页，返回摘要状态（非完整解析）。"""
    template = journal.get("search_url_template") or ""
    url = template.format(query=urllib.parse.quote(query))
    cookie_env = journal.get("cookie_env") or ""
    cookie = os.environ.get(cookie_env, "") if cookie_env else ""
    headers = {"User-Agent": "MedSegLabAgent/1.0"}
    if cookie:
        headers["Cookie"] = cookie
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers) if handlers else urllib.request.build_opener()
    req = urllib.request.Request(url, headers=headers)
    try:
        with opener.open(req, timeout=25) as r:
            body = r.read(8000).decode("utf-8", errors="replace")
            status = r.status
    except Exception as e:
        return {
            "name": journal.get("name"),
            "ok": False,
            "url": url,
            "error": str(e),
            "hint": f"请确认已登录学校账号并设置环境变量 {cookie_env}，或配置 proxy。",
        }
    # 粗判定是否像登录墙
    login_wall = bool(re.search(r"sign\s*in|log\s*in|登录|认证", body, flags=re.I))
    return {
        "name": journal.get("name"),
        "ok": True,
        "url": url,
        "http_status": status,
        "cookie_set": bool(cookie),
        "possible_login_wall": login_wall,
        "snippet": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))[:300],
    }


class PaperAgent(BaseAgent):
    name = "paper-agent"
    description = "检索最新医学图像分割论文（arXiv + 机构期刊站点）"
    skills = [
        AgentSkill("arxiv", "arXiv 最新论文"),
        AgentSkill("journal", "学校账号期刊站点检索"),
    ]

    def __init__(self):
        cfg = load_config()
        self.port = cfg["ports"]["paper"]
        self.cfg = cfg

    def handle(self, message: AgentMessage, metadata: dict) -> AgentMessage:
        text = message.text().strip()
        papers_cfg = self.cfg.get("papers") or {}
        query = text or papers_cfg.get("default_query", "medical image segmentation")
        # 允许 "paper: xxx" / "期刊: xxx"
        m = re.match(r"^(paper|论文|arxiv|期刊|journal)[:：\s]+(.+)$", text, flags=re.I)
        mode = "all"
        if m:
            tag = m.group(1).lower()
            query = m.group(2).strip()
            if tag in ("期刊", "journal"):
                mode = "journal"
            elif tag in ("arxiv",):
                mode = "arxiv"

        if not query:
            query = papers_cfg.get("default_query", "medical image segmentation")

        lines = [f"查询: {query}", ""]
        if mode in ("all", "arxiv"):
            try:
                items = search_arxiv(
                    query,
                    max_results=int(papers_cfg.get("max_results", 10)),
                    categories=papers_cfg.get("arxiv_categories"),
                )
                lines.append("## arXiv 最新")
                if not items:
                    lines.append("(无结果)")
                for i, p in enumerate(items, 1):
                    lines.append(f"{i}. [{p['published']}] {p['title']}")
                    lines.append(f"   {p['url']}")
                    lines.append(f"   {p['summary'][:180]}...")
                    lines.append("")
            except Exception as e:
                lines.append(f"arXiv 检索失败: {e}")

        if mode in ("all", "journal"):
            proxy = self.cfg.get("proxy") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or ""
            journals = papers_cfg.get("journals") or []
            if journals:
                lines.append("## 机构期刊站点")
                for j in journals:
                    result = search_journal(j, query, proxy=proxy)
                    if result.get("ok"):
                        lines.append(
                            f"- {result['name']}: HTTP {result.get('http_status')} "
                            f"cookie={'有' if result.get('cookie_set') else '无'} "
                            f"登录墙疑似={result.get('possible_login_wall')}"
                        )
                        lines.append(f"  链接: {result['url']}")
                        lines.append(f"  摘录: {result.get('snippet', '')[:200]}")
                    else:
                        lines.append(f"- {result['name']}: 失败 — {result.get('error')}")
                        lines.append(f"  {result.get('hint')}")
                        lines.append(f"  链接: {result.get('url')}")
                lines.append("")
            elif mode == "journal":
                lines.append("未配置 papers.journals，请在 config.json 中添加期刊 search_url_template 与 cookie_env。")

        return AgentMessage.agent_text("\n".join(lines), message.context_id)
