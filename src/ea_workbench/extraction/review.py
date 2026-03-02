"""Staging review workflow helpers — approve, reject, and list pending extractions."""

import logging
import os
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ea_workbench.registry.migration import (
    BUSINESS_TYPES,
    IMPL_TYPES,
    MOTIVATION_TYPES,
    SOLUTION_TYPES,
    STRATEGY_TYPES,
)

logger = logging.getLogger(__name__)


def _route_to_concern_table(archimate_type: str) -> str:
    """Return the Option C concern table name for an ArchiMate element type.

    Args:
        archimate_type: ArchiMate element type string.

    Returns:
        Table name: motivation|strategy|business_architecture|solution_architecture|implementation|elements
    """
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
    return "elements"  # fallback to legacy table


async def approve_staged_entities(staging_file: str, workspace: str) -> int:
    """Move a staging file to the approved directory.

    Args:
        staging_file: Path to the staging YAML file to approve.
        workspace: Path to the PFC workspace root.

    Returns:
        Number of files moved (1 on success, 0 if already absent).

    Raises:
        FileNotFoundError: If staging_file does not exist.
    """
    if not os.path.exists(staging_file):
        raise FileNotFoundError(f"Staging file not found: {staging_file}")

    approved_dir = os.path.join(workspace, ".staging", "approved")
    os.makedirs(approved_dir, exist_ok=True)

    filename = os.path.basename(staging_file)
    dest = os.path.join(approved_dir, filename)
    shutil.move(staging_file, dest)
    logger.info("Approved: %s → %s", staging_file, dest)
    return 1


async def reject_staged_entities(staging_file: str) -> None:
    """Delete a staging file (reject the extraction).

    Args:
        staging_file: Path to the staging YAML file to delete.

    Raises:
        FileNotFoundError: If staging_file does not exist.
    """
    if not os.path.exists(staging_file):
        raise FileNotFoundError(f"Staging file not found: {staging_file}")

    os.remove(staging_file)
    logger.info("Rejected and deleted: %s", staging_file)


async def approve_to_registry(staging_file: str, workspace: str, db_path: str) -> int:
    """Move staging file to approved/ AND upsert entities into the correct concern tables.

    Routes each entity to its target Option C concern table based on archimate_type.
    Falls back to the legacy elements table for unknown types.

    Args:
        staging_file: Path to the staging YAML file to approve.
        workspace: Path to the PFC workspace root.
        db_path: Path to the element registry SQLite database.

    Returns:
        Count of elements upserted into the registry.

    Raises:
        FileNotFoundError: If staging_file does not exist.
    """
    from ea_workbench.models.implementation import ImplementationElement
    from ea_workbench.models.motivation import MotivationElement
    from ea_workbench.models.solution_architecture import SolutionArchElement
    from ea_workbench.models.strategy import StrategyElement
    from ea_workbench.models.elements import Element
    from ea_workbench.registry.db import get_connection, initialise_schema
    from ea_workbench.registry.queries import (
        upsert_element,
        upsert_implementation,
        upsert_motivation,
        upsert_solution_arch,
        upsert_strategy,
    )

    if not os.path.exists(staging_file):
        raise FileNotFoundError(f"Staging file not found: {staging_file}")

    # Read entities before moving the file
    with open(staging_file, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    entities_raw = data.get("entities", []) if isinstance(data, dict) else []

    # Move to approved/
    await approve_staged_entities(staging_file, workspace)

    if not entities_raw:
        return 0

    await initialise_schema(db_path)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    upserted = 0

    async with get_connection(db_path) as conn:
        for raw in entities_raw:
            if not isinstance(raw, dict):
                continue
            name = raw.get("name", "")
            if not name:
                continue

            archimate_type = raw.get("archimate_type", "application-component")
            target_table = _route_to_concern_table(archimate_type)
            entity_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"element:{name}"))
            domain_id = raw.get("domain_id") or raw.get("domain", "unknown")
            status = raw.get("status", "proposed")
            description = raw.get("description") or ""
            confidence = float(raw.get("confidence", 0.8))

            try:
                if target_table == "motivation":
                    element = MotivationElement(
                        id=entity_id,
                        name=name,
                        archimate_type=archimate_type,
                        domain_id=domain_id,
                        status=status,
                        description=description,
                        confidence=confidence,
                    )
                    await upsert_motivation(conn, element)

                elif target_table == "strategy":
                    element = StrategyElement(
                        id=entity_id,
                        name=name,
                        archimate_type=archimate_type,
                        domain_id=domain_id,
                        status=status,
                        description=description,
                        confidence=confidence,
                    )
                    await upsert_strategy(conn, element)

                elif target_table == "solution_architecture":
                    element = SolutionArchElement(
                        id=entity_id,
                        name=name,
                        archimate_type=archimate_type,
                        domain_id=domain_id,
                        status=status,
                        description=description,
                        confidence=confidence,
                    )
                    await upsert_solution_arch(conn, element)

                elif target_table == "implementation":
                    element = ImplementationElement(
                        id=entity_id,
                        name=name,
                        archimate_type=archimate_type,
                        domain_id=domain_id,
                        status=status,
                        description=description,
                    )
                    await upsert_implementation(conn, element)

                else:
                    # Legacy fallback: elements table
                    element = Element(
                        id=entity_id,
                        name=name,
                        archimate_type=archimate_type,
                        domain=domain_id,
                        status=status,
                        description=description or None,
                        source_spec=raw.get("source_spec"),
                        source_line=raw.get("source_line"),
                        created_at=now,
                        updated_at=now,
                        created_by="staging-review",
                        confidence=confidence,
                    )
                    await upsert_element(conn, element)

                upserted += 1

            except Exception as exc:
                logger.warning("Could not upsert entity '%s': %s", name, exc)

    logger.info("Approved %s: %d element(s) upserted to registry", staging_file, upserted)
    return upserted


async def list_pending(workspace: str) -> dict[str, int]:
    """Count pending staging files by directory.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Dict mapping directory name to file count.
    """
    staging_base = os.path.join(workspace, ".staging")
    subdirs = ["entities", "relationships", "work", "sessions"]
    result: dict[str, int] = {}

    for subdir in subdirs:
        dirpath = os.path.join(staging_base, subdir)
        if os.path.exists(dirpath):
            yaml_files = [
                f for f in os.listdir(dirpath)
                if f.endswith(".yaml") and not f.startswith(".")
            ]
            result[subdir] = len(yaml_files)
        else:
            result[subdir] = 0

    return result
