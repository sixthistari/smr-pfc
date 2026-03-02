"""Tests for entity and relationship staging file writer."""

import os
from pathlib import Path

import pytest
import yaml

from ea_workbench.extraction.extractor import write_entity_staging
from ea_workbench.models.extraction import StagedEntity, StagedRelationship


@pytest.fixture
def workspace(tmp_path: Path) -> str:
    """Create a minimal workspace with .staging directories."""
    (tmp_path / ".staging" / "entities").mkdir(parents=True)
    (tmp_path / ".staging" / "relationships").mkdir(parents=True)
    return str(tmp_path)


async def test_write_entity_staging_creates_file(workspace: str) -> None:
    """write_entity_staging creates a YAML file in .staging/entities/."""
    entities = [
        StagedEntity(
            name="Document Intelligence Pipeline",
            archimate_type="application-component",
            domain="knowledge-infrastructure",
            confidence=0.9,
        )
    ]
    path = await write_entity_staging(
        entities=entities,
        relationships=[],
        agent_id="adr-generator",
        run_id="test001",
        source="tests/fixtures/transcripts/sample.md",
        workspace=workspace,
    )
    assert os.path.exists(path)
    assert "adr-generator_test001" in path

    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert data["metadata"]["extracted_by"] == "adr-generator"
    assert len(data["entities"]) == 1


async def test_write_entity_staging_filters_invalid(workspace: str) -> None:
    """write_entity_staging skips entities with invalid ArchiMate types."""
    entities = [
        StagedEntity(
            name="Valid Entity",
            archimate_type="application-component",
            domain="knowledge-infrastructure",
            confidence=0.9,
        ),
        StagedEntity(
            name="Invalid Type Entity",
            archimate_type="not-a-real-type",
            domain="safety",
            confidence=0.8,
        ),
    ]
    path = await write_entity_staging(
        entities=entities,
        relationships=[],
        agent_id="test-agent",
        run_id="test002",
        source="test.md",
        workspace=workspace,
    )
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert len(data["entities"]) == 1
    assert data["entities"][0]["name"] == "Valid Entity"


async def test_write_entity_staging_filters_low_confidence(workspace: str) -> None:
    """write_entity_staging skips entities with confidence below 0.5."""
    entities = [
        StagedEntity(
            name="Low Confidence Entity",
            archimate_type="data-object",
            domain="safety",
            confidence=0.3,
        ),
        StagedEntity(
            name="High Confidence Entity",
            archimate_type="data-object",
            domain="safety",
            confidence=0.8,
        ),
    ]
    path = await write_entity_staging(
        entities=entities,
        relationships=[],
        agent_id="test-agent",
        run_id="test003",
        source="test.md",
        workspace=workspace,
    )
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert len(data["entities"]) == 1
    assert data["entities"][0]["name"] == "High Confidence Entity"


async def test_write_entity_staging_with_relationships(workspace: str) -> None:
    """write_entity_staging also writes relationship file when relationships provided."""
    entities = [
        StagedEntity(
            name="Pipeline",
            archimate_type="application-component",
            domain="knowledge-infrastructure",
            confidence=0.9,
        )
    ]
    relationships = [
        StagedRelationship(
            source_element="Pipeline",
            target_element="Store",
            archimate_type="serving-relationship",
            confidence=0.7,
        )
    ]
    await write_entity_staging(
        entities=entities,
        relationships=relationships,
        agent_id="test-agent",
        run_id="test004",
        source="test.md",
        workspace=workspace,
    )
    rel_path = os.path.join(workspace, ".staging", "relationships", "test-agent_test004.yaml")
    assert os.path.exists(rel_path)


async def test_write_entity_staging_empty_entities(workspace: str) -> None:
    """write_entity_staging handles empty entity list gracefully."""
    path = await write_entity_staging(
        entities=[],
        relationships=[],
        agent_id="test-agent",
        run_id="test005",
        source="test.md",
        workspace=workspace,
    )
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert data["entities"] == []
