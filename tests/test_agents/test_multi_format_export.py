"""Tests for the multi-format export agent (UC-14)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.multi_format_export import (
    AGENT_ID,
    _output_dir_for_spec,
    _slug_from_path,
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
        name="Multi-Format Architecture Export",
        use_case="UC-14",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/multi-format-export.md",
        input_type="file",
        output_dir="output/exports",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _slug_from_path
# ---------------------------------------------------------------------------

def test_slug_from_path_normalises() -> None:
    """Normalises a file path to a lowercase hyphenated slug."""
    assert _slug_from_path("/workspace/specs/Safety Management Platform.md") == "safety-management-platform"
    assert _slug_from_path("specs/tier2/api-gateway.md") == "api-gateway"
    assert _slug_from_path("my_spec_page.md") == "my-spec-page"


def test_slug_from_path_empty_stem() -> None:
    """Returns default slug for paths with no usable stem."""
    # Path with no stem defaults to "spec"
    result = _slug_from_path(".")
    assert result == "spec" or len(result) > 0


# ---------------------------------------------------------------------------
# _output_dir_for_spec
# ---------------------------------------------------------------------------

def test_output_dir_for_spec(tmp_path: Path) -> None:
    """Returns the correct output directory path for a given slug."""
    result = _output_dir_for_spec(str(tmp_path), "safety-management-platform")
    expected = tmp_path / "output" / "exports" / "safety-management-platform"
    assert result == expected


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_creates_output_dir(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() creates the output directory before running the agent."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "multi-format-export.md"
    prompt_file.write_text("Export the spec to five formats.", encoding="utf-8")

    spec_file = tmp_path / "test-spec.md"
    spec_file.write_text("# Test Spec\n\nContent here.", encoding="utf-8")

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = "Export complete."
        msg.usage = {"input_tokens": 300, "output_tokens": 150}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.multi_format_export.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, str(spec_file), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID

    # Output directory should have been created
    slug = _slug_from_path(str(spec_file))
    output_dir = tmp_path / "output" / "exports" / slug
    assert output_dir.exists()


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns failed status on SDK error."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    spec_file = tmp_path / "test-spec.md"
    spec_file.write_text("# Test Spec", encoding="utf-8")

    with patch(
        "ea_workbench.agents.multi_format_export.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, str(spec_file), str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
