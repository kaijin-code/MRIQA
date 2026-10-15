# Backend

FastAPI 后端：JWT 鉴权、多角色 Agent 调度、RAG 检索（pgvector）、SSE 流式输出。

## Quick start (venv)

1. Create and activate a virtual environment:
   - Create: `python -m venv .venv`
   - Activate (PowerShell): `.\.venv\Scripts\Activate.ps1`

2. Install dependencies:
   - `pip install -r requirements.lock.txt`（精确复现已验证环境）
   - 或 `pip install -r requirements.txt`（按 `>=` 约束装最新版）

3. Configure environment variables:
   - `Copy-Item .env.example .env`
   - Edit `.env` with your credentials
   - Set `DASHSCOPE_API_KEY` for Tongyi Qwen access
   - Set `DASHSCOPE_HTTP_BASE_URL` when using the OpenAI-compatible endpoint (e.g. `https://dashscope.aliyuncs.com/compatible-mode/v1`); chat and embeddings both go through it via the OpenAI protocol, and the native DashScope SDK is not used
   - Confirm `DATABASE_URL` (default: `postgresql+asyncpg://postgres:123456@localhost:5432/agentdb`, matches the root `docker-compose.yml`)

4. Start the API server:
   - `.\.venv\Scripts\uvicorn app.main:app --reload`
   - Or activate the venv first, then `uvicorn app.main:app --reload`

## Database

根目录 `docker-compose.yml` 提供本地 PostgreSQL + pgvector：

```cmd
docker compose up -d
```

后端启动时自动执行 `CREATE EXTENSION IF NOT EXISTS vector`、建表与增量列迁移（含 `users.is_admin`），无需手动迁移。也可通过 `DATABASE_URL` 指向已有实例。

## 知识库权限

文档接口（ingest / upload / list / download / delete）仅限管理员（`users.is_admin`）；启动时会自动将 `admin` 用户名置为管理员。普通用户仅通过 RAG 检索间接消费知识库。

## Updating the lock file

依赖变更后重新生成锁定：

```cmd
pip freeze > requirements.lock.txt
```
