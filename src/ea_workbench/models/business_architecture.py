"""Pydantic models for the ArchiMate Business Architecture layer."""

from pydantic import BaseModel, Field


class BusinessArchElement(BaseModel):
    """An ArchiMate Business layer element: actor, role, process, function, service, object, or event."""

    id: str
    name: str
    archimate_type: str          # business-actor|role|process|function|service|object|event
    domain_id: str = ""
    status: str = "draft"
    description: str = ""
    confidence: float = 0.8
    # Hierarchy
    parent_id: str = ""
    # Actor fields
    actor_type: str = ""         # person|team|org-unit|agent
    # Role fields
    agent_augmented: int = 0     # 0 or 1
    augmentation_level: str = "" # L0-L5
    # Process fields
    track: str = ""              # Track1|Track2
    governance_level: str = ""
    trigger_event: str = ""
    process_owner_id: str = ""   # FK → business-role
    # Service fields
    service_type: str = ""       # internal|external
    # Object fields
    has_authority_scoring: int = 0  # 0 or 1


class ProcessStep(BaseModel):
    """A single step within a business process."""

    id: str
    process_id: str              # FK → business_architecture (process)
    sequence: int
    name: str
    step_type: str = "human"     # human|agent|system|decision|gateway
    role_id: str = ""            # FK → business-role
    agent_id: str = ""           # FK → solution_architecture (agent)
    agent_autonomy: str = ""     # L0-L5
    description: str = ""
    input_objects: list = Field(default_factory=list)    # JSON-serialisable
    output_objects: list = Field(default_factory=list)   # JSON-serialisable
    approval_required: int = 0   # 0 or 1
    track_crossing: int = 0      # 0 or 1
