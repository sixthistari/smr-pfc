"""Tests for the weekly summary agent."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from ea_workbench.agents.weekly_summary import (
    AGENT_ID,
    _format_sessions_text,
    _load_agent_run_summary,
    _load_session_records,
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
        name="Weekly Summary Agent",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/weekly-summary.md",
        input_type="workspace",
        output_dir="output/weekly-summaries",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _load_session_records
# ---------------------------------------------------------------------------

def test_load_session_records_empty_dir(tmp_path: Path) -> None:
    """Returns empty list when no session files exist."""
    result = _load_session_records(str(tmp_path))
    assert result == []


def test_load_session_records_reads_yaml(tmp_path: Path) -> None:
    """Reads YAML session files and returns parsed dicts."""
    sessions_dir = tmp_path / ".staging" / "sessions"
    sessions_dir.mkdir(parents=True)

    record = {
        "session_id": "abc-123",
        "started_at": "2026-02-15T09:00:00Z",
        "ended_at": "2026-02-15T10:00:00Z",
        "summary": "Discussed safety platform architecture",
        "topics_discussed": ["safety", "architecture"],
    }
    (sessions_dir / "abc-123.yaml").write_text(yaml.dump(record), encoding="utf-8")

    result = _load_session_records(str(tmp_path))
    assert len(result) == 1
    assert result[0]["session_id"] == "abc-123"


# ---------------------------------------------------------------------------
# _load_agent_run_summary
# ---------------------------------------------------------------------------

def test_load_agent_run_summary_reads_json(tmp_path: Path) -> None:
    """Reads JSON run manifest files and returns summary fields."""
    runs_dir = tmp_path / ".agents" / "runs"
    runs_dir.mkdir(parents=True)

    manifest = {
        "agent_id": "wiki-integrity",
        "run_id": "abc12345",
        "status": "completed",
        "timestamp": "2026-02-15T08:00:00Z",
        "tokens_consumed": 500,
        "entities_extracted": 0,
    }
    (runs_dir / "wiki-integrity_abc12345.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = _load_agent_run_summary(str(tmp_path))
    assert len(result) == 1
    assert result[0]["agent_id"] == "wiki-integrity"
    assert result[0]["status"] == "completed"


# ---------------------------------------------------------------------------
# _format_sessions_text
# ---------------------------------------------------------------------------

def test_format_sessions_text_non_empty() -> None:
    """Returns a non-empty formatted string from session records."""
    records = [
        {
            "session_id": "sess-1",
            "started_at": "2026-02-15T09:00:00Z",
            "summary": "Reviewed safety spec",
        }
    ]
    result = _format_sessions_text(records)
    assert len(result) > 0
    assert "sess-1" in result
    assert "Reviewed safety spec" in result


def test_format_sessions_text_empty() -> None:
    """Returns placeholder when no records provided."""
    result = _format_sessions_text([])
    assert "no session records" in result.lower()


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_writes_output_file(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() writes the weekly summary markdown to output/weekly-summaries/."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "weekly-summary.md"
    prompt_file.write_text(
        "Summarise. Sessions: {{SESSION_RECORDS}} Runs: {{AGENT_RUN_SUMMARY}}",
        encoding="utf-8",
    )

    summary_content = "# EA Week in Review\n\n## Key Decisions\n\n- Decision 1"

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = summary_content
        msg.usage = {"input_tokens": 300, "output_tokens": 150}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.weekly_summary.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, ".", str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID

    output_dir = tmp_path / "output" / "weekly-summaries"
    output_files = list(output_dir.glob("week-*.md"))
    assert len(output_files) == 1


@pytest.mark.asyncio
async def test_run_empty_sessions_completes(
    tmp_path: Path, agent_config: AgentConfig
) -> None:
    """run() completes without error when there are no session records."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = "# Week in Review\n\nNothing to report."
        msg.usage = {"input_tokens": 50, "output_tokens": 30}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.weekly_summary.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, ".", str(tmp_path))

    assert manifest.status == "completed"
    assert manifest.summary["sessions_included"] == 0
