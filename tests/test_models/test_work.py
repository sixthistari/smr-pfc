"""Tests for work artefact staging and session record models."""

import pytest

from ea_workbench.models.work import (
    Provenance,
    SessionRecord,
    StagedWorkItem,
    StagingWorkFile,
    StagingWorkMetadata,
)


def test_provenance_valid() -> None:
    """Provenance validates with required fields."""
    p = Provenance(
        session_id="chainlit-session-abc123",
        conversation_summary="Discussed Purview label coverage gap.",
        trigger_message="What happens if labels aren't applied?",
    )
    assert p.key_exchanges == []
    assert p.related_artefacts == []


def test_staged_work_item_task() -> None:
    """StagedWorkItem for a task validates."""
    item = StagedWorkItem(
        type="task",
        title="Investigate Purview label coverage",
        description="Assess current sensitivity label coverage on Safety SharePoint.",
        priority="high",
        domain="knowledge-infrastructure",
        suggested_devops_type="Task",
        provenance=Provenance(
            session_id="session-xyz",
            conversation_summary="Coverage gap identified during spec review.",
        ),
    )
    assert item.type == "task"
    assert item.provenance.session_id == "session-xyz"


def test_staging_work_file_valid() -> None:
    """StagingWorkFile validates with items."""
    meta = StagingWorkMetadata(
        extracted_by="chat-agent",
        session_id="session-abc",
        timestamp="2026-03-02T10:00:00Z",
    )
    f = StagingWorkFile(
        metadata=meta,
        items=[
            StagedWorkItem(
                type="risk",
                title="Label coverage below 30%",
                description="Risk to Safety domain governance.",
                provenance=Provenance(
                    session_id="session-abc",
                    conversation_summary="Risk identified during analysis.",
                ),
            )
        ],
    )
    assert len(f.items) == 1
    data = f.model_dump()
    assert data["metadata"]["extracted_by"] == "chat-agent"


def test_session_record_valid() -> None:
    """SessionRecord validates and has correct defaults."""
    rec = SessionRecord(
        session_id="chainlit-session-abc",
        started_at="2026-03-02T09:30:00Z",
        ended_at="2026-03-02T11:15:00Z",
        intent="Working on ingestion spec",
        summary="Reviewed ingestion pipeline design.",
        artefacts_produced={"entities_staged": 2, "work_items_staged": 1},
        topics_discussed=["Purview label coverage"],
    )
    assert rec.staged_references == []
    assert rec.artefacts_produced["entities_staged"] == 2


def test_work_item_missing_provenance_raises() -> None:
    """StagedWorkItem requires provenance."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        StagedWorkItem.model_validate(
            {
                "type": "task",
                "title": "Some task",
                "description": "desc",
            }
        )
