"""Common query functions for the element registry."""

import logging

import aiosqlite

from ea_workbench.models.elements import Capability, Element, Relationship

logger = logging.getLogger(__name__)


def _row_to_element(row: aiosqlite.Row) -> Element:
    """Convert a database row to an Element model."""
    return Element(
        id=row["id"],
        name=row["name"],
        archimate_type=row["archimate_type"],
        domain=row["domain"],
        status=row["status"],
        description=row["description"],
        source_spec=row["source_spec"],
        source_line=row["source_line"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        created_by=row["created_by"],
        confidence=row["confidence"],
    )


def _row_to_capability(row: aiosqlite.Row) -> Capability:
    """Convert a database row to a Capability model."""
    return Capability(
        id=row["id"],
        name=row["name"],
        parent_id=row["parent_id"],
        level=row["level"],
        domain=row["domain"],
        maturity=row["maturity"],
        description=row["description"],
    )


async def upsert_element(conn: aiosqlite.Connection, element: Element) -> None:
    """Insert or replace an element in the registry.

    Args:
        conn: Open database connection.
        element: Element to upsert.
    """
    await conn.execute(
        """
        INSERT INTO elements
            (id, name, archimate_type, domain, status, description,
             source_spec, source_line, created_at, updated_at, created_by, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            archimate_type=excluded.archimate_type,
            domain=excluded.domain,
            status=excluded.status,
            description=excluded.description,
            source_spec=excluded.source_spec,
            source_line=excluded.source_line,
            updated_at=excluded.updated_at,
            created_by=excluded.created_by,
            confidence=excluded.confidence
        """,
        (
            element.id,
            element.name,
            element.archimate_type,
            element.domain,
            element.status,
            element.description,
            element.source_spec,
            element.source_line,
            element.created_at,
            element.updated_at,
            element.created_by,
            element.confidence,
        ),
    )
    await conn.commit()


async def upsert_relationship(conn: aiosqlite.Connection, rel: Relationship) -> None:
    """Insert or replace a relationship in the registry.

    Args:
        conn: Open database connection.
        rel: Relationship to upsert.
    """
    await conn.execute(
        """
        INSERT INTO relationships
            (id, source_element_id, target_element_id, archimate_type,
             description, source_spec, evidence, confidence, created_at, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_element_id, target_element_id, archimate_type) DO UPDATE SET
            id=excluded.id,
            description=excluded.description,
            source_spec=excluded.source_spec,
            evidence=excluded.evidence,
            confidence=excluded.confidence,
            created_by=excluded.created_by
        """,
        (
            rel.id,
            rel.source_element_id,
            rel.target_element_id,
            rel.archimate_type,
            rel.description,
            rel.source_spec,
            rel.evidence,
            rel.confidence,
            rel.created_at,
            rel.created_by,
        ),
    )
    await conn.commit()


async def upsert_capability(conn: aiosqlite.Connection, cap: Capability) -> None:
    """Insert or replace a capability in the registry.

    Args:
        conn: Open database connection.
        cap: Capability to upsert.
    """
    await conn.execute(
        """
        INSERT INTO capabilities (id, name, parent_id, level, domain, maturity, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            parent_id=excluded.parent_id,
            level=excluded.level,
            domain=excluded.domain,
            maturity=excluded.maturity,
            description=excluded.description
        """,
        (cap.id, cap.name, cap.parent_id, cap.level, cap.domain, cap.maturity, cap.description),
    )
    await conn.commit()


async def get_element(conn: aiosqlite.Connection, element_id: str) -> Element | None:
    """Retrieve a single element by ID.

    Args:
        conn: Open database connection.
        element_id: The element's primary key.

    Returns:
        Element if found, None otherwise.
    """
    async with conn.execute("SELECT * FROM elements WHERE id = ?", (element_id,)) as cursor:
        row = await cursor.fetchone()
    return _row_to_element(row) if row else None


async def search_elements(
    conn: aiosqlite.Connection,
    query: str,
    domain: str | None = None,
    archimate_type: str | None = None,
) -> list[Element]:
    """Search elements by name or description with optional filters.

    Args:
        conn: Open database connection.
        query: Search term matched against name and description.
        domain: Optional domain filter.
        archimate_type: Optional ArchiMate type filter.

    Returns:
        List of matching elements.
    """
    conditions = ["(name LIKE ? OR description LIKE ?)"]
    params: list[object] = [f"%{query}%", f"%{query}%"]

    if domain:
        conditions.append("domain = ?")
        params.append(domain)
    if archimate_type:
        conditions.append("archimate_type = ?")
        params.append(archimate_type)

    sql = f"SELECT * FROM elements WHERE {' AND '.join(conditions)} ORDER BY name"
    async with conn.execute(sql, params) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_element(r) for r in rows]


async def list_capabilities(
    conn: aiosqlite.Connection,
    parent_id: str | None = None,
    max_level: int | None = None,
) -> list[Capability]:
    """List capabilities with optional filters.

    Args:
        conn: Open database connection.
        parent_id: Filter to children of this parent (None = root level).
        max_level: Maximum hierarchy depth to return.

    Returns:
        List of matching capabilities.
    """
    conditions: list[str] = []
    params: list[object] = []

    if parent_id is not None:
        conditions.append("parent_id = ?")
        params.append(parent_id)
    else:
        conditions.append("parent_id IS NULL")

    if max_level is not None:
        conditions.append("level <= ?")
        params.append(max_level)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM capabilities {where} ORDER BY level, name"
    async with conn.execute(sql, params) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_capability(r) for r in rows]


async def find_orphan_elements(conn: aiosqlite.Connection) -> list[Element]:
    """Return elements not linked to any capability.

    Args:
        conn: Open database connection.

    Returns:
        List of orphan elements.
    """
    async with conn.execute("SELECT * FROM v_orphan_elements ORDER BY domain, name") as cursor:
        rows = await cursor.fetchall()
    return [_row_to_element(r) for r in rows]


async def domain_summary(
    conn: aiosqlite.Connection,
    domain: str | None = None,
) -> list[dict[str, object]]:
    """Return element counts grouped by domain, type, and status.

    Args:
        conn: Open database connection.
        domain: Optional domain filter.

    Returns:
        List of dicts with domain, archimate_type, status, count keys.
    """
    if domain:
        sql = "SELECT * FROM v_domain_summary WHERE domain = ? ORDER BY domain, archimate_type"
        params: tuple[object, ...] = (domain,)
    else:
        sql = "SELECT * FROM v_domain_summary ORDER BY domain, archimate_type"
        params = ()

    async with conn.execute(sql, params) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def link_element_to_capability(
    conn: aiosqlite.Connection,
    element_id: str,
    capability_id: str,
    relationship_type: str = "realizes",
) -> None:
    """Link an element to a capability.

    Args:
        conn: Open database connection.
        element_id: The element ID to link.
        capability_id: The capability ID to link to.
        relationship_type: ArchiMate relationship type (default: 'realizes').
    """
    await conn.execute(
        """
        INSERT INTO element_capabilities (element_id, capability_id, relationship_type)
        VALUES (?, ?, ?)
        ON CONFLICT(element_id, capability_id) DO UPDATE SET
            relationship_type=excluded.relationship_type
        """,
        (element_id, capability_id, relationship_type),
    )
    await conn.commit()
