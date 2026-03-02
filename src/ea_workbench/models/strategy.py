"""Pydantic model for the ArchiMate Strategy layer — capabilities, value streams, resources."""

from pydantic import BaseModel, Field


class StrategyElement(BaseModel):
    """An ArchiMate Strategy layer element: capability, value-stream, resource, or course-of-action."""

    id: str
    name: str
    archimate_type: str          # capability|value-stream|resource|course-of-action
    domain_id: str = ""
    status: str = "draft"
    description: str = ""
    confidence: float = 0.8
    # Capability fields
    parent_id: str = ""
    level: int = 0
    maturity: str = ""
    # Value-stream fields
    stages: list = Field(default_factory=list)       # JSON-serialisable list
    value_proposition: str = ""
    # Course-of-action / goal reference
    horizon: str = ""                                # H1|H2|H3
    traces_to_goal: str = ""                         # FK → motivation
