"""Common query functions for the element registry — legacy + Option C concern-table upserts."""

import json
import logging

import aiosqlite

from ea_workbench.models.business_architecture import BusinessArchElement, ProcessStep
from ea_workbench.models.domains import Domain
from ea_workbench.models.elements import Capability, Element, Relationship
from ea_workbench.models.governance import GovernanceControl, QualityEvaluation
from ea_workbench.models.implementation import ImplementationElement
from ea_workbench.models.motivation import MotivationElement
from ea_workbench.models.portfolio import (
    DeploymentTarget,
    Solution,
    SolutionComponent,
    SolutionDeployment,
)
from ea_workbench.models.solution_architecture import SolutionArchElement
from ea_workbench.models.strategy import StrategyElement
from ea_workbench.models.work import StagingItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Legacy helpers (backward compatible)
# ---------------------------------------------------------------------------


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
    """Insert or replace an element in the legacy registry."""
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


async def upsert_capability(conn: aiosqlite.Connection, cap: Capability) -> None:
    """Insert or replace a capability in the legacy registry."""
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

    Checks the legacy elements table first (full fields including confidence),
    then falls back to element_registry_view which covers all Option C concern tables.

    Args:
        conn: Open database connection.
        element_id: The element's primary key.

    Returns:
        Element if found (with available fields), None otherwise.
    """
    # Try legacy elements table first (has full field set)
    async with conn.execute("SELECT * FROM elements WHERE id = ?", (element_id,)) as cursor:
        row = await cursor.fetchone()
    if row:
        return _row_to_element(row)

    # Fall back to element_registry_view (Option C concern tables)
    async with conn.execute(
        "SELECT * FROM element_registry_view WHERE id = ?", (element_id,)
    ) as cursor:
        view_row = await cursor.fetchone()
    if view_row is None:
        return None

    return Element(
        id=view_row["id"],
        name=view_row["name"],
        archimate_type=view_row["archimate_type"],
        domain=view_row["domain"] or "",
        status=view_row["status"] or "proposed",
        description=view_row["description"],
    )


async def search_elements(
    conn: aiosqlite.Connection,
    query: str,
    domain: str | None = None,
    archimate_type: str | None = None,
) -> list[Element]:
    """Search elements by name or description with optional filters (legacy table)."""
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
    """List capabilities with optional filters."""
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
    """Return elements not linked to any capability."""
    async with conn.execute("SELECT * FROM v_orphan_elements ORDER BY domain, name") as cursor:
        rows = await cursor.fetchall()
    return [_row_to_element(r) for r in rows]


async def domain_summary(
    conn: aiosqlite.Connection,
    domain: str | None = None,
) -> list[dict[str, object]]:
    """Return element counts grouped by domain, type, and status (legacy view)."""
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
    """Link a legacy element to a capability."""
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


# ---------------------------------------------------------------------------
# Option C — cross-table relationship upsert
# ---------------------------------------------------------------------------


async def upsert_relationship(conn: aiosqlite.Connection, rel: Relationship) -> None:
    """Insert or replace a cross-table relationship."""
    await conn.execute(
        """
        INSERT INTO relationships
            (id, source_table, source_id, target_table, target_id,
             archimate_type, description, evidence, confidence, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            source_table=excluded.source_table,
            source_id=excluded.source_id,
            target_table=excluded.target_table,
            target_id=excluded.target_id,
            archimate_type=excluded.archimate_type,
            description=excluded.description,
            evidence=excluded.evidence,
            confidence=excluded.confidence,
            created_by=excluded.created_by
        """,
        (
            rel.id,
            rel.source_table,
            rel.source_id,
            rel.target_table,
            rel.target_id,
            rel.archimate_type,
            rel.description,
            rel.evidence,
            rel.confidence,
            rel.created_by,
            rel.created_at,
        ),
    )
    await conn.commit()


async def validate_relationship(
    conn: aiosqlite.Connection,
    source_type: str,
    target_type: str,
    rel_type: str,
) -> bool:
    """Check whether a relationship pair is permitted by the ArchiMate metamodel."""
    async with conn.execute(
        "SELECT 1 FROM valid_relationships WHERE source_archimate_type=? "
        "AND target_archimate_type=? AND relationship_type=?",
        (source_type, target_type, rel_type),
    ) as cursor:
        row = await cursor.fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Option C — concern-table upserts
# ---------------------------------------------------------------------------


async def upsert_domain(conn: aiosqlite.Connection, domain: Domain) -> str:
    """Insert or replace a domain record. Returns the domain ID."""
    await conn.execute(
        """
        INSERT INTO domains
            (id, name, description, priority, maturity, autonomy_ceiling,
             track_default, spec_coverage, owner_role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            description=excluded.description,
            priority=excluded.priority,
            maturity=excluded.maturity,
            autonomy_ceiling=excluded.autonomy_ceiling,
            track_default=excluded.track_default,
            spec_coverage=excluded.spec_coverage,
            owner_role=excluded.owner_role
        """,
        (
            domain.id, domain.name, domain.description, domain.priority,
            domain.maturity, domain.autonomy_ceiling, domain.track_default,
            domain.spec_coverage, domain.owner_role,
        ),
    )
    await conn.commit()
    return domain.id


async def upsert_motivation(conn: aiosqlite.Connection, element: MotivationElement) -> str:
    """Insert or replace a motivation layer element. Returns the element ID."""
    await conn.execute(
        """
        INSERT INTO motivation
            (id, name, archimate_type, domain_id, status, description, confidence,
             role, influence_level, driver_category, evidence, impact, horizon,
             requirement_type, category, threshold, target, acceptance_criteria,
             solution_id, engagement_ref)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            archimate_type=excluded.archimate_type,
            domain_id=excluded.domain_id,
            status=excluded.status,
            description=excluded.description,
            confidence=excluded.confidence,
            role=excluded.role,
            influence_level=excluded.influence_level,
            driver_category=excluded.driver_category,
            evidence=excluded.evidence,
            impact=excluded.impact,
            horizon=excluded.horizon,
            requirement_type=excluded.requirement_type,
            category=excluded.category,
            threshold=excluded.threshold,
            target=excluded.target,
            acceptance_criteria=excluded.acceptance_criteria,
            solution_id=excluded.solution_id,
            engagement_ref=excluded.engagement_ref
        """,
        (
            element.id, element.name, element.archimate_type, element.domain_id,
            element.status, element.description, element.confidence,
            element.role, element.influence_level, element.driver_category,
            element.evidence, element.impact, element.horizon,
            element.requirement_type, element.category, element.threshold,
            element.target, json.dumps(element.acceptance_criteria),
            element.solution_id, element.engagement_ref,
        ),
    )
    await conn.commit()
    return element.id


async def upsert_strategy(conn: aiosqlite.Connection, element: StrategyElement) -> str:
    """Insert or replace a strategy layer element. Returns the element ID."""
    await conn.execute(
        """
        INSERT INTO strategy
            (id, name, archimate_type, domain_id, status, description, confidence,
             parent_id, level, maturity, stages, value_proposition, horizon, traces_to_goal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            archimate_type=excluded.archimate_type,
            domain_id=excluded.domain_id,
            status=excluded.status,
            description=excluded.description,
            confidence=excluded.confidence,
            parent_id=excluded.parent_id,
            level=excluded.level,
            maturity=excluded.maturity,
            stages=excluded.stages,
            value_proposition=excluded.value_proposition,
            horizon=excluded.horizon,
            traces_to_goal=excluded.traces_to_goal
        """,
        (
            element.id, element.name, element.archimate_type, element.domain_id,
            element.status, element.description, element.confidence,
            element.parent_id or None, element.level, element.maturity,
            json.dumps(element.stages), element.value_proposition,
            element.horizon, element.traces_to_goal,
        ),
    )
    await conn.commit()
    return element.id


async def upsert_business_arch(conn: aiosqlite.Connection, element: BusinessArchElement) -> str:
    """Insert or replace a business architecture element. Returns the element ID."""
    await conn.execute(
        """
        INSERT INTO business_architecture
            (id, name, archimate_type, domain_id, status, description, confidence,
             parent_id, actor_type, agent_augmented, augmentation_level,
             track, governance_level, trigger_event, process_owner_id,
             service_type, has_authority_scoring)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            archimate_type=excluded.archimate_type,
            domain_id=excluded.domain_id,
            status=excluded.status,
            description=excluded.description,
            confidence=excluded.confidence,
            parent_id=excluded.parent_id,
            actor_type=excluded.actor_type,
            agent_augmented=excluded.agent_augmented,
            augmentation_level=excluded.augmentation_level,
            track=excluded.track,
            governance_level=excluded.governance_level,
            trigger_event=excluded.trigger_event,
            process_owner_id=excluded.process_owner_id,
            service_type=excluded.service_type,
            has_authority_scoring=excluded.has_authority_scoring
        """,
        (
            element.id, element.name, element.archimate_type, element.domain_id,
            element.status, element.description, element.confidence,
            element.parent_id or None, element.actor_type,
            element.agent_augmented, element.augmentation_level,
            element.track, element.governance_level, element.trigger_event,
            element.process_owner_id, element.service_type, element.has_authority_scoring,
        ),
    )
    await conn.commit()
    return element.id


async def upsert_process_step(conn: aiosqlite.Connection, step: ProcessStep) -> str:
    """Insert or replace a process step. Returns the step ID."""
    await conn.execute(
        """
        INSERT INTO process_steps
            (id, process_id, sequence, name, step_type, role_id, agent_id,
             agent_autonomy, description, input_objects, output_objects,
             approval_required, track_crossing)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            process_id=excluded.process_id,
            sequence=excluded.sequence,
            name=excluded.name,
            step_type=excluded.step_type,
            role_id=excluded.role_id,
            agent_id=excluded.agent_id,
            agent_autonomy=excluded.agent_autonomy,
            description=excluded.description,
            input_objects=excluded.input_objects,
            output_objects=excluded.output_objects,
            approval_required=excluded.approval_required,
            track_crossing=excluded.track_crossing
        """,
        (
            step.id, step.process_id, step.sequence, step.name, step.step_type,
            step.role_id, step.agent_id, step.agent_autonomy, step.description,
            json.dumps(step.input_objects), json.dumps(step.output_objects),
            step.approval_required, step.track_crossing,
        ),
    )
    await conn.commit()
    return step.id


async def upsert_solution_arch(conn: aiosqlite.Connection, element: SolutionArchElement) -> str:
    """Insert or replace a solution architecture element. Returns the element ID."""
    await conn.execute(
        """
        INSERT INTO solution_architecture
            (id, name, archimate_type, domain_id, status, description, confidence,
             version, deployment_status, is_agent, default_autonomy, default_track,
             knowledge_base_ref, promoted_to_actor, is_knowledge_store, store_type,
             config_path, fallback_ref, ingestion_pipeline_ref,
             platform, environment, provider, region, ga_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            archimate_type=excluded.archimate_type,
            domain_id=excluded.domain_id,
            status=excluded.status,
            description=excluded.description,
            confidence=excluded.confidence,
            version=excluded.version,
            deployment_status=excluded.deployment_status,
            is_agent=excluded.is_agent,
            default_autonomy=excluded.default_autonomy,
            default_track=excluded.default_track,
            knowledge_base_ref=excluded.knowledge_base_ref,
            promoted_to_actor=excluded.promoted_to_actor,
            is_knowledge_store=excluded.is_knowledge_store,
            store_type=excluded.store_type,
            config_path=excluded.config_path,
            fallback_ref=excluded.fallback_ref,
            ingestion_pipeline_ref=excluded.ingestion_pipeline_ref,
            platform=excluded.platform,
            environment=excluded.environment,
            provider=excluded.provider,
            region=excluded.region,
            ga_status=excluded.ga_status
        """,
        (
            element.id, element.name, element.archimate_type, element.domain_id,
            element.status, element.description, element.confidence,
            element.version, element.deployment_status, element.is_agent,
            element.default_autonomy, element.default_track, element.knowledge_base_ref,
            element.promoted_to_actor, element.is_knowledge_store, element.store_type,
            element.config_path, element.fallback_ref, element.ingestion_pipeline_ref,
            element.platform, element.environment, element.provider, element.region,
            element.ga_status,
        ),
    )
    await conn.commit()
    return element.id


async def upsert_implementation(conn: aiosqlite.Connection, element: ImplementationElement) -> str:
    """Insert or replace an implementation element. Returns the element ID."""
    await conn.execute(
        """
        INSERT INTO implementation
            (id, name, archimate_type, domain_id, status, description,
             solution_id, phase, target_date, plateau_description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            archimate_type=excluded.archimate_type,
            domain_id=excluded.domain_id,
            status=excluded.status,
            description=excluded.description,
            solution_id=excluded.solution_id,
            phase=excluded.phase,
            target_date=excluded.target_date,
            plateau_description=excluded.plateau_description
        """,
        (
            element.id, element.name, element.archimate_type, element.domain_id,
            element.status, element.description, element.solution_id,
            element.phase, element.target_date, element.plateau_description,
        ),
    )
    await conn.commit()
    return element.id


async def upsert_staging_item(conn: aiosqlite.Connection, item: StagingItem) -> str:
    """Insert or replace a staging item. Returns the item ID."""
    await conn.execute(
        """
        INSERT INTO staging_items
            (id, entity_type, entity_data, target_table, source_type,
             source_id, confidence, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            entity_type=excluded.entity_type,
            entity_data=excluded.entity_data,
            target_table=excluded.target_table,
            source_type=excluded.source_type,
            source_id=excluded.source_id,
            confidence=excluded.confidence,
            status=excluded.status
        """,
        (
            item.id, item.entity_type, json.dumps(item.entity_data),
            item.target_table, item.source_type, item.source_id,
            item.confidence, item.status,
        ),
    )
    await conn.commit()
    return item.id


# Routing map: entity_type → upsert function
_TABLE_MAP: dict[str, object] = {}


def _get_table_map() -> dict:
    """Lazy-initialise routing map (avoids circular import at module load)."""
    if not _TABLE_MAP:
        _TABLE_MAP.update({
            "motivation": upsert_motivation,
            "strategy": upsert_strategy,
            "business_architecture": upsert_business_arch,
            "solution_architecture": upsert_solution_arch,
            "implementation": upsert_implementation,
        })
    return _TABLE_MAP


async def approve_staging_item(conn: aiosqlite.Connection, item_id: str) -> str:
    """Route a staged item to its target concern table and mark it approved.

    Reads the staging item, constructs the appropriate Pydantic model,
    calls the matching upsert function, and updates the item status.

    Args:
        conn: Open database connection.
        item_id: Primary key of the staging_items row to approve.

    Returns:
        The ID of the upserted concern-table element.

    Raises:
        ValueError: If the item is not found or the entity_type is unknown.
    """
    async with conn.execute(
        "SELECT * FROM staging_items WHERE id = ?", (item_id,)
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        raise ValueError(f"Staging item not found: {item_id}")

    entity_type = row["entity_type"]
    entity_data = json.loads(row["entity_data"])
    table_map = _get_table_map()

    if entity_type not in table_map:
        raise ValueError(f"Unknown entity_type: {entity_type}")

    model_map = {
        "motivation": MotivationElement,
        "strategy": StrategyElement,
        "business_architecture": BusinessArchElement,
        "solution_architecture": SolutionArchElement,
        "implementation": ImplementationElement,
    }
    model_cls = model_map[entity_type]
    element = model_cls.model_validate(entity_data)
    upsert_fn = table_map[entity_type]
    element_id = await upsert_fn(conn, element)  # type: ignore[operator]

    # Mark staging item as approved
    await conn.execute(
        "UPDATE staging_items SET status='approved' WHERE id=?", (item_id,)
    )
    await conn.commit()
    return element_id
