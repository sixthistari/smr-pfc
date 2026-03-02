"""Pydantic models for work artefact staging and session records."""

from pydantic import BaseModel


class Provenance(BaseModel):
    """Provenance block linking a staged item to its originating conversation."""

    session_id: str
    timestamp: str | None = None
    conversation_summary: str
    trigger_message: str | None = None
    key_exchanges: list[dict[str, str]] = []
    session_link: str | None = None
    related_artefacts: list[dict[str, str]] = []


class StagedWorkItem(BaseModel):
    """A single work item staged for DevOps triage."""

    type: str  # "task" | "risk"
    title: str
    description: str
    priority: str | None = None
    domain: str | None = None
    blocks: str | None = None
    suggested_devops_type: str | None = None
    suggested_area_path: str | None = None
    provenance: Provenance


class StagingWorkMetadata(BaseModel):
    """Metadata header for a work staging file."""

    extracted_by: str
    session_id: str
    timestamp: str


class StagingWorkFile(BaseModel):
    """A complete work staging file (.staging/work/chat_{session_id}_{seq}.yaml)."""

    metadata: StagingWorkMetadata
    items: list[StagedWorkItem] = []


class SessionRecord(BaseModel):
    """Structured summary of a chat session persisted to .staging/sessions/."""

    session_id: str
    started_at: str
    ended_at: str | None = None
    session_link: str | None = None
    intent: str | None = None
    summary: str | None = None
    artefacts_produced: dict[str, int] = {}
    staged_references: list[str] = []
    topics_discussed: list[str] = []
