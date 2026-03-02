"""Pydantic models for architectural elements, relationships, and capabilities."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utcnow() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class Element(BaseModel):
    """An architectural element in the element registry."""

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
    """A relationship between two architectural elements."""

    id: str
    source_element_id: str
    target_element_id: str
    archimate_type: str
    description: str | None = None
    source_spec: str | None = None
    evidence: str | None = None
    confidence: float = 1.0
    created_at: str = Field(default_factory=_utcnow)
    created_by: str | None = None


class Capability(BaseModel):
    """A business capability in the capability hierarchy."""

    id: str
    name: str
    parent_id: str | None = None
    level: int
    domain: str | None = None
    maturity: str | None = None
    description: str | None = None


class ElementCapability(BaseModel):
    """Link between an element and a capability it realises."""

    element_id: str
    capability_id: str
    relationship_type: str = "realizes"
