"""Tests for RunManifest model."""

import pytest

from ea_workbench.models.manifests import RunManifest


def test_manifest_valid() -> None:
    """RunManifest with all required fields validates."""
    m = RunManifest(
        agent_id="adr-generator",
        run_id="a1b2c3d4",
        triggered_by="manual",
        timestamp="2026-03-02T10:00:00Z",
        duration_seconds=12.5,
        model_used="claude-sonnet-4-6",
        tokens_consumed=2400,
        status="completed",
        inputs=["tests/fixtures/transcripts/sample-decision-discussion.md"],
        outputs=["stanmore-pfc/architecture/decisions/ADR-001.md"],
        entities_extracted=2,
        summary={"pages_written": 1, "decisions_identified": 1},
    )
    assert m.error is None
    assert m.entities_extracted == 2
    data = m.model_dump()
    assert data["agent_id"] == "adr-generator"


def test_manifest_failed() -> None:
    """Failed manifest with error field validates."""
    m = RunManifest(
        agent_id="adr-generator",
        run_id="fail001",
        triggered_by="chat",
        timestamp="2026-03-02T10:00:00Z",
        duration_seconds=0.5,
        model_used="claude-sonnet-4-6",
        tokens_consumed=0,
        status="failed",
        inputs=[],
        outputs=[],
        error="Input file not found: context.md",
    )
    assert m.status == "failed"
    assert m.error is not None


def test_manifest_missing_required_raises() -> None:
    """Missing required fields raise ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RunManifest.model_validate({"agent_id": "x"})
