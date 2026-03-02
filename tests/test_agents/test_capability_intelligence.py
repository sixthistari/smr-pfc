"""Tests for the capability intelligence agent (UC-4)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.capability_intelligence import (
    AGENT_ID,
    _load_work_items,
    run,
)
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_WORK_ITEMS = (
    Path(__file__).parent.parent / "fixtures" / "work_items" / "sample-work-items.yaml"
)


@pytest.fixture()
def agent_config() -> AgentConfig:
    return AgentConfig(
        id=AGENT_ID,
        name="Capability Intelligence Agent",
        use_case="UC-4",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/capability-intelligence.md",
        input_type="file",
        output_dir="output/intelligence",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _load_work_items
# ---------------------------------------------------------------------------

def test_load_work_items_from_file(tmp_path: Path) -> None:
    """Reads work items from a file path."""
    result = _load_work_items(str(tmp_path), str(FIXTURE_WORK_ITEMS))
    assert "work_items" in result
    assert "Safety Case Repository" in result


def test_load_work_items_missing(tmp_path: Path) -> None:
    """Returns placeholder when file does not exist."""
    result = _load_work_items(str(tmp_path), str(tmp_path / "nonexistent.yaml"))
    assert "not found" in result.lower()


def test_load_work_items_inline(tmp_path: Path) -> None:
    """Returns inline YAML string directly (non-path multi-line string)."""
    inline = "work_items:\n  - id: WI-001\n    title: Test Item\n"
    result = _load_work_items(str(tmp_path), inline)
    assert result == inline


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_writes_report(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() writes the capability intelligence report to output/intelligence/."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "capability-intelligence.md"
    prompt_file.write_text(
        "Analyse. Cap: {{CAPABILITY_MODEL}} Reg: {{ELEMENT_REGISTRY_SUMMARY}} "
        "Work: {{WORK_ITEMS}} Date: {{REPORT_DATE}}",
        encoding="utf-8",
    )

    report_output = (
        "# Capability Intelligence Report — 2026-03-02\n\n"
        "## Implied New Capabilities\n\n"
        "| Proposed Capability | Domain | Evidence | Priority |\n"
        "|---|---|---|---|\n"
        "| Safety Case Lifecycle Management | Safety | WI-001 | High |\n"
    )

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = report_output
        msg.usage = {"input_tokens": 500, "output_tokens": 250}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.capability_intelligence.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, str(FIXTURE_WORK_ITEMS), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID
    assert manifest.status == "completed"

    output_dir = tmp_path / "output" / "intelligence"
    output_files = list(output_dir.glob("capability-report-*.md"))
    assert len(output_files) == 1


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns failed status on SDK error."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)

    with patch(
        "ea_workbench.agents.capability_intelligence.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, str(FIXTURE_WORK_ITEMS), str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
