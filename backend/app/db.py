from __future__ import annotations

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from .config import get_settings
from .models import Base

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=settings.db_echo, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='conversations' AND column_name='user_id'"
        ))
        if result.first() is None:
            await conn.execute(text(
                "ALTER TABLE conversations ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE"
            ))
            await conn.execute(text(
                "CREATE INDEX ix_conversations_user_id ON conversations(user_id)"
            ))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
