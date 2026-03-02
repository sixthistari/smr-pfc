"""Tests for the SolutionArchElement model."""

import pytest
import pydantic

from ea_workbench.models.solution_architecture import SolutionArchElement


def test_application_component() -> None:
    """SolutionArchElement for application-component validates correctly."""
    el = SolutionArchElement(
        id="comp-doc-intel",
        name="Document Intelligence Pipeline",
        archimate_type="application-component",
        domain_id="dom-knowledge",
        version="2.1",
        deployment_status="production",
    )
    assert el.version == "2.1"
    assert el.deployment_status == "production"


def test_agent_component_fields() -> None:
    """SolutionArchElement for AI agent includes autonomy fields."""
    el = SolutionArchElement(
        id="comp-safety-agent",
        name="Safety Agent",
        archimate_type="application-component",
        is_agent=1,
        default_autonomy="L2",
        default_track="Track1",
        knowledge_base_ref="dom-safety",
    )
    assert el.is_agent == 1
    assert el.default_autonomy == "L2"


def test_knowledge_store_fields() -> None:
    """SolutionArchElement for knowledge store includes store_type."""
    el = SolutionArchElement(
        id="data-safety-store",
        name="Safety Knowledge Store",
        archimate_type="data-object",
        is_knowledge_store=1,
        store_type="vector",
        config_path="stanmore-pfc/config/safety-store.yaml",
    )
    assert el.is_knowledge_store == 1
    assert el.store_type == "vector"


def test_solution_arch_defaults() -> None:
    """SolutionArchElement has correct defaults."""
    el = SolutionArchElement(
        id="svc-search", name="Search Service", archimate_type="application-service"
    )
    assert el.ga_status == "ga"
    assert el.deployment_status == "planned"
    assert el.confidence == 0.8
