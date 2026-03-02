"""Pydantic models for the ArchiMate Motivation layer — needs, requirements, engagements."""

from pydantic import BaseModel


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
