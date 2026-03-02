"""Tests for the architecture review gate agent (UC-3)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.architecture_review import (
    AGENT_ID,
    _load_nfr_summary,
    _load_standards_summary,
    run,
)
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def agent_config() -> AgentConfig:
    return AgentConfig(
        id=AGENT_ID,
        name="Architecture Review Gate Agent",
        use_case="UC-3",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/architecture-review.md",
        input_type="file",
        output_dir="output/reviews",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def test_load_standards_summary_missing(tmp_path: Path) -> None:
    """Returns placeholder when standards index does not exist."""
    result = _load_standards_summary(str(tmp_path))
    assert "not found" in result.lower()


def test_load_standards_summary_from_file(tmp_path: Path) -> None:
    """Reads standards summary from file when it exists."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    index = specs_dir / "_standards_index.yaml"
    index.write_text("standards:\n  STD-01: API Design\n  STD-02: Security\n", encoding="utf-8")
    result = _load_standards_summary(str(tmp_path))
    assert "STD-01" in result


def test_load_nfr_summary_missing(tmp_path: Path) -> None:
    """Returns placeholder when NFR index does not exist."""
    result = _load_nfr_summary(str(tmp_path))
    assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_writes_report(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() writes the review report to output/reviews/."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "architecture-review.md"
    prompt_file.write_text(
        "Review. Standards: {{STANDARDS_SUMMARY}} NFR: {{NFR_SUMMARY}}", encoding="utf-8"
    )

    input_file = tmp_path / "pr-diff.md"
    input_file.write_text("diff --git a/service.py...", encoding="utf-8")

    review_output = (
        "# Architecture Review Report\n\n"
        "| Check | STD-01 | ✅ pass | Meets standard | None |\n"
    )

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = review_output
        msg.usage = {"input_tokens": 300, "output_tokens": 150}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.architecture_review.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, str(input_file), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID

    output_dir = tmp_path / "output" / "reviews"
    output_files = list(output_dir.glob("arch-review-*.md"))
    assert len(output_files) == 1


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns failed status on SDK error."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    input_file = tmp_path / "pr-diff.md"
    input_file.write_text("diff content", encoding="utf-8")

    with patch(
        "ea_workbench.agents.architecture_review.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, str(input_file), str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
