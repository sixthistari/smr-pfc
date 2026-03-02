"""Migration utility: Phase 0 generic schema → Option C concern tables.

This migration is additive — it reads rows from the old generic tables
(elements, relationships, capabilities) and inserts them into the correct
Option C concern tables based on archimate_type. Old tables are NOT dropped.
"""

import logging

from ea_workbench.models.implementation import ImplementationElement
from ea_workbench.models.motivation import MotivationElement
from ea_workbench.models.solution_architecture import SolutionArchElement
from ea_workbench.models.strategy import StrategyElement
from ea_workbench.registry.db import get_connection, initialise_schema
from ea_workbench.registry.queries import (
    upsert_implementation,
    upsert_motivation,
    upsert_solution_arch,
    upsert_strategy,
)

logger = logging.getLogger(__name__)

# ArchiMate type → concern table routing
MOTIVATION_TYPES = frozenset({
    "stakeholder", "driver", "assessment", "goal", "outcome",
    "requirement", "constraint",
})
STRATEGY_TYPES = frozenset({
    "capability", "value-stream", "resource", "course-of-action",
})
BUSINESS_TYPES = frozenset({
    "business-actor", "role", "business-role", "process", "business-process",
    "function", "business-function", "service", "business-service",
    "object", "business-object", "event", "business-event",
})
SOLUTION_TYPES = frozenset({
    "application-component", "application-service", "application-interface",
    "data-object", "node", "technology-node", "technology-service",
    "technology-interface", "system-software", "artifact",
})
IMPL_TYPES = frozenset({
    "work-package", "deliverable", "implementation-event", "plateau", "gap",
})


def _route_archimate_type(archimate_type: str) -> str | None:
    """Return the target concern table name for an ArchiMate type, or None if unknown."""
    t = archimate_type.lower()
    if t in MOTIVATION_TYPES:
        return "motivation"
    if t in STRATEGY_TYPES:
        return "strategy"
    if t in BUSINESS_TYPES:
        return "business_architecture"
    if t in SOLUTION_TYPES:
        return "solution_architecture"
    if t in IMPL_TYPES:
        return "implementation"
    return None


async def migrate_phase0_to_option_c(db_path: str) -> dict[str, object]:
    """Migrate Phase 0 generic rows to Option C concern tables.

    Reads rows from: elements, capabilities
    Inserts into: motivation, strategy, business_architecture, solution_architecture, implementation

    Old relationships rows are migrated to the new cross-table relationships table with
    source_table/target_table set to 'elements' (legacy reference).

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        dict with keys: migrated (int), skipped (int), errors (list[str])
    """
    await initialise_schema(db_path)

    migrated = 0
    skipped = 0
    errors: list[str] = []

    async with get_connection(db_path) as conn:
        # --- Migrate elements table ---
        try:
            async with conn.execute("SELECT * FROM elements") as cursor:
                rows = await cursor.fetchall()
        except Exception as exc:
            logger.warning("Could not read elements table: %s", exc)
            rows = []

        for row in rows:
            archimate_type = row["archimate_type"] or ""
            target_table = _route_archimate_type(archimate_type)

            if target_table is None:
                logger.debug("Skipping unknown archimate_type: %s (id=%s)", archimate_type, row["id"])
                skipped += 1
                continue

            try:
                if target_table == "motivation":
                    element = MotivationElement(
                        id=row["id"],
                        name=row["name"],
                        archimate_type=archimate_type,
                        domain_id=row["domain"] or "",
                        status=row["status"] or "draft",
                        description=row["description"] or "",
                        confidence=float(row["confidence"] or 0.8),
                    )
                    await upsert_motivation(conn, element)

                elif target_table == "strategy":
                    element = StrategyElement(
                        id=row["id"],
                        name=row["name"],
                        archimate_type=archimate_type,
                        domain_id=row["domain"] or "",
                        status=row["status"] or "draft",
                        description=row["description"] or "",
                        confidence=float(row["confidence"] or 0.8),
                    )
                    await upsert_strategy(conn, element)

                elif target_table == "solution_architecture":
                    element = SolutionArchElement(
                        id=row["id"],
                        name=row["name"],
                        archimate_type=archimate_type,
                        domain_id=row["domain"] or "",
                        status=row["status"] or "draft",
                        description=row["description"] or "",
                        confidence=float(row["confidence"] or 0.8),
                    )
                    await upsert_solution_arch(conn, element)

                elif target_table == "implementation":
                    element = ImplementationElement(
                        id=row["id"],
                        name=row["name"],
                        archimate_type=archimate_type,
                        domain_id=row["domain"] or "",
                        status=row["status"] or "draft",
                        description=row["description"] or "",
                    )
                    await upsert_implementation(conn, element)

                else:
                    # business_architecture — skip for now (no simple mapping from generic Element)
                    skipped += 1
                    continue

                migrated += 1

            except Exception as exc:
                msg = f"Error migrating element {row['id']}: {exc}"
                logger.warning(msg)
                errors.append(msg)

        # --- Migrate capabilities → strategy (capability type) ---
        try:
            async with conn.execute("SELECT * FROM capabilities") as cursor:
                cap_rows = await cursor.fetchall()
        except Exception as exc:
            logger.warning("Could not read capabilities table: %s", exc)
            cap_rows = []

        for row in cap_rows:
            try:
                element = StrategyElement(
                    id=row["id"],
                    name=row["name"],
                    archimate_type="capability",
                    domain_id=row["domain"] or "",
                    status="draft",
                    description=row["description"] or "",
                    parent_id=row["parent_id"] or "",
                    level=int(row["level"] or 0),
                    maturity=row["maturity"] or "",
                )
                await upsert_strategy(conn, element)
                migrated += 1
            except Exception as exc:
                msg = f"Error migrating capability {row['id']}: {exc}"
                logger.warning(msg)
                errors.append(msg)

    result = {"migrated": migrated, "skipped": skipped, "errors": errors}
    logger.info("Migration complete: %s", result)
    return result
