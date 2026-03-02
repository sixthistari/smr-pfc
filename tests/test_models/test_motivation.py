"""Tests for motivation layer models."""

import pytest

from ea_workbench.models.motivation import Driver, Engagement, Need, Outcome, Requirement


def test_need_valid() -> None:
    """Need validates with required fields."""
    need = Need(
        id="NEED-001",
        statement="Find the current authoritative version of a safety procedure quickly",
        domain="safety",
        stakeholders=["Safety Manager", "Site Supervisor"],
        drivers=["Multiple versions exist across SharePoint"],
        priority="high",
    )
    assert need.archimate_type == "goal"
    assert need.requirements_derived == []


def test_requirement_valid() -> None:
    """Requirement validates with required fields."""
    req = Requirement(
        id="REQ-001",
        traces_to_need="NEED-001",
        statement="The system shall return only the current authoritative document version",
        domain="safety",
        acceptance_criteria=["Default query excludes Superseded docs"],
    )
    assert req.archimate_type == "requirement"
    assert req.type == "functional"


def test_driver_valid() -> None:
    """Driver validates with required fields."""
    d = Driver(
        id="DRV-001",
        statement="Multiple document versions cause confusion",
        domain="safety",
    )
    assert d.archimate_type == "driver"


def test_outcome_valid() -> None:
    """Outcome validates with required fields."""
    o = Outcome(
        id="OUT-001",
        statement="Reduce lookup time to under 1 minute",
        domain="safety",
    )
    assert o.archimate_type == "outcome"


def test_engagement_valid() -> None:
    """Engagement validates with required fields."""
    eng = Engagement(
        id="ENG-001",
        title="Safety Managers Knowledge Access Workshop",
        date="2026-03-15",
        type="workshop",
        participants=[{"role": "Safety Manager"}],
        needs_identified=[{"ref": "NEED-001"}],
    )
    assert eng.type == "workshop"


def test_need_missing_required_raises() -> None:
    """Missing required fields raise ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        Need.model_validate({"id": "NEED-001"})  # missing statement, domain
