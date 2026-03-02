"""Tests for the practice analytics utility."""

from pathlib import Path

import pytest
import yaml

from ea_workbench.utils.practice_analytics import (
    analyse_practice_artefacts,
    format_analytics_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_index(tmp_path: Path, practice_type: str, items: list[dict]) -> None:
    """Create a _index.yaml file for a practice type."""
    type_dir = tmp_path / "architecture" / practice_type
    type_dir.mkdir(parents=True, exist_ok=True)
    index_path = type_dir / "_index.yaml"
    with index_path.open("w", encoding="utf-8") as fh:
        yaml.dump({"items": items}, fh, default_flow_style=False, allow_unicode=True)


# ---------------------------------------------------------------------------
# analyse_practice_artefacts
# ---------------------------------------------------------------------------

def test_analyse_empty_workspace(tmp_path: Path) -> None:
    """Returns zero counts when no architecture directory exists."""
    result = analyse_practice_artefacts(str(tmp_path))
    assert result["totals_by_type"]["principles"] == 0
    assert result["totals_by_type"]["decisions"] == 0
    assert result["by_status"] == {}
    assert result["domain_coverage"] == []
    assert result["idea_to_decision_rate"] == 0.0


def test_analyse_with_principles(tmp_path: Path) -> None:
    """Counts principles correctly."""
    _make_index(tmp_path, "principles", [
        {"id": "PRIN-01", "title": "Reuse First", "status": "active", "domain": "technology"},
        {"id": "PRIN-02", "title": "Security by Design", "status": "active", "domain": "security"},
    ])
    result = analyse_practice_artefacts(str(tmp_path))
    assert result["totals_by_type"]["principles"] == 2
    assert "technology" in result["domain_coverage"]
    assert "security" in result["domain_coverage"]


def test_analyse_status_breakdown(tmp_path: Path) -> None:
    """Counts items by status correctly."""
    _make_index(tmp_path, "standards", [
        {"id": "STD-01", "title": "API Design", "status": "active"},
        {"id": "STD-02", "title": "Old Standard", "status": "deprecated"},
        {"id": "STD-03", "title": "Draft Standard", "status": "draft"},
    ])
    result = analyse_practice_artefacts(str(tmp_path))
    assert result["by_status"].get("active", 0) == 1
    assert result["by_status"].get("deprecated", 0) == 1
    assert result["by_status"].get("draft", 0) == 1


def test_analyse_idea_to_decision_rate(tmp_path: Path) -> None:
    """Computes idea-to-decision conversion rate."""
    _make_index(tmp_path, "ideas", [
        {"id": "IDEA-01", "title": "Safety AI", "status": "exploring"},
        {"id": "IDEA-02", "title": "Cost Optimisation", "status": "exploring"},
    ])
    _make_index(tmp_path, "decisions", [
        {"id": "ADR-001", "title": "Adopt Safety AI", "status": "accepted",
         "traces_to_idea": "IDEA-01"},
    ])
    result = analyse_practice_artefacts(str(tmp_path))
    # 1 decision traces to an idea out of 2 ideas → 0.5
    assert result["idea_to_decision_rate"] == 0.5


def test_format_analytics_report(tmp_path: Path) -> None:
    """format_analytics_report returns a non-empty markdown string."""
    _make_index(tmp_path, "principles", [
        {"id": "PRIN-01", "status": "active", "domain": "enterprise"},
    ])
    analytics = analyse_practice_artefacts(str(tmp_path))
    report = format_analytics_report(analytics)
    assert len(report) > 0
    assert "Artefacts by Type" in report
    assert "Principles" in report
