"""
Database engine and session configuration.
Uses async SQLAlchemy for FastAPI endpoints, sync for seed/migration scripts.
"""

import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load .env from repo root (two levels up from apps/api/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://nadi:nadi@localhost:5433/nadi",
)
DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://nadi:nadi@localhost:5433/nadi",
)

# Async engine for FastAPI
async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Sync engine for seed scripts and migrations
sync_engine = create_engine(DATABASE_URL_SYNC, echo=False)
SyncSessionLocal = sessionmaker(bind=sync_engine)


async def get_db():
    """FastAPI dependency yielding an async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
