"""Pydantic models for practice artefacts — principles, standards, decisions, NFRs, ideas, strategies."""

from pydantic import BaseModel


class PracticeArtefact(BaseModel):
    """Base class for all practice artefact types."""

    id: str
    title: str
    status: str  # "active" | "draft" | "deprecated" | "superseded"
    created_at: str
    updated_at: str
    file: str | None = None
    domain: str | None = None
    summary: str | None = None


class Principle(PracticeArtefact):
    """An architectural principle (ArchiMate: principle)."""

    archimate_type: str = "principle"
    rationale: str | None = None
    implications: list[str] = []


class Standard(PracticeArtefact):
    """An architectural standard or policy."""

    archimate_type: str | None = None
    scope: str | None = None
    enforcement: str | None = None  # "mandatory" | "recommended" | "advisory"


class Decision(PracticeArtefact):
    """An Architecture Decision Record."""

    archimate_type: str | None = None
    context: str | None = None
    decision_text: str | None = None
    consequences: list[str] = []
    related_adrs: list[str] = []


class NFR(PracticeArtefact):
    """A non-functional requirement (ArchiMate: constraint)."""

    archimate_type: str = "constraint"
    category: str | None = None  # "performance" | "security" | "availability" | ...
    threshold: str | None = None
    target: str | None = None
    measured_by: str | None = None


class Idea(PracticeArtefact):
    """An idea parked for evaluation."""

    archimate_type: str | None = None
    # status extends to: "parked" | "evaluating" | "adopted" | "rejected"
    evaluation_notes: str | None = None


class Strategy(PracticeArtefact):
    """A strategic position or approach (ArchiMate: course-of-action)."""

    archimate_type: str = "course-of-action"
    affects_roadmap: bool = False
    rationale: str | None = None


class PracticeIndex(BaseModel):
    """The _index.yaml register for a practice artefact type."""

    version: str = "1.0"
    last_updated: str
    items: list[PracticeArtefact] = []
