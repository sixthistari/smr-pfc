"""Tests for the stakeholder communication generator (UC-5)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.stakeholder_comms import (
    AGENT_ID,
    _load_spec_content,
    run,
)
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_SPEC = (
    Path(__file__).parent.parent / "fixtures" / "specs" / "sample-parent-spec.md"
)


@pytest.fixture()
def agent_config() -> AgentConfig:
    return AgentConfig(
        id=AGENT_ID,
        name="Stakeholder Communication Generator",
        use_case="UC-5",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/stakeholder-comms.md",
        input_type="file",
        output_dir="output/communications",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _load_spec_content
# ---------------------------------------------------------------------------

def test_load_spec_content_valid(tmp_path: Path) -> None:
    """Reads spec content from an existing file."""
    spec = tmp_path / "my-spec.md"
    spec.write_text("# My Spec\n\nContent here.", encoding="utf-8")
    result = _load_spec_content(str(tmp_path), str(spec))
    assert "My Spec" in result
    assert "Content here" in result


def test_load_spec_content_missing(tmp_path: Path) -> None:
    """Returns placeholder when spec file does not exist."""
    result = _load_spec_content(str(tmp_path), str(tmp_path / "nonexistent.md"))
    assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_creates_output_dir(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() creates the output/communications/{slug}/ directory."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "stakeholder-comms.md"
    prompt_file.write_text(
        "Generate comms. Spec: {{SPEC_CONTENT}}", encoding="utf-8"
    )

    spec_file = tmp_path / "safety-platform.md"
    spec_file.write_text("# Safety Platform\n\nContent.", encoding="utf-8")

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = "Three variants generated."
        msg.usage = {"input_tokens": 400, "output_tokens": 200}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.stakeholder_comms.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, str(spec_file), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID

    # Output directory should exist
    slug = "safety-platform"
    output_dir = tmp_path / "output" / "communications" / slug
    assert output_dir.exists()


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns failed status on SDK error."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    spec_file = tmp_path / "test-spec.md"
    spec_file.write_text("# Test", encoding="utf-8")

    with patch(
        "ea_workbench.agents.stakeholder_comms.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, str(spec_file), str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
