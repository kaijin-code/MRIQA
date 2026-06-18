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

        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='conversations' AND column_name='deleted_at'"
        ))
        if result.first() is None:
            await conn.execute(text(
                "ALTER TABLE conversations ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE"
            ))

        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='messages' AND column_name='deleted_at'"
        ))
        if result.first() is None:
            await conn.execute(text(
                "ALTER TABLE messages ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE"
            ))

        result = await conn.execute(text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name='messages' AND column_name='conversation_id'"
        ))
        row = result.first()
        if row is not None and row[0] == 'NO':
            await conn.execute(text(
                "ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_conversation_id_fkey"
            ))
            await conn.execute(text(
                "ALTER TABLE messages ALTER COLUMN conversation_id DROP NOT NULL"
            ))
            await conn.execute(text(
                "ALTER TABLE messages ADD CONSTRAINT messages_conversation_id_fkey "
                "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL"
            ))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
