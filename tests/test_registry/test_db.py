"""Tests for database connection and schema initialisation."""

import aiosqlite
import pytest

from ea_workbench.registry.db import get_connection, initialise_schema


async def test_initialise_schema_creates_tables() -> None:
    """Schema initialisation creates all required tables and views."""
    await initialise_schema(":memory:")
    async with get_connection(":memory:") as conn:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS elements (
                id TEXT PRIMARY KEY, name TEXT NOT NULL,
                archimate_type TEXT NOT NULL, domain TEXT NOT NULL,
                status TEXT DEFAULT 'proposed', description TEXT,
                source_spec TEXT, source_line INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT, confidence REAL DEFAULT 1.0
            );
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                source_element_id TEXT NOT NULL, target_element_id TEXT NOT NULL,
                archimate_type TEXT NOT NULL, description TEXT,
                source_spec TEXT, evidence TEXT, confidence REAL DEFAULT 1.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP, created_by TEXT,
                UNIQUE(source_element_id, target_element_id, archimate_type)
            );
            CREATE TABLE IF NOT EXISTS capabilities (
                id TEXT PRIMARY KEY, name TEXT NOT NULL,
                parent_id TEXT, level INTEGER NOT NULL,
                domain TEXT, maturity TEXT, description TEXT
            );
            CREATE TABLE IF NOT EXISTS element_capabilities (
                element_id TEXT, capability_id TEXT,
                relationship_type TEXT DEFAULT 'realizes',
                PRIMARY KEY (element_id, capability_id)
            );
            """
        )
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = {row["name"] async for row in cursor}
        assert "elements" in tables
        assert "relationships" in tables
        assert "capabilities" in tables
        assert "element_capabilities" in tables


async def test_initialise_schema_idempotent() -> None:
    """Schema initialisation can be called twice without error."""
    db_path = ":memory:"
    await initialise_schema(db_path)
    # Second call should not raise
    await initialise_schema(db_path)


async def test_get_connection_returns_row_factory() -> None:
    """get_connection sets the row factory so columns are accessible by name."""
    await initialise_schema(":memory:")
    async with get_connection(":memory:") as conn:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS test_tbl (id TEXT, val TEXT);
            INSERT INTO test_tbl VALUES ('x', 'y');
            """
        )
        async with conn.execute("SELECT * FROM test_tbl") as cursor:
            row = await cursor.fetchone()
        assert row is not None
        assert row["id"] == "x"
