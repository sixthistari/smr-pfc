"""Tests for the NFR compliance report generator (UC-10)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.nfr_compliance import (
    AGENT_ID,
    _count_status,
    _load_nfr_baseline,
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
        name="NFR Compliance Report Generator",
        use_case="UC-10",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/nfr-compliance.md",
        input_type="file",
        output_dir="output/compliance",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _load_nfr_baseline
# ---------------------------------------------------------------------------

def test_load_nfr_baseline_missing(tmp_path: Path) -> None:
    """Returns placeholder when NFR baseline file does not exist."""
    result = _load_nfr_baseline(str(tmp_path))
    assert "not found" in result.lower()


def test_load_nfr_baseline_from_file(tmp_path: Path) -> None:
    """Reads NFR baseline from file when it exists."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    baseline = specs_dir / "_nfr_index.yaml"
    baseline.write_text(
        "availability: 99.9%\nresponse_time_p95: 500ms\nerror_rate: 0.1%\n",
        encoding="utf-8",
    )

    result = _load_nfr_baseline(str(tmp_path))
    assert "availability" in result
    assert "99.9%" in result


# ---------------------------------------------------------------------------
# _count_status
# ---------------------------------------------------------------------------

def test_count_status() -> None:
    """Counts pass/warn/fail occurrences in result text."""
    text = "| Availability | 99.9% | 99.95% | pass | ↑ |\n| Response Time | <500ms | 480ms | pass | → |\n| Error Rate | <0.1% | 0.15% | fail | ↓ |"
    pass_count, warn_count, fail_count = _count_status(text)
    assert pass_count == 2
    assert fail_count == 1


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_writes_scorecard(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() writes the NFR compliance scorecard to output/compliance/."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "nfr-compliance.md"
    prompt_file.write_text("Assess NFRs. Baseline: {{NFR_BASELINE}}", encoding="utf-8")

    spec_file = tmp_path / "solution-spec.md"
    spec_file.write_text(
        "# Solution Spec\n\n## NFRs\n\n- Availability: 99.9%\n- Response: <500ms\n",
        encoding="utf-8",
    )

    scorecard_output = (
        "# NFR Compliance Scorecard — 2026-03-02\n\n"
        "| Availability | 99.9% | 99.95% | pass | ↑ |\n"
        "| Response Time | <500ms | 480ms | pass | → |\n"
    )

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = scorecard_output
        msg.usage = {"input_tokens": 250, "output_tokens": 120}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.nfr_compliance.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, str(spec_file), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID

    output_dir = tmp_path / "output" / "compliance"
    output_files = list(output_dir.glob("nfr-*.md"))
    assert len(output_files) == 1


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns failed status on SDK error."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    spec_file = tmp_path / "spec.md"
    spec_file.write_text("# Spec\n", encoding="utf-8")

    with patch(
        "ea_workbench.agents.nfr_compliance.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, str(spec_file), str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
