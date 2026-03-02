"""Tests for Portfolio models: Solution, SolutionComponent, DeploymentTarget, SolutionDeployment."""

import pytest

from ea_workbench.models.portfolio import (
    DeploymentTarget,
    Solution,
    SolutionComponent,
    SolutionDeployment,
    SolutionDiagram,
)


def test_solution_create() -> None:
    """Solution creates with required fields and defaults."""
    sol = Solution(
        id="sol-safety-knowledge",
        name="Safety Knowledge Platform",
        domain_id="dom-safety",
        solution_type="agent-service",
        status="proposed",
    )
    assert sol.id == "sol-safety-knowledge"
    assert sol.status == "proposed"


def test_deployment_target() -> None:
    """DeploymentTarget validates environment and region."""
    dt = DeploymentTarget(
        id="dt-prod-aue",
        name="Production AuE",
        environment="prod",
        region="australiaeast",
        subscription="sub-prod-001",
    )
    assert dt.environment == "prod"


def test_solution_deployment() -> None:
    """SolutionDeployment links solution to target."""
    dep = SolutionDeployment(
        solution_id="sol-safety-knowledge",
        target_id="dt-prod-aue",
        iac_path="infra/safety/main.bicep",
        status="planned",
    )
    assert dep.iac_path == "infra/safety/main.bicep"


def test_solution_component() -> None:
    """SolutionComponent links element to solution."""
    sc = SolutionComponent(
        solution_id="sol-safety-knowledge",
        element_id="comp-doc-intel",
        role_in_solution="ingestion",
    )
    assert sc.role_in_solution == "ingestion"
