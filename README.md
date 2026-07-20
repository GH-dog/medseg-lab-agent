# 医学图像分割课题组 AI-Agent

基于 A2A（Agent-to-Agent）协议的垂直落地多 Agent 系统，面向医学图像分割实验课题组。

## 能力

1. **权限管理**：老师（`teacher`）授予/撤销组内代码目录读写权限
2. **知识问答**：CNN / U-Net / nnU-Net / Transformer 基础知识库 + FAISS RAG + 联网搜索
3. **论文检索**：arXiv 最新论文 + 学校账号 Cookie/代理访问已购期刊站点
4. **AI Coding**：Codex 兼容模型（OpenAI 兼容 API）在 ACL 允许路径下读写代码

协议实现对齐同目录学习项目 `a2a-cpp-sdk` 的 JSON-RPC 方法：`message/send`、`/.well-known/agent-card.json`。

## 快速开始

```bash
cd AI-powered-Network-Diagnostics-main
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
copy config.example.json config.json
# 编辑 .env 填入 LLM_API_KEY
```

终端 1：

```bash
python run_agents.py
```

终端 2：

```bash
python cli.py
# 老师身份：
python cli.py --user teacher
```

## 端口

| Agent | 端口 |
|-------|------|
| Orchestrator | 8000 |
| Permission | 8001 |
| Knowledge | 8002 |
| Paper | 8003 |
| Coding | 8004 |

## 期刊学校账号

在 `.env` 中设置浏览器登录后的 Cookie，例如 `IEEE_COOKIE=...`，并在 `config.json` 的 `papers.journals` 中配置 `search_url_template` 与 `cookie_env`。可选设置 `HTTP_PROXY` 走机构代理。

## 目录说明

- `a2a/`：A2A HTTP 协议
- `agents/`：四个专业 Agent + 编排器
- `knowledge/`：医学分割知识库与 RAG
- `data/permissions.json`：ACL
- `workspace/`：组内代码工作区（受权限控制）
