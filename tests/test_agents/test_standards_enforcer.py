"""Tests for the standards & patterns register enforcer (UC-15)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.standards_enforcer import (
    AGENT_ID,
    _load_standards_register,
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
        name="Standards & Patterns Register Enforcer",
        use_case="UC-15",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/standards-enforcer.md",
        input_type="file",
        output_dir="output/reviews",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _load_standards_register
# ---------------------------------------------------------------------------

def test_load_standards_register_missing(tmp_path: Path) -> None:
    """Returns placeholder when standards index does not exist."""
    result = _load_standards_register(str(tmp_path))
    assert "not found" in result.lower()


def test_load_standards_register_from_file(tmp_path: Path) -> None:
    """Reads standards register from file when it exists."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    index = specs_dir / "_standards_index.yaml"
    index.write_text(
        "standards:\n  STD-01: API Design\n  STD-02: Security\n  STD-03: Event Sourcing\n",
        encoding="utf-8",
    )

    result = _load_standards_register(str(tmp_path))
    assert "STD-01" in result
    assert "API Design" in result


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_writes_report(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() writes the standards applicability report to output/reviews/."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "standards-enforcer.md"
    prompt_file.write_text(
        "Enforce standards. Register: {{STANDARDS_REGISTER_SUMMARY}}", encoding="utf-8"
    )

    spec_file = tmp_path / "solution-spec.md"
    spec_file.write_text(
        "# Solution Spec\n\n## Architecture\n\nREST API with event sourcing.\n",
        encoding="utf-8",
    )

    report_output = (
        "# Standards & Patterns Applicability Report\n\n"
        "| API Gateway Pattern | STD-03 | applicable | ✅ covered | ... |\n"
    )

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = report_output
        msg.usage = {"input_tokens": 400, "output_tokens": 200}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.standards_enforcer.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, str(spec_file), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID

    output_dir = tmp_path / "output" / "reviews"
    output_files = list(output_dir.glob("standards-*.md"))
    assert len(output_files) == 1


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns failed status on SDK error."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    spec_file = tmp_path / "spec.md"
    spec_file.write_text("# Spec\n", encoding="utf-8")

    with patch(
        "ea_workbench.agents.standards_enforcer.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, str(spec_file), str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
