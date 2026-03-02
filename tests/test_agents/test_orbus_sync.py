"""Tests for the Orbus sync intelligence agent (UC-9)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.orbus_sync import (
    AGENT_ID,
    _load_completed_work_items,
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
        name="Orbus Sync Intelligence Agent",
        use_case="UC-9",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/orbus-sync.md",
        input_type="workspace",
        output_dir="output/orbus-sync",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _load_completed_work_items
# ---------------------------------------------------------------------------

def test_load_completed_work_items_empty(tmp_path: Path) -> None:
    """Returns placeholder when no work item directories exist."""
    result = _load_completed_work_items(str(tmp_path))
    assert "no completed" in result.lower()


def test_load_completed_work_items_reads_yaml(tmp_path: Path) -> None:
    """Reads work item YAML files from the work-items staging directory."""
    wi_dir = tmp_path / ".staging" / "work-items"
    wi_dir.mkdir(parents=True)
    (wi_dir / "WI-001.yaml").write_text(
        "id: WI-001\ntitle: Safety Case Repository\nstatus: completed\n",
        encoding="utf-8",
    )

    result = _load_completed_work_items(str(tmp_path))
    assert "WI-001" in result
    assert "Safety Case Repository" in result


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_writes_changeset(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() writes the change set to output/orbus-sync/."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "orbus-sync.md"
    prompt_file.write_text("Produce a change set.", encoding="utf-8")

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = "Change set analysis complete."
        msg.usage = {"input_tokens": 300, "output_tokens": 150}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.orbus_sync.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, ".", str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID

    output_dir = tmp_path / "output" / "orbus-sync"
    output_files = list(output_dir.glob("changeset-*.yaml"))
    assert len(output_files) == 1


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns failed status on SDK error."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)

    with patch(
        "ea_workbench.agents.orbus_sync.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, ".", str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
