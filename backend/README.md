# Backend

## Quick start (venv)

1. Create and activate a virtual environment:
   - Create: `python -m venv .venv`
   - Activate (PowerShell): `.\.venv\Scripts\Activate.ps1`

2. Install dependencies:
   - `pip install -r requirements.txt`

3. Configure environment variables:
   - `Copy-Item .env.example .env`
   - Edit `.env` with your credentials
   - Set `DASHSCOPE_API_KEY` for Tongyi Qwen access
   - Set `DASHSCOPE_HTTP_BASE_URL` when using the compatible-mode endpoint
   - Confirm `DATABASE_URL` (default: `postgresql+asyncpg://postgres:123456@192.168.10.174:5432/agentdb`)

4. Start the API server:
   - `uvicorn app.main:app --reload`

## Database

Ensure PostgreSQL is running with the pgvector extension installed.
