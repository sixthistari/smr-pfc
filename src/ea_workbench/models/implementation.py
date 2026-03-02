"""Pydantic model for the ArchiMate Implementation & Migration layer."""

from pydantic import BaseModel


class ImplementationElement(BaseModel):
    """An ArchiMate Implementation layer element: work-package, deliverable, plateau, or gap."""

    id: str
    name: str
    archimate_type: str          # work-package|deliverable|implementation-event|plateau|gap
    domain_id: str = ""
    status: str = "draft"
    description: str = ""
    solution_id: str = ""        # FK → solutions
    phase: str = ""              # Phase 0|1|2 etc.
    target_date: str = ""        # work-package target date
    plateau_description: str = ""  # plateau narrative
