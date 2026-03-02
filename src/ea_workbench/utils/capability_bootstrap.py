"""Capability model validation and summary utilities."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def _count_capabilities(nodes: list, depth: int = 0) -> tuple[int, int]:
    """Recursively count capabilities and find max depth.

    Args:
        nodes: List of capability dicts (may have 'children').
        depth: Current recursion depth.

    Returns:
        Tuple of (total_count, max_depth).
    """
    total = 0
    max_depth = depth
    for node in nodes:
        if not isinstance(node, dict):
            continue
        total += 1
        children = node.get("children", [])
        if children:
            child_count, child_max_depth = _count_capabilities(children, depth + 1)
            total += child_count
            max_depth = max(max_depth, child_max_depth)
    return total, max_depth


def _collect_domains(nodes: list) -> set[str]:
    """Recursively collect all domain values from capability nodes.

    Args:
        nodes: List of capability dicts.

    Returns:
        Set of domain strings found.
    """
    domains: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        domain = node.get("domain")
        if domain:
            domains.add(domain)
        children = node.get("children", [])
        if children:
            domains |= _collect_domains(children)
    return domains


def validate_capability_model(workspace: str) -> dict:
    """Load capability-model.yaml, validate structure, and return a summary dict.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Dict with keys:
          - domain_count: Number of unique domains
          - capability_count: Total number of capability nodes
          - max_depth: Maximum hierarchy depth (0 = top-level only)
          - is_valid: True if the model loaded and has at least one capability
    """
    cap_path = Path(workspace) / "capabilities" / "capability-model.yaml"

    if not cap_path.exists():
        return {
            "domain_count": 0,
            "capability_count": 0,
            "max_depth": 0,
            "is_valid": False,
        }

    try:
        with cap_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as exc:
        logger.error("Could not parse capability model at %s: %s", cap_path, exc)
        return {
            "domain_count": 0,
            "capability_count": 0,
            "max_depth": 0,
            "is_valid": False,
        }

    if not isinstance(data, dict):
        return {
            "domain_count": 0,
            "capability_count": 0,
            "max_depth": 0,
            "is_valid": False,
        }

    capabilities = data.get("capabilities", [])
    if not isinstance(capabilities, list):
        return {
            "domain_count": 0,
            "capability_count": 0,
            "max_depth": 0,
            "is_valid": False,
        }

    capability_count, max_depth = _count_capabilities(capabilities)
    domains = _collect_domains(capabilities)

    return {
        "domain_count": len(domains),
        "capability_count": capability_count,
        "max_depth": max_depth,
        "is_valid": capability_count > 0,
    }
