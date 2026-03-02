"""Pydantic model for Architecture Domains — bounded contexts with governed partitions."""

from pydantic import BaseModel


class Domain(BaseModel):
    """A first-class domain entity representing a bounded context in the enterprise."""

    id: str
    name: str
    description: str = ""
    priority: int = 0
    maturity: str = "initial"          # initial|defined|managed|optimised
    autonomy_ceiling: str = "L5"       # L0-L5 max autonomy allowed for this domain
    track_default: str = "Track1"      # Track1|Track2 default operating track
    spec_coverage: str = ""
    owner_role: str = ""
