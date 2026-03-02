"""Extraction schema validation with domain-specific constraints.

Re-exports and augments models from models/extraction.py and models/work.py
with validators for ArchiMate types and confidence ranges.
"""

from typing import Any

from pydantic import field_validator

from ea_workbench.models.extraction import (
    ExtractionFile,
    ExtractionMetadata,
    RelationshipFile,
    StagedEntity,
    StagedRelationship,
)
from ea_workbench.models.work import Provenance, StagedWorkItem, StagingWorkFile

# Re-export for convenience
__all__ = [
    "ExtractionFile",
    "ExtractionMetadata",
    "RelationshipFile",
    "StagedEntity",
    "StagedRelationship",
    "Provenance",
    "StagedWorkItem",
    "StagingWorkFile",
    "VALID_ARCHIMATE_ELEMENT_TYPES",
    "VALID_ARCHIMATE_RELATIONSHIP_TYPES",
    "ValidatedStagedEntity",
    "ValidatedStagedRelationship",
]

# Valid ArchiMate 3.2 element types — from REQUIREMENTS.md §7.3
VALID_ARCHIMATE_ELEMENT_TYPES: frozenset[str] = frozenset(
    {
        # Motivation layer
        "stakeholder",
        "driver",
        "assessment",
        "goal",
        "outcome",
        "principle",
        "requirement",
        "constraint",
        "meaning",
        "value",
        # Strategy layer
        "resource",
        "capability",
        "value-stream",
        "course-of-action",
        # Business layer
        "business-actor",
        "business-role",
        "business-process",
        "business-function",
        "business-service",
        "business-object",
        "business-event",
        # Application layer
        "application-component",
        "application-service",
        "application-interface",
        "data-object",
        # Technology layer
        "technology-node",
        "technology-service",
        "technology-interface",
        "system-software",
        "artifact",
    }
)

# Valid ArchiMate 3.2 relationship types
VALID_ARCHIMATE_RELATIONSHIP_TYPES: frozenset[str] = frozenset(
    {
        "composition-relationship",
        "aggregation-relationship",
        "assignment-relationship",
        "realization-relationship",
        "serving-relationship",
        "access-relationship",
        "flow-relationship",
        "triggering-relationship",
        "association-relationship",
        "influence-relationship",
    }
)

_MIN_CONFIDENCE = 0.5
_MAX_CONFIDENCE = 1.0


class ValidatedStagedEntity(StagedEntity):
    """StagedEntity with strict ArchiMate type and confidence validation."""

    @field_validator("archimate_type")
    @classmethod
    def archimate_type_must_be_valid(cls, v: str) -> str:
        """Validate that archimate_type is a recognised ArchiMate 3.2 element type."""
        if v not in VALID_ARCHIMATE_ELEMENT_TYPES:
            raise ValueError(
                f"'{v}' is not a valid ArchiMate element type. "
                f"Valid types: {sorted(VALID_ARCHIMATE_ELEMENT_TYPES)}"
            )
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_in_range(cls, v: float) -> float:
        """Confidence must be >= 0.5 (below 0.5 should not be staged)."""
        if v < _MIN_CONFIDENCE:
            raise ValueError(
                f"Confidence {v} is below minimum {_MIN_CONFIDENCE}. "
                "Entities with confidence < 0.5 should not be staged."
            )
        if v > _MAX_CONFIDENCE:
            raise ValueError(f"Confidence {v} exceeds maximum {_MAX_CONFIDENCE}.")
        return v


class ValidatedStagedRelationship(StagedRelationship):
    """StagedRelationship with strict ArchiMate type and confidence validation."""

    @field_validator("archimate_type")
    @classmethod
    def archimate_type_must_be_valid(cls, v: str) -> str:
        """Validate that archimate_type is a recognised ArchiMate relationship type."""
        if v not in VALID_ARCHIMATE_RELATIONSHIP_TYPES:
            raise ValueError(
                f"'{v}' is not a valid ArchiMate relationship type. "
                f"Valid types: {sorted(VALID_ARCHIMATE_RELATIONSHIP_TYPES)}"
            )
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_in_range(cls, v: float) -> float:
        """Confidence must be >= 0.5."""
        if v < _MIN_CONFIDENCE:
            raise ValueError(
                f"Confidence {v} is below minimum {_MIN_CONFIDENCE}."
            )
        if v > _MAX_CONFIDENCE:
            raise ValueError(f"Confidence {v} exceeds maximum {_MAX_CONFIDENCE}.")
        return v
