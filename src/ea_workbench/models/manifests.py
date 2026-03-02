"""Pydantic models for agent run manifests."""

from pydantic import BaseModel


class RunManifest(BaseModel):
    """Record of a single batch agent execution."""

    agent_id: str
    run_id: str
    triggered_by: str  # "manual" | "pipeline" | "chat" | "scheduled"
    timestamp: str
    duration_seconds: float
    model_used: str
    tokens_consumed: int
    status: str  # "completed" | "failed" | "partial"
    inputs: list[str]
    outputs: list[str]
    entities_extracted: int = 0
    relationships_extracted: int = 0
    summary: dict[str, object] = {}
    error: str | None = None
