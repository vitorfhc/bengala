"""Shared test fixtures."""

from __future__ import annotations

import pytest
import pytest_asyncio

import aiosqlite

from bengala.db.repository import Repository
from bengala.db.schema import SCHEMA_SQL


@pytest_asyncio.fixture
async def db_conn() -> aiosqlite.Connection:
    """In-memory SQLite connection with schema initialized."""
    conn = await aiosqlite.connect(":memory:")
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()
    yield conn  # type: ignore[misc]
    await conn.close()


@pytest_asyncio.fixture
async def repo(db_conn: aiosqlite.Connection) -> Repository:
    """Repository backed by in-memory database."""
    return Repository(db_conn)
