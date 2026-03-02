"""Entity and relationship staging file writer."""

import logging
import os
from datetime import UTC, datetime

import yaml

from ea_workbench.extraction.schemas import ValidatedStagedEntity, ValidatedStagedRelationship
from ea_workbench.models.extraction import (
    ExtractionFile,
    ExtractionMetadata,
    RelationshipFile,
    StagedEntity,
    StagedRelationship,
)

logger = logging.getLogger(__name__)


async def write_entity_staging(
    entities: list[StagedEntity],
    relationships: list[StagedRelationship],
    agent_id: str,
    run_id: str,
    source: str,
    workspace: str,
) -> str:
    """Validate and write entity staging YAML files.

    Invalid entities are logged and skipped (run status remains 'completed'
    unless ALL entities are invalid, in which case caller should set 'partial').

    Args:
        entities: List of raw staged entities to validate and write.
        relationships: List of raw staged relationships to validate and write.
        agent_id: The agent that produced these extractions.
        run_id: The run ID.
        source: The source document path.
        workspace: Path to the PFC workspace root.

    Returns:
        Path to the written entity staging file.
    """
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    metadata = ExtractionMetadata(
        extracted_by=agent_id,
        run_id=run_id,
        timestamp=timestamp,
        source=source,
    )

    # Validate entities, skip invalid ones
    valid_entities: list[StagedEntity] = []
    for raw in entities:
        try:
            validated = ValidatedStagedEntity.model_validate(raw.model_dump())
            valid_entities.append(validated)
        except Exception as exc:
            logger.warning("Skipping invalid entity '%s': %s", raw.name, exc)

    # Validate relationships, skip invalid ones
    valid_relationships: list[StagedRelationship] = []
    for raw in relationships:
        try:
            validated = ValidatedStagedRelationship.model_validate(raw.model_dump())
            valid_relationships.append(validated)
        except Exception as exc:
            logger.warning(
                "Skipping invalid relationship '%s→%s': %s",
                raw.source_element,
                raw.target_element,
                exc,
            )

    staging_base = os.path.join(workspace, ".staging")
    entities_dir = os.path.join(staging_base, "entities")
    relationships_dir = os.path.join(staging_base, "relationships")
    os.makedirs(entities_dir, exist_ok=True)
    os.makedirs(relationships_dir, exist_ok=True)

    filename = f"{agent_id}_{run_id}.yaml"

    # Write entity file
    entity_file = ExtractionFile(metadata=metadata, entities=valid_entities)
    entity_path = os.path.join(entities_dir, filename)
    with open(entity_path, "w", encoding="utf-8") as fh:
        yaml.dump(entity_file.model_dump(), fh, default_flow_style=False, allow_unicode=True)

    # Write relationship file if any
    if valid_relationships:
        rel_file = RelationshipFile(metadata=metadata, relationships=valid_relationships)
        rel_path = os.path.join(relationships_dir, filename)
        with open(rel_path, "w", encoding="utf-8") as fh:
            yaml.dump(rel_file.model_dump(), fh, default_flow_style=False, allow_unicode=True)
        logger.info("Staged %d relationships to %s", len(valid_relationships), rel_path)

    logger.info("Staged %d entities to %s", len(valid_entities), entity_path)
    return entity_path
