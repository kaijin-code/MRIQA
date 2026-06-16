from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "multi-role-agent")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:123456@192.168.10.174:5432/agentdb",
    )
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    dashscope_http_base_url: str | None = os.getenv("DASHSCOPE_HTTP_BASE_URL")
    qwen_model: str = os.getenv("QWEN_MODEL", "qwen3.6-plus")
    qwen_embedding_model: str = os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v3")
    rag_top_k: int = _get_int("RAG_TOP_K", 5)
    rag_min_similarity: float = _get_float("RAG_MIN_SIMILARITY", 0.2)
    chunk_size: int = _get_int("CHUNK_SIZE", 800)
    chunk_overlap: int = _get_int("CHUNK_OVERLAP", 100)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    db_echo: bool = os.getenv("DB_ECHO", "false").lower() == "true"
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = _get_int("JWT_EXPIRE_MINUTES", 1440)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
