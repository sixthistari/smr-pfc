"""Pydantic models for architectural elements, relationships, and capabilities."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utcnow() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class Element(BaseModel):
    """An architectural element in the element registry (legacy generic model)."""

    id: str
    name: str
    archimate_type: str
    domain: str
    status: str = "proposed"
    description: str | None = None
    source_spec: str | None = None
    source_line: int | None = None
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
    created_by: str | None = None
    confidence: float = 1.0


class Relationship(BaseModel):
    """A cross-table relationship between two architectural elements (Option C schema)."""

    id: str
    source_table: str = ""       # Name of the source concern table
    source_id: str = ""          # ID of the source element
    target_table: str = ""       # Name of the target concern table
    target_id: str = ""          # ID of the target element
    archimate_type: str
    description: str = ""
    evidence: str = ""
    confidence: float = 1.0
    created_at: str = Field(default_factory=_utcnow)
    created_by: str = ""


class ValidRelationship(BaseModel):
    """A permitted ArchiMate metamodel relationship pair (seed data for valid_relationships table)."""

    source_archimate_type: str
    target_archimate_type: str
    relationship_type: str


class Capability(BaseModel):
    """A business capability in the capability hierarchy (legacy model)."""

    id: str
    name: str
    parent_id: str | None = None
    level: int
    domain: str | None = None
    maturity: str | None = None
    description: str | None = None


class ElementCapability(BaseModel):
    """Link between an element and a capability it realises (legacy model)."""

    element_id: str
    capability_id: str
    relationship_type: str = "realizes"
