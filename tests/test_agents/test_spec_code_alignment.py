"""Tests for the spec-to-code alignment checker (UC-8)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.spec_code_alignment import (
    AGENT_ID,
    _parse_input_paths,
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
        name="Spec-to-Code Alignment Checker",
        use_case="UC-8",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/spec-code-alignment.md",
        input_type="file",
        output_dir="output/reviews",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _parse_input_paths
# ---------------------------------------------------------------------------

def test_parse_input_paths_with_separator() -> None:
    """Splits '::' separated prompt into diff and spec paths."""
    diff, spec = _parse_input_paths("/workspace/pr.diff::specs/tier2/api-gateway.md")
    assert diff == "/workspace/pr.diff"
    assert spec == "specs/tier2/api-gateway.md"


def test_parse_input_paths_no_separator() -> None:
    """Returns full prompt as diff_path and empty string as spec_path."""
    diff, spec = _parse_input_paths("/workspace/pr.diff")
    assert diff == "/workspace/pr.diff"
    assert spec == ""


def test_parse_input_paths_with_spaces() -> None:
    """Strips whitespace from paths."""
    diff, spec = _parse_input_paths("  /a/b.diff  ::  /c/d.md  ")
    assert diff == "/a/b.diff"
    assert spec == "/c/d.md"


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_writes_alignment_report(
    tmp_path: Path, agent_config: AgentConfig
) -> None:
    """run() writes the alignment report to output/reviews/."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "spec-code-alignment.md"
    prompt_file.write_text("Check alignment.", encoding="utf-8")

    diff_file = tmp_path / "pr.diff"
    diff_file.write_text("--- a/service.py\n+++ b/service.py\n+class NewService:", encoding="utf-8")
    spec_file = tmp_path / "spec.md"
    spec_file.write_text("# API Spec\n\n## Services\n\n- ExistingService", encoding="utf-8")

    alignment_output = (
        "# Spec-to-Code Alignment Report\n\n"
        "| New Services Not in Spec | 1 |\n"
    )

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = alignment_output
        msg.usage = {"input_tokens": 250, "output_tokens": 120}
        msg.is_error = False
        yield msg

    prompt_input = f"{diff_file}::{spec_file}"
    with patch(
        "ea_workbench.agents.spec_code_alignment.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, prompt_input, str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID

    output_dir = tmp_path / "output" / "reviews"
    output_files = list(output_dir.glob("alignment-*.md"))
    assert len(output_files) == 1


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns failed status on SDK error."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)

    with patch(
        "ea_workbench.agents.spec_code_alignment.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, "diff.txt::spec.md", str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
