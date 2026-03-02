"""Tests for the batch agent runner."""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ea_workbench.agents.base import write_manifest
from ea_workbench.agents.runner import load_config, load_prompt, resolve_agent, run_batch_agent
from ea_workbench.models.manifests import RunManifest


def _make_config_yaml(tmp_path: Path) -> str:
    """Write a minimal config.yaml and return its path."""
    config_content = """
version: "1.0"
defaults:
  endpoint: ""
  judgment_model: "claude-sonnet-4-6"
  extraction_model: "gemini-2.5-flash"
  authoring_model: "claude-sonnet-4-6"
agents:
  test-agent:
    id: "test-agent"
    name: "Test Agent"
    model: "claude-sonnet-4-6"
    prompt: ".agents/prompts/test-agent.md"
    extracts_entities: false
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    return str(config_path)


def _make_workspace(tmp_path: Path) -> str:
    """Set up a minimal workspace structure."""
    workspace = tmp_path / "workspace"
    (workspace / ".agents" / "prompts").mkdir(parents=True)
    (workspace / ".agents" / "runs").mkdir(parents=True)
    prompt_file = workspace / ".agents" / "prompts" / "test-agent.md"
    prompt_file.write_text("# Role\nYou are a test agent. Respond with 'Hello test.'")
    return str(workspace)


def test_load_config_valid(tmp_path: Path) -> None:
    """load_config parses and validates a config.yaml."""
    config_path = _make_config_yaml(tmp_path)
    config = load_config(config_path)
    assert "test-agent" in config.agents
    assert config.defaults.judgment_model == "claude-sonnet-4-6"


def test_load_config_missing_file(tmp_path: Path) -> None:
    """load_config raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        load_config(str(tmp_path / "nonexistent.yaml"))


def test_resolve_agent_found(tmp_path: Path) -> None:
    """resolve_agent returns the correct AgentConfig."""
    config_path = _make_config_yaml(tmp_path)
    config = load_config(config_path)
    agent = resolve_agent(config, "test-agent")
    assert agent.id == "test-agent"


def test_resolve_agent_not_found(tmp_path: Path) -> None:
    """resolve_agent raises KeyError for unknown agent."""
    config_path = _make_config_yaml(tmp_path)
    config = load_config(config_path)
    with pytest.raises(KeyError, match="unknown-agent"):
        resolve_agent(config, "unknown-agent")


def test_load_prompt_valid(tmp_path: Path) -> None:
    """load_prompt reads a prompt file."""
    prompt_file = tmp_path / "test.md"
    prompt_file.write_text("# Role\nYou are a test agent.")
    content = load_prompt(str(prompt_file))
    assert "test agent" in content


def test_load_prompt_missing(tmp_path: Path) -> None:
    """load_prompt raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        load_prompt(str(tmp_path / "missing.md"))


def test_write_manifest(tmp_path: Path) -> None:
    """write_manifest creates a JSON file in runs_dir."""
    runs_dir = str(tmp_path / "runs")
    manifest = RunManifest(
        agent_id="test-agent",
        run_id="abc12345",
        triggered_by="manual",
        timestamp="2026-03-02T10:00:00Z",
        duration_seconds=1.5,
        model_used="claude-sonnet-4-6",
        tokens_consumed=100,
        status="completed",
        inputs=["input.md"],
        outputs=["output.md"],
    )
    path = write_manifest(manifest, runs_dir)
    assert os.path.exists(path)
    with open(path) as fh:
        data = json.load(fh)
    assert data["agent_id"] == "test-agent"
    assert data["run_id"] == "abc12345"


async def test_run_batch_agent_config_not_found(tmp_path: Path) -> None:
    """run_batch_agent returns failed manifest when config is missing."""
    manifest = await run_batch_agent(
        agent_id="test-agent",
        prompt="test input",
        workspace=str(tmp_path / "workspace"),
        config_path=str(tmp_path / "nonexistent.yaml"),
    )
    assert manifest.status == "failed"
    assert manifest.error is not None


async def test_run_batch_agent_agent_not_found(tmp_path: Path) -> None:
    """run_batch_agent returns failed manifest when agent ID is not in config."""
    config_path = _make_config_yaml(tmp_path)
    workspace = _make_workspace(tmp_path)
    manifest = await run_batch_agent(
        agent_id="nonexistent-agent",
        prompt="test",
        workspace=workspace,
        config_path=config_path,
    )
    assert manifest.status == "failed"
    assert "nonexistent-agent" in (manifest.error or "")


async def test_run_batch_agent_sdk_mocked(tmp_path: Path) -> None:
    """run_batch_agent succeeds when SDK query is mocked."""
    from claude_code_sdk import ResultMessage

    config_path = _make_config_yaml(tmp_path)
    workspace = _make_workspace(tmp_path)

    mock_result = MagicMock(spec=ResultMessage)
    mock_result.result = "Agent ran successfully."
    mock_result.is_error = False
    mock_result.usage = {"input_tokens": 100, "output_tokens": 50}

    async def mock_query(*args: object, **kwargs: object):  # type: ignore[return]
        yield mock_result

    with patch("ea_workbench.agents.runner.query", side_effect=mock_query):
        manifest = await run_batch_agent(
            agent_id="test-agent",
            prompt="process this input",
            workspace=workspace,
            config_path=config_path,
        )

    assert manifest.status == "completed"
    assert manifest.tokens_consumed == 150
    assert manifest.agent_id == "test-agent"
    # Verify manifest was written to disk
    runs_dir = os.path.join(workspace, ".agents", "runs")
    manifest_files = os.listdir(runs_dir)
    assert any("test-agent" in f for f in manifest_files)
