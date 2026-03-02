"""Tests for the StrategyElement model."""

import pytest
import pydantic

from ea_workbench.models.strategy import StrategyElement


def test_capability_element() -> None:
    """StrategyElement for capability validates with hierarchy fields."""
    el = StrategyElement(
        id="CAP-001",
        name="Safety Knowledge Management",
        archimate_type="capability",
        domain_id="dom-safety",
        level=1,
        maturity="defined",
    )
    assert el.archimate_type == "capability"
    assert el.level == 1
    assert el.maturity == "defined"


def test_value_stream_element() -> None:
    """StrategyElement for value-stream includes stages."""
    el = StrategyElement(
        id="VS-001",
        name="Safety Procedure Lifecycle",
        archimate_type="value-stream",
        stages=["Draft", "Review", "Approve", "Publish", "Supersede"],
        value_proposition="Ensure only authoritative procedures are used",
    )
    assert len(el.stages) == 5
    assert el.value_proposition != ""


def test_strategy_default_values() -> None:
    """StrategyElement has correct defaults."""
    el = StrategyElement(id="RES-001", name="AI Platform Budget", archimate_type="resource")
    assert el.confidence == 0.8
    assert el.status == "draft"
    assert el.stages == []
    assert el.level == 0


def test_strategy_missing_required_raises() -> None:
    """Missing required fields raise ValidationError."""
    with pytest.raises(pydantic.ValidationError):
        StrategyElement.model_validate({"id": "CAP-bad"})  # missing name + archimate_type
