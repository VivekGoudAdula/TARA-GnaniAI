"""
Database client and lifecycle management using Motor (async MongoDB driver).
Provides collection access and schema indexing for voice sessions and tenant-owned entities.
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: Optional[AsyncIOMotorClient] = None
_client_loop = None


def get_mongo_uri() -> str:
    """Return MongoDB URI from environment or default to local instance."""
    return os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")


def get_db_name() -> str:
    """Return active database name from environment or default."""
    return os.getenv("MONGO_DB_NAME", "tara_gnani")


def get_client() -> AsyncIOMotorClient:
    """Get or instantiate AsyncIOMotorClient, handling event loop recreation in test runners."""
    global _client, _client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _client is None or (_client_loop is not None and _client_loop is not current_loop):
        _client = AsyncIOMotorClient(get_mongo_uri())
        _client_loop = current_loop
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """Return reference to default application database."""
    return get_client()[get_db_name()]


async def init_db() -> None:
    """Create necessary collection indexes for multi-tenant isolation and fast lookups."""
    db = get_db()

    # Tenant-owned collections indexed by tenant_id
    await db["tenants"].create_index("tenant_id", unique=True)
    await db["users"].create_index("email", unique=True)
    await db["users"].create_index("tenant_id")

    await db["products"].create_index("tenant_id")
    await db["products"].create_index([("tenant_id", 1), ("product_id", 1)], unique=True)

    await db["customers"].create_index("tenant_id")
    await db["customers"].create_index([("tenant_id", 1), ("phone", 1)], unique=True)

    await db["leads"].create_index("tenant_id")
    await db["leads"].create_index([("tenant_id", 1), ("phone", 1)], unique=True)

    await db["product_matches"].create_index("tenant_id")
    await db["product_matches"].create_index([("tenant_id", 1), ("record_id", 1)])
    await db["product_matches"].create_index([("tenant_id", 1), ("fit_score", -1)])

    await db["voice_sessions"].create_index("tenant_id")
    await db["voice_sessions"].create_index("session_id", unique=True)
    await db["voice_sessions"].create_index("started_at")


async def close_db() -> None:
    """Close active MongoDB client connection if open."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
