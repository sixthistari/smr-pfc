"""Pydantic models for the Solution Portfolio layer."""

from pydantic import BaseModel


class Solution(BaseModel):
    """A solution grouping related components into a deployable product."""

    id: str
    name: str
    description: str = ""
    domain_id: str = ""
    solution_type: str = "agent-service"  # agent-service|platform|integration
    status: str = "proposed"              # proposed|in-build|deployed|retired
    portfolio_product: str = ""
    business_service_id: str = ""         # FK → business_architecture
    owner: str = ""


class SolutionComponent(BaseModel):
    """Link between a solution and a solution architecture element."""

    solution_id: str
    element_id: str              # FK → solution_architecture
    role_in_solution: str = ""


class SolutionDiagram(BaseModel):
    """A diagram associated with a solution."""

    id: str
    solution_id: str
    diagram_type: str = ""       # component|sequence|deployment|class
    title: str = ""
    file_path: str = ""
    notation: str = ""           # UML|ArchiMate|custom


class DeploymentTarget(BaseModel):
    """An infrastructure target environment for solution deployment."""

    id: str
    name: str
    environment: str = ""        # dev|test|staging|prod
    region: str = ""
    subscription: str = ""


class SolutionDeployment(BaseModel):
    """A deployment of a solution to a target environment."""

    solution_id: str
    target_id: str               # FK → deployment_targets
    iac_path: str = ""           # Bicep or Terraform path
    status: str = "planned"      # planned|provisioned|active|decommissioned
