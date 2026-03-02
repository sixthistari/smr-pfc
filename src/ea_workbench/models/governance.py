"""Pydantic models for Governance Controls and Quality Evaluations."""

from pydantic import BaseModel, Field


class GovernanceControl(BaseModel):
    """A governance control enforcing compliance across architectural elements."""

    id: str
    name: str
    description: str = ""
    target_table: str = ""       # Which concern table this governs
    target_id: str = ""          # FK → governed element
    standard_id: str = ""        # FK → practice_artefacts
    constraint_id: str = ""      # Optional FK → motivation (constraint type)
    enforcement_type: str = "manual-audit"    # automated|manual-audit|self-assessment|approval-gate
    enforcement_mechanism: str = ""
    assessment_frequency: str = "monthly"     # continuous|daily|weekly|monthly|quarterly|annual
    last_assessed: str = ""
    compliance_status: str = "not-assessed"   # compliant|non-compliant|partially-compliant|not-assessed|exempt
    scope: str = "enterprise"                 # enterprise|domain|process|step
    domain_id: str = ""


class QualityEvaluation(BaseModel):
    """A quality evaluation record for an architectural element or solution."""

    id: str
    name: str
    target_table: str = ""       # sol_arch|solutions|process_steps|bus_arch|strategy
    target_id: str = ""          # FK → evaluated element
    domain_id: str = ""
    evaluation_type: str = ""    # retrieval|generation|end-to-end|latency|cost
    phase: str = ""              # Phase 0|1|2 etc.
    baseline_ref: str = ""       # FK → prior evaluation
    methodology: str = ""        # reference to test protocol
    metrics: dict = Field(default_factory=dict)  # precision_at_5, latency_p50, etc.
    pass_fail: str = "inconclusive"   # pass|fail|inconclusive
    summary: str = ""
    decision_ref: str = ""       # FK → practice_artefacts (ADR)
    evaluated_by: str = ""
    evaluated_at: str = ""
