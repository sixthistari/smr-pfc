"""Tests for the design-time guardrail agent."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from ea_workbench.agents.guardrail import AGENT_ID, _load_index_summary, run
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def agent_config() -> AgentConfig:
    return AgentConfig(
        id=AGENT_ID,
        name="Design-Time Guardrail Agent",
        use_case="UC-7",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/guardrail.md",
        input_type="file",
        output_dir=".staging/work",
        extracts_entities=False,
        tools=["Read"],
    )


@pytest.fixture()
def fixture_spec(tmp_path: Path) -> Path:
    """A minimal spec file to check."""
    spec = tmp_path / "test-spec.md"
    spec.write_text(
        "---\nparent: index\ntitle: Test Spec\n---\n\n# Test Spec\n\nSome content.\n",
        encoding="utf-8",
    )
    return spec


# ---------------------------------------------------------------------------
# _load_index_summary
# ---------------------------------------------------------------------------

def test_load_index_summary_missing_file(tmp_path: Path) -> None:
    result = _load_index_summary(str(tmp_path / "nonexistent.yaml"))
    assert result == "(not available)"


def test_load_index_summary_empty_yaml(tmp_path: Path) -> None:
    index = tmp_path / "index.yaml"
    index.write_text("{}", encoding="utf-8")
    result = _load_index_summary(str(index))
    assert result == "(empty)"


def test_load_index_summary_populated(tmp_path: Path) -> None:
    index = tmp_path / "index.yaml"
    data = {
        "standards": ["STD-01", "STD-02", "STD-03"],
        "version": "1.0",
    }
    index.write_text(yaml.dump(data), encoding="utf-8")
    result = _load_index_summary(str(index))
    assert "standards" in result
    assert "STD-01" in result
    assert "version" in result


def test_load_index_summary_nested_dict(tmp_path: Path) -> None:
    index = tmp_path / "index.yaml"
    data = {"principles": {"PRIN-01": "Reuse first", "PRIN-02": "Simple is better"}}
    index.write_text(yaml.dump(data), encoding="utf-8")
    result = _load_index_summary(str(index))
    assert "principles" in result
    assert "2 entries" in result


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_writes_review_to_staging(
    tmp_path: Path, agent_config: AgentConfig, fixture_spec: Path
) -> None:
    """run() writes a review comment file to .staging/work/."""
    runs_dir = tmp_path / ".agents" / "runs"
    runs_dir.mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "guardrail.md"
    prompt_file.write_text("You are a guardrail. Review: {{STANDARDS_SUMMARY}}", encoding="utf-8")

    review_content = "## Guardrail Review\n\n### Findings\n\nNo issues found."

    with patch("ea_workbench.agents.guardrail.query") as mock_query:
        from claude_code_sdk import ResultMessage as _RM

        async def fake_query(*args, **kwargs):
            msg = MagicMock(spec=_RM)
            msg.result = review_content
            msg.usage = {"input_tokens": 100, "output_tokens": 50}
            msg.is_error = False
            yield msg

        mock_query.return_value = fake_query()
        mock_query.side_effect = None
        mock_query.__call__ = lambda *a, **kw: fake_query()

        # Patch query at module level
        with patch("ea_workbench.agents.guardrail.query", side_effect=lambda **kw: fake_query()):
            manifest = await run(agent_config, str(fixture_spec), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID

    # Verify review file written to .staging/work/
    work_dir = tmp_path / ".staging" / "work"
    work_files = list(work_dir.glob("guardrail_*.md"))
    assert len(work_files) == 1
    content = work_files[0].read_text(encoding="utf-8")
    assert len(content) > 0


@pytest.mark.asyncio
async def test_run_sdk_error_still_writes_file(
    tmp_path: Path, agent_config: AgentConfig, fixture_spec: Path
) -> None:
    """Even if the SDK fails, a fallback review file is written."""
    runs_dir = tmp_path / ".agents" / "runs"
    runs_dir.mkdir(parents=True)

    with patch("ea_workbench.agents.guardrail.query", side_effect=RuntimeError("SDK unavailable")):
        manifest = await run(agent_config, str(fixture_spec), str(tmp_path))

    assert manifest.status == "failed"
    work_dir = tmp_path / ".staging" / "work"
    work_files = list(work_dir.glob("guardrail_*.md"))
    assert len(work_files) == 1
