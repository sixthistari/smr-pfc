"""Tests for extraction staging models."""

import pytest

from ea_workbench.models.extraction import (
    ExtractionFile,
    ExtractionMetadata,
    RelationshipFile,
    StagedEntity,
    StagedRelationship,
)


def test_staged_entity_valid() -> None:
    """StagedEntity validates with required fields."""
    e = StagedEntity(
        name="Document Intelligence Pipeline",
        archimate_type="application-component",
        domain="knowledge-infrastructure",
        confidence=0.9,
    )
    assert e.status == "proposed"
    assert e.confidence == 0.9


def test_staged_relationship_valid() -> None:
    """StagedRelationship validates."""
    r = StagedRelationship(
        source_element="Document Intelligence Pipeline",
        target_element="Safety Knowledge Store",
        archimate_type="serving-relationship",
        confidence=0.75,
        evidence="Section 4.2: 'DI output routes to domain-specific indexes'",
    )
    assert r.source_element == "Document Intelligence Pipeline"


def test_extraction_file_valid() -> None:
    """ExtractionFile validates with metadata and entities."""
    meta = ExtractionMetadata(
        extracted_by="adr-generator",
        run_id="a1b2c3d4",
        timestamp="2026-03-02T10:00:00Z",
        source="tests/fixtures/transcripts/sample-decision-discussion.md",
    )
    ef = ExtractionFile(
        metadata=meta,
        entities=[
            StagedEntity(
                name="Chainlit",
                archimate_type="application-component",
                domain="ea-practice",
                confidence=0.95,
            )
        ],
    )
    assert len(ef.entities) == 1
    data = ef.model_dump()
    assert data["metadata"]["extracted_by"] == "adr-generator"


def test_relationship_file_valid() -> None:
    """RelationshipFile validates with metadata and relationships."""
    meta = ExtractionMetadata(
        extracted_by="adr-generator",
        run_id="a1b2c3d4",
        timestamp="2026-03-02T10:00:00Z",
        source="tests/fixtures/transcripts/sample-decision-discussion.md",
    )
    rf = RelationshipFile(
        metadata=meta,
        relationships=[
            StagedRelationship(
                source_element="Chainlit",
                target_element="Azure Container Apps",
                archimate_type="realization-relationship",
                confidence=0.8,
            )
        ],
    )
    assert len(rf.relationships) == 1
