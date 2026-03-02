"""Tests for GovernanceControl and QualityEvaluation models."""

import pytest

from ea_workbench.models.governance import GovernanceControl, QualityEvaluation


def test_governance_control_create() -> None:
    """GovernanceControl creates with required fields."""
    ctrl = GovernanceControl(
        id="ctrl-tcp-bp-incident",
        name="Incident Process Dual-Track Gate",
        description="Ensures all incident processes define Track1/Track2 routing",
        target_table="business_architecture",
        enforcement_type="approval-gate",
        assessment_frequency="weekly",
        domain_id="dom-safety",
    )
    assert ctrl.id == "ctrl-tcp-bp-incident"
    assert ctrl.enforcement_type == "approval-gate"


def test_governance_control_defaults() -> None:
    """GovernanceControl has correct defaults."""
    ctrl = GovernanceControl(id="ctrl-test", name="Test Control")
    assert ctrl.compliance_status == "not-assessed"
    assert ctrl.scope == "enterprise"
    assert ctrl.assessment_frequency == "monthly"


def test_quality_evaluation() -> None:
    """QualityEvaluation stores metrics dict."""
    qe = QualityEvaluation(
        id="eval-safety-retrieval-baseline",
        name="Safety Retrieval Baseline",
        target_table="solution_architecture",
        target_id="comp-safety-agent",
        domain_id="dom-safety",
        evaluation_type="retrieval",
        phase="Phase 0",
        metrics={"precision_at_5": 0.87, "latency_p50_ms": 320},
        pass_fail="pass",
        evaluated_by="test-runner",
        evaluated_at="2026-03-01",
    )
    assert qe.metrics["precision_at_5"] == 0.87
    assert qe.pass_fail == "pass"
