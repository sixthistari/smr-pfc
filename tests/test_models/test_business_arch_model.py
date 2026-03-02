"""Tests for the BusinessArchElement and ProcessStep models."""

import pytest
import pydantic

from ea_workbench.models.business_architecture import BusinessArchElement, ProcessStep


def test_business_actor() -> None:
    """BusinessArchElement for business-actor validates correctly."""
    el = BusinessArchElement(
        id="BA-001",
        name="Safety Manager",
        archimate_type="business-actor",
        domain_id="dom-safety",
        actor_type="person",
    )
    assert el.actor_type == "person"
    assert el.agent_augmented == 0


def test_business_role_with_augmentation() -> None:
    """BusinessArchElement for role with agent augmentation."""
    el = BusinessArchElement(
        id="BR-001",
        name="Incident Responder",
        archimate_type="role",
        agent_augmented=1,
        augmentation_level="L2",
    )
    assert el.agent_augmented == 1
    assert el.augmentation_level == "L2"


def test_business_process_fields() -> None:
    """BusinessArchElement for process includes track and governance."""
    el = BusinessArchElement(
        id="BP-001",
        name="Incident Investigation Process",
        archimate_type="process",
        domain_id="dom-safety",
        track="Track1",
        governance_level="operational",
    )
    assert el.track == "Track1"


def test_process_step() -> None:
    """ProcessStep validates with step_type and approval fields."""
    step = ProcessStep(
        id="step-001",
        process_id="BP-001",
        sequence=1,
        name="Classify Incident",
        step_type="agent",
        agent_id="comp-classifier",
        agent_autonomy="L2",
        approval_required=1,
    )
    assert step.step_type == "agent"
    assert step.approval_required == 1
    assert step.input_objects == []


def test_business_arch_default_values() -> None:
    """BusinessArchElement has correct defaults."""
    el = BusinessArchElement(
        id="BO-001", name="Safety Report", archimate_type="object"
    )
    assert el.status == "draft"
    assert el.confidence == 0.8
    assert el.has_authority_scoring == 0
