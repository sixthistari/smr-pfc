"""Pydantic models for the ArchiMate Motivation layer — needs, requirements, engagements."""

from pydantic import BaseModel, Field


class MotivationElement(BaseModel):
    """Unified ArchiMate Motivation layer element for the Option C schema.

    Replaces the separate Driver/Outcome/Need/Requirement models in the database.
    The ``archimate_type`` field determines which subtype-specific fields are relevant.
    """

    id: str
    name: str
    archimate_type: str          # stakeholder|driver|assessment|goal|outcome|requirement|constraint
    domain_id: str = ""
    status: str = "draft"
    description: str = ""
    confidence: float = 0.8
    # Stakeholder fields
    role: str = ""
    influence_level: str = ""
    # Driver fields
    driver_category: str = ""    # internal|external|regulatory
    # Assessment fields
    evidence: str = ""
    impact: str = ""
    # Goal / outcome fields
    horizon: str = ""            # H1|H2|H3
    # Requirement fields
    requirement_type: str = ""   # business|solution|nonfunctional
    category: str = ""
    threshold: str = ""
    target: str = ""
    acceptance_criteria: dict = Field(default_factory=dict)
    solution_id: str = ""
    engagement_ref: str = ""


# ---------------------------------------------------------------------------
# Legacy classes — kept for backward compatibility with existing code/tests.
# New code should use MotivationElement with the appropriate archimate_type.
# ---------------------------------------------------------------------------


class Driver(BaseModel):
    """An ArchiMate driver — internal or external condition that motivates change."""

    id: str
    statement: str
    archimate_type: str = "driver"
    domain: str | None = None


class Outcome(BaseModel):
    """An ArchiMate outcome — desired end result of meeting a need."""

    id: str
    statement: str
    archimate_type: str = "outcome"
    domain: str | None = None


class Need(BaseModel):
    """A stakeholder need (ArchiMate: goal) — solution-independent."""

    id: str
    statement: str
    archimate_type: str = "goal"
    domain: str
    stakeholders: list[str] = []
    drivers: list[str] = []
    outcomes: list[str] = []
    priority: str | None = None
    engagement_ref: str | None = None
    requirements_derived: list[str] = []


class Requirement(BaseModel):
    """A solution requirement (ArchiMate: requirement) — solution-specific."""

    id: str
    traces_to_need: str
    statement: str
    archimate_type: str = "requirement"
    type: str = "functional"  # "functional" | "non-functional"
    domain: str
    acceptance_criteria: list[str] = []
    realised_by: list[dict[str, str]] = []
    nfr_ref: str | None = None
    category: str | None = None
    threshold: str | None = None
    target: str | None = None


class Engagement(BaseModel):
    """A stakeholder engagement session record."""

    id: str
    title: str
    date: str
    type: str  # "workshop" | "interview" | "review" | "observation"
    participants: list[dict[str, str]] = []
    context: str | None = None
    needs_identified: list[dict[str, str]] = []
    provenance: dict[str, str] | None = None
