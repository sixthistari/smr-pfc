"""Tests for extraction schema validation."""

import pytest

from ea_workbench.extraction.schemas import (
    VALID_ARCHIMATE_ELEMENT_TYPES,
    VALID_ARCHIMATE_RELATIONSHIP_TYPES,
    ValidatedStagedEntity,
    ValidatedStagedRelationship,
)


def test_valid_entity_passes() -> None:
    """ValidatedStagedEntity accepts a valid ArchiMate type and confidence."""
    e = ValidatedStagedEntity(
        name="Document Intelligence Pipeline",
        archimate_type="application-component",
        domain="knowledge-infrastructure",
        confidence=0.9,
    )
    assert e.archimate_type == "application-component"
    assert e.confidence == 0.9


def test_invalid_archimate_type_raises() -> None:
    """ValidatedStagedEntity rejects invalid ArchiMate type."""
    with pytest.raises(Exception, match="not a valid ArchiMate"):
        ValidatedStagedEntity(
            name="Something",
            archimate_type="made-up-type",
            domain="safety",
            confidence=0.8,
        )


def test_confidence_below_minimum_raises() -> None:
    """ValidatedStagedEntity rejects confidence below 0.5."""
    with pytest.raises(Exception, match="below minimum"):
        ValidatedStagedEntity(
            name="Something",
            archimate_type="application-component",
            domain="safety",
            confidence=0.3,
        )


def test_confidence_above_maximum_raises() -> None:
    """ValidatedStagedEntity rejects confidence above 1.0."""
    with pytest.raises(Exception, match="exceeds maximum"):
        ValidatedStagedEntity(
            name="Something",
            archimate_type="application-component",
            domain="safety",
            confidence=1.5,
        )


def test_confidence_at_boundary_passes() -> None:
    """ValidatedStagedEntity accepts confidence exactly at 0.5 and 1.0."""
    e1 = ValidatedStagedEntity(
        name="Entity A",
        archimate_type="data-object",
        domain="safety",
        confidence=0.5,
    )
    e2 = ValidatedStagedEntity(
        name="Entity B",
        archimate_type="data-object",
        domain="safety",
        confidence=1.0,
    )
    assert e1.confidence == 0.5
    assert e2.confidence == 1.0


def test_valid_relationship_passes() -> None:
    """ValidatedStagedRelationship accepts a valid type and confidence."""
    r = ValidatedStagedRelationship(
        source_element="Pipeline",
        target_element="Store",
        archimate_type="serving-relationship",
        confidence=0.75,
    )
    assert r.archimate_type == "serving-relationship"


def test_invalid_relationship_type_raises() -> None:
    """ValidatedStagedRelationship rejects invalid relationship type."""
    with pytest.raises(Exception, match="not a valid ArchiMate relationship"):
        ValidatedStagedRelationship(
            source_element="A",
            target_element="B",
            archimate_type="fake-relationship",
            confidence=0.7,
        )


def test_all_valid_types_are_in_frozenset() -> None:
    """Spot-check that expected types are in the valid sets."""
    assert "application-component" in VALID_ARCHIMATE_ELEMENT_TYPES
    assert "goal" in VALID_ARCHIMATE_ELEMENT_TYPES
    assert "requirement" in VALID_ARCHIMATE_ELEMENT_TYPES
    assert "serving-relationship" in VALID_ARCHIMATE_RELATIONSHIP_TYPES
    assert "realization-relationship" in VALID_ARCHIMATE_RELATIONSHIP_TYPES


def test_motivation_types_valid() -> None:
    """All ArchiMate motivation layer element types validate."""
    motivation_types = [
        "stakeholder", "driver", "assessment", "goal", "outcome",
        "principle", "requirement", "constraint",
    ]
    for t in motivation_types:
        e = ValidatedStagedEntity(
            name=f"Test {t}",
            archimate_type=t,
            domain="enterprise",
            confidence=0.7,
        )
        assert e.archimate_type == t
