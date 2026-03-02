"""Tests for the MotivationElement model (Option C unified motivation layer)."""

import pytest
import pydantic

from ea_workbench.models.motivation import MotivationElement


def test_stakeholder_element() -> None:
    """MotivationElement for stakeholder archimate_type validates correctly."""
    el = MotivationElement(
        id="STKH-001",
        name="Safety Manager",
        archimate_type="stakeholder",
        domain_id="dom-safety",
        role="Safety Manager",
        influence_level="high",
    )
    assert el.archimate_type == "stakeholder"
    assert el.role == "Safety Manager"
    assert el.influence_level == "high"


def test_driver_element() -> None:
    """MotivationElement for driver archimate_type validates correctly."""
    el = MotivationElement(
        id="DRV-001",
        name="Regulatory Compliance Pressure",
        archimate_type="driver",
        domain_id="dom-safety",
        driver_category="regulatory",
        description="New WHS Act obligations",
    )
    assert el.driver_category == "regulatory"


def test_requirement_element() -> None:
    """MotivationElement for requirement archimate_type validates correctly."""
    el = MotivationElement(
        id="BREQ-001",
        name="Procedure Retrieval Accuracy",
        archimate_type="requirement",
        domain_id="dom-safety",
        requirement_type="nonfunctional",
        category="accuracy",
        threshold="95%",
        target="99%",
        acceptance_criteria={"precision_at_5": 0.95},
    )
    assert el.requirement_type == "nonfunctional"
    assert el.acceptance_criteria["precision_at_5"] == 0.95


def test_goal_element_with_horizon() -> None:
    """MotivationElement for goal archimate_type includes horizon."""
    el = MotivationElement(
        id="GOAL-001",
        name="Zero Safety Incidents",
        archimate_type="goal",
        horizon="H1",
    )
    assert el.horizon == "H1"


def test_motivation_default_confidence() -> None:
    """MotivationElement has correct default confidence."""
    el = MotivationElement(id="ASSESS-001", name="Risk Assessment", archimate_type="assessment")
    assert el.confidence == 0.8
    assert el.status == "draft"


def test_motivation_missing_required_raises() -> None:
    """Missing id or name raises ValidationError."""
    with pytest.raises(pydantic.ValidationError):
        MotivationElement.model_validate({"archimate_type": "driver"})
