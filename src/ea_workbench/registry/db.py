"""Database connection management and schema initialisation for the element registry."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiosqlite

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS elements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT DEFAULT 'proposed',
    description TEXT,
    source_spec TEXT,
    source_line INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    confidence REAL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    source_element_id TEXT NOT NULL REFERENCES elements(id),
    target_element_id TEXT NOT NULL REFERENCES elements(id),
    archimate_type TEXT NOT NULL,
    description TEXT,
    source_spec TEXT,
    evidence TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    UNIQUE(source_element_id, target_element_id, archimate_type)
);

CREATE TABLE IF NOT EXISTS capabilities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT REFERENCES capabilities(id),
    level INTEGER NOT NULL,
    domain TEXT,
    maturity TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS element_capabilities (
    element_id TEXT REFERENCES elements(id),
    capability_id TEXT REFERENCES capabilities(id),
    relationship_type TEXT DEFAULT 'realizes',
    PRIMARY KEY (element_id, capability_id)
);

CREATE VIEW IF NOT EXISTS v_orphan_elements AS
SELECT e.* FROM elements e
LEFT JOIN element_capabilities ec ON e.id = ec.element_id
WHERE ec.capability_id IS NULL;

CREATE VIEW IF NOT EXISTS v_domain_summary AS
SELECT domain, archimate_type, status, COUNT(*) as count
FROM elements GROUP BY domain, archimate_type, status;
"""


@asynccontextmanager
async def get_connection(db_path: str) -> AsyncIterator[aiosqlite.Connection]:
    """Open an aiosqlite connection with row_factory set to Row.

    Args:
        db_path: Path to the SQLite database file, or ':memory:' for in-memory.

    Yields:
        An open aiosqlite connection.
    """
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        yield conn


async def initialise_schema(db_path: str) -> None:
    """Create all tables and views if they do not already exist.

    Args:
        db_path: Path to the SQLite database file, or ':memory:'.
    """
    async with get_connection(db_path) as conn:
        await conn.executescript(_SCHEMA_SQL)
        await conn.commit()
    logger.info("Element registry schema initialised at %s", db_path)
