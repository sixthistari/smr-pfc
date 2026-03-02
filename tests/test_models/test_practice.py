"""Tests for practice artefact models."""

import pytest

from ea_workbench.models.practice import (
    Decision,
    Idea,
    NFR,
    Principle,
    PracticeIndex,
    Standard,
    Strategy,
)


def test_principle_valid() -> None:
    """Principle validates with required fields."""
    p = Principle(
        id="PRI-001",
        title="The Specification Imperative",
        status="active",
        created_at="2026-02-20",
        updated_at="2026-03-01",
        domain="enterprise",
        summary="Precise articulation of intent is the irreplaceable human contribution",
        rationale="As AI assumes implementation, specs become the primary EA contribution",
        implications=["All AI use cases require formal spec before implementation"],
    )
    assert p.archimate_type == "principle"
    assert len(p.implications) == 1


def test_decision_valid() -> None:
    """Decision validates with required fields."""
    d = Decision(
        id="ADR-001",
        title="Use Chainlit as Chat Interface",
        status="proposed",
        created_at="2026-02-20",
        updated_at="2026-02-20",
        domain="ea-practice",
    )
    assert d.consequences == []


def test_nfr_valid() -> None:
    """NFR validates with required fields."""
    nfr = NFR(
        id="NFR-001",
        title="RAG Retrieval Accuracy",
        status="active",
        created_at="2026-02-20",
        updated_at="2026-02-20",
        domain="safety",
        category="accuracy",
        threshold="70%",
        target="85%",
    )
    assert nfr.archimate_type == "constraint"


def test_idea_valid() -> None:
    """Idea validates."""
    i = Idea(
        id="IDEA-001",
        title="Meta-Agent Spawning",
        status="parked",
        created_at="2026-02-20",
        updated_at="2026-02-20",
    )
    assert i.status == "parked"


def test_standard_valid() -> None:
    """Standard validates."""
    s = Standard(
        id="STD-001",
        title="Dual-Track Model",
        status="active",
        created_at="2026-02-20",
        updated_at="2026-02-20",
        enforcement="mandatory",
    )
    assert s.enforcement == "mandatory"


def test_strategy_valid() -> None:
    """Strategy validates with archimate_type."""
    s = Strategy(
        id="STRAT-001",
        title="Fabric IQ Phase 2 Gate",
        status="proposed",
        created_at="2026-02-20",
        updated_at="2026-02-20",
        affects_roadmap=True,
    )
    assert s.archimate_type == "course-of-action"


def test_practice_index_empty() -> None:
    """PracticeIndex with empty items list validates."""
    idx = PracticeIndex(last_updated="2026-03-02")
    assert idx.items == []
    assert idx.version == "1.0"


def test_practice_missing_required_raises() -> None:
    """Missing required fields raise ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        Principle.model_validate({"id": "PRI-001"})  # missing title, status, etc.
