"""Practice artefact analytics utility.

Pure Python — reads all practice _index.yaml files and computes artefact
lifecycle metrics without any LLM. Used by the /analytics chat command.
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_PRACTICE_TYPES = [
    "principles",
    "standards",
    "decisions",
    "nfrs",
    "ideas",
    "strategies",
]


def analyse_practice_artefacts(workspace: str) -> dict:
    """Walk practice directories and compute artefact lifecycle metrics.

    Reads _index.yaml files from each practice type directory under
    `{workspace}/architecture/`. Computes:
    - totals_by_type: count per type
    - by_status: count per status value
    - domain_coverage: set of domains referenced
    - idea_to_decision_rate: ideas that have a corresponding decision

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Dict with keys: totals_by_type, by_status, domain_coverage,
        idea_to_decision_rate.
    """
    arch_dir = Path(workspace) / "architecture"

    totals_by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    domains: set[str] = set()
    idea_ids: set[str] = set()
    decision_ids: set[str] = set()
    idea_to_decision_count = 0

    for practice_type in _PRACTICE_TYPES:
        type_dir = arch_dir / practice_type
        index_path = type_dir / "_index.yaml"

        if not index_path.exists():
            totals_by_type[practice_type] = 0
            continue

        try:
            with index_path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except Exception as exc:
            logger.warning("Could not read %s: %s", index_path, exc)
            totals_by_type[practice_type] = 0
            continue

        if not isinstance(data, dict):
            totals_by_type[practice_type] = 0
            continue

        # Count items in the index
        items = data.get("items", data.get(practice_type, []))
        if isinstance(items, list):
            totals_by_type[practice_type] = len(items)

            for item in items:
                if not isinstance(item, dict):
                    continue

                # Track status
                status = item.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1

                # Track domains
                domain = item.get("domain", item.get("domains", None))
                if isinstance(domain, str) and domain:
                    domains.add(domain)
                elif isinstance(domain, list):
                    domains.update(d for d in domain if isinstance(d, str))

                # Track ideas and decisions for ratio
                item_id = str(item.get("id", ""))
                if practice_type == "ideas" and item_id:
                    idea_ids.add(item_id)
                elif practice_type == "decisions" and item_id:
                    decision_ids.add(item_id)
                    # Check if this decision traces to an idea
                    traces_to = item.get("traces_to_idea", item.get("idea_id", ""))
                    if traces_to:
                        idea_to_decision_count += 1
        else:
            totals_by_type[practice_type] = 0

    # Compute idea → decision conversion rate
    idea_count = len(idea_ids)
    idea_to_decision_rate = (
        round(idea_to_decision_count / idea_count, 2) if idea_count > 0 else 0.0
    )

    return {
        "totals_by_type": totals_by_type,
        "by_status": by_status,
        "domain_coverage": sorted(domains),
        "idea_to_decision_rate": idea_to_decision_rate,
    }


def format_analytics_report(analytics: dict) -> str:
    """Render the analytics dict as a markdown table for display.

    Args:
        analytics: Output from analyse_practice_artefacts().

    Returns:
        Markdown-formatted report string.
    """
    totals = analytics.get("totals_by_type", {})
    by_status = analytics.get("by_status", {})
    domains = analytics.get("domain_coverage", [])
    idea_rate = analytics.get("idea_to_decision_rate", 0.0)

    lines = ["**Practice Artefact Analytics**", ""]

    # Artefact counts by type
    lines.append("## Artefacts by Type")
    lines.append("")
    lines.append("| Type | Count |")
    lines.append("|---|---|")
    for ptype in _PRACTICE_TYPES:
        count = totals.get(ptype, 0)
        lines.append(f"| {ptype.capitalize()} | {count} |")
    lines.append("")

    # Status breakdown
    if by_status:
        lines.append("## Status Breakdown")
        lines.append("")
        lines.append("| Status | Count |")
        lines.append("|---|---|")
        for status, count in sorted(by_status.items()):
            lines.append(f"| {status} | {count} |")
        lines.append("")

    # Domain coverage
    domain_str = ", ".join(domains) if domains else "(none recorded)"
    lines.append(f"## Domain Coverage")
    lines.append("")
    lines.append(f"**Domains:** {domain_str}")
    lines.append("")

    # Idea to decision rate
    rate_pct = f"{idea_rate * 100:.0f}%"
    lines.append(f"## Idea → Decision Conversion Rate")
    lines.append("")
    lines.append(f"**Rate:** {rate_pct}")

    return "\n".join(lines)
