"""Tests for the use-case assessment agent (UC-2)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.use_case_assessment import (
    AGENT_ID,
    _DEFAULT_CRITERIA,
    _extract_recommendation,
    _load_assessment_criteria,
    run,
)
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_SUBMISSION = (
    Path(__file__).parent.parent / "fixtures" / "submissions" / "sample-submission.md"
)


@pytest.fixture()
def agent_config() -> AgentConfig:
    return AgentConfig(
        id=AGENT_ID,
        name="Use-Case Assessment Agent",
        use_case="UC-2",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/use-case-assessment.md",
        input_type="file",
        output_dir="output/assessments",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _load_assessment_criteria
# ---------------------------------------------------------------------------

def test_load_assessment_criteria_missing(tmp_path: Path) -> None:
    """Returns default criteria string when file does not exist."""
    result = _load_assessment_criteria(str(tmp_path))
    assert result == _DEFAULT_CRITERIA


def test_load_assessment_criteria_from_file(tmp_path: Path) -> None:
    """Reads criteria from file when it exists."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    criteria_file = specs_dir / "_assessment-criteria.md"
    criteria_file.write_text("# Custom Criteria\n\n- Criterion A\n", encoding="utf-8")

    result = _load_assessment_criteria(str(tmp_path))
    assert "Custom Criteria" in result
    assert "Criterion A" in result


# ---------------------------------------------------------------------------
# _extract_recommendation
# ---------------------------------------------------------------------------

def test_extract_recommendation_approve() -> None:
    """Extracts 'Approve' from output text."""
    text = "After careful analysis...\n\n## Recommendation: Approve\n\nThis meets criteria."
    assert _extract_recommendation(text) == "Approve"


def test_extract_recommendation_none() -> None:
    """Returns 'unknown' when no recommendation keyword is found."""
    text = "## Assessment\n\nThe submission is incomplete."
    assert _extract_recommendation(text) == "unknown"


def test_extract_recommendation_conditional() -> None:
    """Extracts 'Conditional' from output text."""
    text = "## Recommendation: Conditional — address PII handling first."
    assert _extract_recommendation(text) == "Conditional"


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_writes_assessment(
    tmp_path: Path, agent_config: AgentConfig
) -> None:
    """run() writes the assessment file to output/assessments/."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "use-case-assessment.md"
    prompt_file.write_text(
        "Assess. Roadmap: {{ROADMAP_SUMMARY}} Criteria: {{ASSESSMENT_CRITERIA}}",
        encoding="utf-8",
    )

    assessment_output = (
        "## Executive Summary\n\nStrong submission.\n\n"
        "## Recommendation: Approve\n\nMeets all criteria."
    )

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = assessment_output
        msg.usage = {"input_tokens": 400, "output_tokens": 200}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.use_case_assessment.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, str(FIXTURE_SUBMISSION), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID
    assert manifest.summary["recommendation"] == "Approve"

    output_dir = tmp_path / "output" / "assessments"
    output_files = list(output_dir.glob("*-assessment.md"))
    assert len(output_files) == 1


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns failed status on SDK error."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)

    with patch(
        "ea_workbench.agents.use_case_assessment.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, str(FIXTURE_SUBMISSION), str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
