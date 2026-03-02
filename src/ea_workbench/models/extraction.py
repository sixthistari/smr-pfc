"""Pydantic models for staging file formats — entities and relationships."""

from pydantic import BaseModel


class StagedEntity(BaseModel):
    """A single architectural entity extracted from a source document."""

    name: str
    archimate_type: str
    domain: str
    status: str = "proposed"
    description: str | None = None
    source_line: int | None = None
    confidence: float


class StagedRelationship(BaseModel):
    """A relationship between two extracted entities."""

    source_element: str
    target_element: str
    archimate_type: str
    description: str | None = None
    confidence: float
    evidence: str | None = None


class ExtractionMetadata(BaseModel):
    """Metadata header for a staging file."""

    extracted_by: str
    run_id: str
    timestamp: str
    source: str


class ExtractionFile(BaseModel):
    """A complete entity staging file (.staging/entities/{agent}_{run}.yaml)."""

    metadata: ExtractionMetadata
    entities: list[StagedEntity] = []


class RelationshipFile(BaseModel):
    """A complete relationship staging file (.staging/relationships/{agent}_{run}.yaml)."""

    metadata: ExtractionMetadata
    relationships: list[StagedRelationship] = []
