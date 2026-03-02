"""Utility functions for loading and summarising YAML knowledge base files."""

import logging
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _load_yaml(path: str) -> Any:
    """Safely load a YAML file.

    Args:
        path: Filesystem path to the YAML file.

    Returns:
        Parsed YAML content.

    Raises:
        FileNotFoundError: If path does not exist.
        yaml.YAMLError: If the file is not valid YAML.
    """
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _render_capability_node(node: dict[str, Any], indent: int, max_depth: int) -> list[str]:
    """Recursively render a capability node as markdown outline lines.

    Args:
        node: Capability node dict with optional 'children'.
        indent: Current indent level.
        max_depth: Maximum depth to render (0-indexed).

    Returns:
        List of markdown outline lines.
    """
    lines: list[str] = []
    prefix = "  " * indent + "- "
    name = node.get("name", node.get("id", "Unknown"))
    maturity = node.get("maturity", "")
    maturity_tag = f" *({maturity})*" if maturity else ""
    lines.append(f"{prefix}**{name}**{maturity_tag}")

    if indent < max_depth:
        for child in node.get("children", []):
            lines.extend(_render_capability_node(child, indent + 1, max_depth))

    return lines


def load_capability_summary(path: str, max_depth: int = 2) -> str:
    """Load capability YAML and render as a markdown outline.

    Args:
        path: Path to capability-model.yaml.
        max_depth: Maximum hierarchy depth to include (0 = top level only).

    Returns:
        Markdown string summarising the capability model.
    """
    try:
        data = _load_yaml(path)
    except FileNotFoundError:
        logger.warning("Capability model not found at %s", path)
        return "_Capability model not available._"
    except yaml.YAMLError as exc:
        logger.error("Failed to parse capability model: %s", exc)
        return "_Capability model could not be loaded._"

    capabilities = data.get("capabilities", [])
    if not capabilities:
        return "_No capabilities defined._"

    lines: list[str] = []
    for cap in capabilities:
        lines.extend(_render_capability_node(cap, 0, max_depth))

    return "\n".join(lines)


def load_glossary_summary(path: str, max_terms: int = 50) -> str:
    """Load glossary YAML and render as a term: definition list.

    Args:
        path: Path to enterprise-glossary.yaml.
        max_terms: Maximum number of terms to include.

    Returns:
        Markdown string of key terms.
    """
    try:
        data = _load_yaml(path)
    except FileNotFoundError:
        logger.warning("Glossary not found at %s", path)
        return "_Glossary not available._"
    except yaml.YAMLError as exc:
        logger.error("Failed to parse glossary: %s", exc)
        return "_Glossary could not be loaded._"

    terms = data.get("terms", [])
    if not terms:
        return "_No glossary terms defined._"

    lines: list[str] = []
    for term in terms[:max_terms]:
        name = term.get("term", term.get("name", ""))
        definition = term.get("definition", term.get("description", ""))
        if name and definition:
            lines.append(f"- **{name}**: {definition}")

    return "\n".join(lines) if lines else "_No glossary terms found._"
