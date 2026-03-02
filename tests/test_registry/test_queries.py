"""Tests for registry query functions against SQLite."""

from pathlib import Path

import pytest

from ea_workbench.models.elements import Capability, Element, Relationship
from ea_workbench.registry.db import get_connection, initialise_schema
from ea_workbench.registry.queries import (
    domain_summary,
    find_orphan_elements,
    get_element,
    link_element_to_capability,
    list_capabilities,
    search_elements,
    upsert_capability,
    upsert_element,
    upsert_relationship,
)

_EL1 = Element(
    id="comp-doc-intel",
    name="Document Intelligence Pipeline",
    archimate_type="application-component",
    domain="knowledge-infrastructure",
    description="Azure AI Document Intelligence pipeline",
    confidence=0.95,
)

_EL2 = Element(
    id="svc-vector-search",
    name="Vector Search Service",
    archimate_type="application-service",
    domain="knowledge-infrastructure",
    confidence=0.9,
)

_EL3 = Element(
    id="data-safety-store",
    name="Safety Knowledge Store",
    archimate_type="data-object",
    domain="safety",
    confidence=0.85,
)

_REL = Relationship(
    id="rel-001",
    source_element_id="comp-doc-intel",
    target_element_id="svc-vector-search",
    archimate_type="serving-relationship",
    description="Pipeline feeds search service",
    confidence=0.8,
)

_CAP = Capability(
    id="cap-doc-ingestion",
    name="Document Ingestion & Processing",
    level=2,
    domain="knowledge-infrastructure",
    maturity="initial",
)


@pytest.fixture
async def db(tmp_path: Path) -> str:
    """Create a fresh initialised SQLite database for each test."""
    db_path = str(tmp_path / "test_registry.db")
    await initialise_schema(db_path)
    return db_path


async def test_upsert_element_insert(db: str) -> None:
    """upsert_element inserts a new element."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        result = await get_element(conn, "comp-doc-intel")
    assert result is not None
    assert result.name == "Document Intelligence Pipeline"


async def test_upsert_element_idempotent(db: str) -> None:
    """Upserting the same element twice doesn't duplicate it."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        await upsert_element(conn, _EL1)
        async with conn.execute(
            "SELECT COUNT(*) as c FROM elements WHERE id=?", ("comp-doc-intel",)
        ) as cur:
            row = await cur.fetchone()
    assert row is not None
    assert row["c"] == 1


async def test_upsert_element_update(db: str) -> None:
    """Upserting with same ID updates the record."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        updated = _EL1.model_copy(update={"confidence": 0.5})
        await upsert_element(conn, updated)
        result = await get_element(conn, "comp-doc-intel")
    assert result is not None
    assert result.confidence == 0.5


async def test_get_element_missing(db: str) -> None:
    """get_element returns None for unknown ID."""
    async with get_connection(db) as conn:
        result = await get_element(conn, "does-not-exist")
    assert result is None


async def test_search_elements_by_name(db: str) -> None:
    """search_elements matches on name substring."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        await upsert_element(conn, _EL2)
        await upsert_element(conn, _EL3)
        results = await search_elements(conn, "intelligence")
    assert len(results) == 1
    assert results[0].id == "comp-doc-intel"


async def test_search_elements_domain_filter(db: str) -> None:
    """search_elements filters by domain."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        await upsert_element(conn, _EL2)
        await upsert_element(conn, _EL3)
        results = await search_elements(conn, "", domain="safety")
    assert all(r.domain == "safety" for r in results)
    assert len(results) == 1


async def test_search_elements_type_filter(db: str) -> None:
    """search_elements filters by archimate_type."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        await upsert_element(conn, _EL2)
        results = await search_elements(conn, "", archimate_type="application-component")
    assert all(r.archimate_type == "application-component" for r in results)


async def test_upsert_relationship(db: str) -> None:
    """upsert_relationship inserts a relationship."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        await upsert_element(conn, _EL2)
        await upsert_relationship(conn, _REL)
        async with conn.execute("SELECT COUNT(*) as c FROM relationships") as cur:
            row = await cur.fetchone()
    assert row is not None
    assert row["c"] == 1


async def test_upsert_relationship_idempotent(db: str) -> None:
    """Upserting same relationship twice doesn't duplicate."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        await upsert_element(conn, _EL2)
        await upsert_relationship(conn, _REL)
        await upsert_relationship(conn, _REL)
        async with conn.execute("SELECT COUNT(*) as c FROM relationships") as cur:
            row = await cur.fetchone()
    assert row is not None
    assert row["c"] == 1


async def test_upsert_capability(db: str) -> None:
    """upsert_capability inserts a capability."""
    async with get_connection(db) as conn:
        await upsert_capability(conn, _CAP)
        caps = await list_capabilities(conn)
    assert len(caps) == 1
    assert caps[0].id == "cap-doc-ingestion"


async def test_list_capabilities_root(db: str) -> None:
    """list_capabilities with no parent returns root-level items."""
    root = Capability(id="cap-root", name="Root", level=0)
    child = Capability(id="cap-child", name="Child", level=1, parent_id="cap-root")
    async with get_connection(db) as conn:
        await upsert_capability(conn, root)
        await upsert_capability(conn, child)
        roots = await list_capabilities(conn)
    assert len(roots) == 1
    assert roots[0].id == "cap-root"


async def test_list_capabilities_by_parent(db: str) -> None:
    """list_capabilities filtered by parent_id returns children."""
    root = Capability(id="cap-root", name="Root", level=0)
    child = Capability(id="cap-child", name="Child", level=1, parent_id="cap-root")
    async with get_connection(db) as conn:
        await upsert_capability(conn, root)
        await upsert_capability(conn, child)
        children = await list_capabilities(conn, parent_id="cap-root")
    assert len(children) == 1
    assert children[0].id == "cap-child"


async def test_find_orphan_elements(db: str) -> None:
    """find_orphan_elements returns elements not linked to a capability."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        await upsert_element(conn, _EL2)
        await upsert_capability(conn, _CAP)
        await link_element_to_capability(conn, "comp-doc-intel", "cap-doc-ingestion")
        orphans = await find_orphan_elements(conn)
    assert any(o.id == "svc-vector-search" for o in orphans)
    assert all(o.id != "comp-doc-intel" for o in orphans)


async def test_domain_summary(db: str) -> None:
    """domain_summary returns correct counts."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        await upsert_element(conn, _EL2)
        await upsert_element(conn, _EL3)
        summary = await domain_summary(conn)
    domains = {row["domain"] for row in summary}
    assert "safety" in domains
    assert "knowledge-infrastructure" in domains


async def test_domain_summary_filtered(db: str) -> None:
    """domain_summary with domain filter returns only that domain."""
    async with get_connection(db) as conn:
        await upsert_element(conn, _EL1)
        await upsert_element(conn, _EL3)
        summary = await domain_summary(conn, domain="safety")
    assert all(row["domain"] == "safety" for row in summary)
