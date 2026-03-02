"""Tests for the Option C 21-table database schema."""

from pathlib import Path

import pytest

from ea_workbench.models.business_architecture import BusinessArchElement
from ea_workbench.models.motivation import MotivationElement
from ea_workbench.models.solution_architecture import SolutionArchElement
from ea_workbench.models.strategy import StrategyElement
from ea_workbench.registry.db import get_connection, initialise_schema
from ea_workbench.registry.queries import (
    upsert_business_arch,
    upsert_motivation,
    upsert_solution_arch,
    upsert_strategy,
    validate_relationship,
)

_EXPECTED_TABLES = {
    # Option C tables
    "domains",
    "motivation",
    "strategy",
    "business_architecture",
    "process_steps",
    "solution_architecture",
    "implementation",
    "relationships",
    "valid_relationships",
    "solutions",
    "solution_components",
    "solution_diagrams",
    "deployment_targets",
    "solution_deployments",
    "practice_artefacts",
    "engagements",
    "governance_controls",
    "staging_items",
    "quality_evaluations",
    "agent_runs",
    "sessions",
    # Legacy tables
    "elements",
    "capabilities",
    "element_capabilities",
}


@pytest.fixture
async def db(tmp_path: Path) -> str:
    """Create a fresh initialised SQLite database for each test."""
    db_path = str(tmp_path / "test_option_c.db")
    await initialise_schema(db_path)
    return db_path


async def test_init_db_creates_all_tables(db: str) -> None:
    """All 21 Option C tables plus legacy tables exist after initialise_schema."""
    async with get_connection(db) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = {row["name"] async for row in cursor}
    for expected in _EXPECTED_TABLES:
        assert expected in tables, f"Missing table: {expected}"


async def test_valid_relationships_seeded(db: str) -> None:
    """valid_relationships table is non-empty after initialisation."""
    async with get_connection(db) as conn:
        async with conn.execute("SELECT COUNT(*) as c FROM valid_relationships") as cursor:
            row = await cursor.fetchone()
    assert row is not None
    assert row["c"] > 0


async def test_upsert_motivation_roundtrip(db: str) -> None:
    """MotivationElement can be upserted and retrieved via element_registry_view."""
    el = MotivationElement(
        id="DRV-001",
        name="Test Driver",
        archimate_type="driver",
        domain_id="dom-test",
        description="A test driver",
    )
    async with get_connection(db) as conn:
        result_id = await upsert_motivation(conn, el)
        async with conn.execute(
            "SELECT * FROM element_registry_view WHERE id = ?", ("DRV-001",)
        ) as cursor:
            row = await cursor.fetchone()

    assert result_id == "DRV-001"
    assert row is not None
    assert row["name"] == "Test Driver"
    assert row["archimate_type"] == "driver"
    assert row["source_table"] == "motivation"


async def test_upsert_strategy_roundtrip(db: str) -> None:
    """StrategyElement can be upserted and retrieved via element_registry_view."""
    el = StrategyElement(
        id="CAP-001",
        name="Test Capability",
        archimate_type="capability",
        domain_id="dom-test",
        level=1,
        maturity="initial",
    )
    async with get_connection(db) as conn:
        await upsert_strategy(conn, el)
        async with conn.execute(
            "SELECT * FROM element_registry_view WHERE id = ?", ("CAP-001",)
        ) as cursor:
            row = await cursor.fetchone()

    assert row is not None
    assert row["source_table"] == "strategy"


async def test_upsert_business_arch_roundtrip(db: str) -> None:
    """BusinessArchElement can be upserted and retrieved via element_registry_view."""
    el = BusinessArchElement(
        id="BA-001",
        name="Test Actor",
        archimate_type="business-actor",
        domain_id="dom-test",
        actor_type="person",
    )
    async with get_connection(db) as conn:
        await upsert_business_arch(conn, el)
        async with conn.execute(
            "SELECT * FROM element_registry_view WHERE id = ?", ("BA-001",)
        ) as cursor:
            row = await cursor.fetchone()

    assert row is not None
    assert row["source_table"] == "business_architecture"


async def test_upsert_solution_arch_roundtrip(db: str) -> None:
    """SolutionArchElement can be upserted and retrieved via element_registry_view."""
    el = SolutionArchElement(
        id="comp-test",
        name="Test Component",
        archimate_type="application-component",
        domain_id="dom-test",
        is_agent=1,
        default_autonomy="L2",
    )
    async with get_connection(db) as conn:
        await upsert_solution_arch(conn, el)
        async with conn.execute(
            "SELECT * FROM element_registry_view WHERE id = ?", ("comp-test",)
        ) as cursor:
            row = await cursor.fetchone()

    assert row is not None
    assert row["source_table"] == "solution_architecture"


async def test_validate_relationship_known(db: str) -> None:
    """Known ArchiMate relationship pair returns True."""
    async with get_connection(db) as conn:
        result = await validate_relationship(
            conn, "application-service", "business-process", "serving"
        )
    assert result is True


async def test_validate_relationship_unknown(db: str) -> None:
    """Unknown relationship pair returns False."""
    async with get_connection(db) as conn:
        result = await validate_relationship(
            conn, "artifact", "stakeholder", "composition"
        )
    assert result is False
