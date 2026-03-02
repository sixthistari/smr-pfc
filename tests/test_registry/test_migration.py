"""Tests for the Phase 0 → Option C migration utility."""

from pathlib import Path

import pytest

from ea_workbench.registry.db import get_connection, initialise_schema
from ea_workbench.registry.migration import migrate_phase0_to_option_c
from ea_workbench.registry.queries import upsert_capability, upsert_element
from ea_workbench.models.elements import Capability, Element


@pytest.fixture
async def db_path(tmp_path: Path) -> str:
    """Create a fresh initialised SQLite database."""
    path = str(tmp_path / "test_migration.db")
    await initialise_schema(path)
    return path


async def test_migrate_empty_db(db_path: str) -> None:
    """Migration of an empty database returns zero counts."""
    result = await migrate_phase0_to_option_c(db_path)
    assert result["migrated"] == 0
    assert result["skipped"] == 0
    assert result["errors"] == []


async def test_migrate_motivation_element(db_path: str) -> None:
    """A driver element in elements table migrates to motivation table."""
    driver = Element(
        id="DRV-migration-001",
        name="Legacy Driver",
        archimate_type="driver",
        domain="dom-legacy",
        status="draft",
        confidence=0.9,
    )
    async with get_connection(db_path) as conn:
        await upsert_element(conn, driver)

    result = await migrate_phase0_to_option_c(db_path)

    assert result["migrated"] >= 1
    async with get_connection(db_path) as conn:
        async with conn.execute(
            "SELECT * FROM motivation WHERE id = ?", ("DRV-migration-001",)
        ) as cursor:
            row = await cursor.fetchone()
    assert row is not None
    assert row["name"] == "Legacy Driver"
    assert row["archimate_type"] == "driver"


async def test_migrate_capability(db_path: str) -> None:
    """A capability row migrates to strategy table with archimate_type=capability."""
    cap = Capability(
        id="CAP-migration-001",
        name="Legacy Capability",
        level=1,
        domain="dom-legacy",
        maturity="initial",
    )
    async with get_connection(db_path) as conn:
        await upsert_capability(conn, cap)

    result = await migrate_phase0_to_option_c(db_path)

    assert result["migrated"] >= 1
    async with get_connection(db_path) as conn:
        async with conn.execute(
            "SELECT * FROM strategy WHERE id = ?", ("CAP-migration-001",)
        ) as cursor:
            row = await cursor.fetchone()
    assert row is not None
    assert row["archimate_type"] == "capability"
    assert row["name"] == "Legacy Capability"


async def test_migrate_unknown_type(db_path: str) -> None:
    """An element with unknown archimate_type goes to the skipped count."""
    el = Element(
        id="UNKNOWN-001",
        name="Unknown Type Element",
        archimate_type="custom-unknown-type",
        domain="dom-test",
    )
    async with get_connection(db_path) as conn:
        await upsert_element(conn, el)

    result = await migrate_phase0_to_option_c(db_path)

    assert result["skipped"] >= 1
