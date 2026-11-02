"""
Database client and lifecycle management using Motor (async MongoDB driver).
Provides collection access and schema indexing for voice sessions.
"""
from __future__ import annotations

import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: Optional[AsyncIOMotorClient] = None


def get_mongo_uri() -> str:
    """Return MongoDB URI from environment or default to local instance."""
    return os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")


def get_db_name() -> str:
    """Return active database name from environment or default."""
    return os.getenv("MONGO_DB_NAME", "tara_gnani")


def get_client() -> AsyncIOMotorClient:
    """Get or instantiate singleton AsyncIOMotorClient."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(get_mongo_uri())
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """Return reference to default application database."""
    return get_client()[get_db_name()]


async def init_db() -> None:
    """Create necessary collection indexes for voice sessions."""
    db = get_db()
    sessions = db["voice_sessions"]
    # Ensure indexes on session_id and started_at
    await sessions.create_index("session_id", unique=True)
    await sessions.create_index("started_at")


async def close_db() -> None:
    """Close active MongoDB client connection if open."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
