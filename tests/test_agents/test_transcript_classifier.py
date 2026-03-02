"""Tests for the transcript classifier agent (UC-1)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.transcript_classifier import (
    AGENT_ID,
    _extract_yaml_block,
    _load_transcript,
    run,
)
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_TRANSCRIPT = (
    Path(__file__).parent.parent / "fixtures" / "transcripts" / "sample-transcript.txt"
)


@pytest.fixture()
def agent_config() -> AgentConfig:
    return AgentConfig(
        id=AGENT_ID,
        name="Transcript → ArchiMate Classifier",
        use_case="UC-1",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/transcript-classifier.md",
        input_type="file",
        output_dir=".staging/entities",
        extracts_entities=True,
        extracts_relationships=True,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _load_transcript
# ---------------------------------------------------------------------------

def test_load_transcript_valid() -> None:
    """Reads the fixture transcript file correctly."""
    content = _load_transcript(str(FIXTURE_TRANSCRIPT))
    assert len(content) > 50
    assert "Safety" in content


def test_load_transcript_missing(tmp_path: Path) -> None:
    """Returns placeholder string when file does not exist."""
    result = _load_transcript(str(tmp_path / "nonexistent.txt"))
    assert result == "(not found)"


# ---------------------------------------------------------------------------
# _extract_yaml_block
# ---------------------------------------------------------------------------

def test_extract_yaml_block_valid() -> None:
    """Parses YAML from a fenced block correctly."""
    text = """
Some preamble text.

```yaml
entities:
  - name: Safety Case Repository
    type: ApplicationComponent
    capability: Safety Management
relationships:
  - source: Safety Case Repository
    target: Incident Reporting System
    type: Association
```

Some follow-up text.
"""
    result = _extract_yaml_block(text)
    assert isinstance(result, dict)
    assert "entities" in result
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Safety Case Repository"
    assert "relationships" in result


def test_extract_yaml_block_no_block() -> None:
    """Returns empty dict when no YAML block is present."""
    result = _extract_yaml_block("Just plain text, no code blocks.")
    assert result == {}


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_returns_manifest(
    tmp_path: Path, agent_config: AgentConfig
) -> None:
    """run() returns a RunManifest with the correct agent_id."""
    # Set up workspace structure
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "transcript-classifier.md"
    prompt_file.write_text(
        "You are an extractor. Cap: {{CAPABILITY_MODEL}} Reg: {{ELEMENT_REGISTRY_SUMMARY}}",
        encoding="utf-8",
    )

    # Create a sample transcript in the workspace
    transcript_file = tmp_path / "sample.txt"
    transcript_file.write_text("Meeting about safety systems.", encoding="utf-8")

    sdk_output = """
```yaml
entities:
  - name: Safety Case Repository
    type: ApplicationComponent
    capability: Safety Management
relationships: []
```

## Classification Report
No issues.
"""

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = sdk_output
        msg.usage = {"input_tokens": 200, "output_tokens": 100}
        msg.is_error = False
        yield msg

    with patch("ea_workbench.agents.transcript_classifier.query", side_effect=lambda **kw: _fake_gen(**kw)):
        manifest = await run(agent_config, str(transcript_file), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID
    assert manifest.status == "completed"
    assert manifest.entities_extracted == 1

    # Staged file should exist
    staging_dir = tmp_path / ".staging" / "entities"
    staged_files = list(staging_dir.glob("transcript-classifier_*.yaml"))
    assert len(staged_files) == 1


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns a failed manifest when the SDK raises an exception."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    transcript_file = tmp_path / "sample.txt"
    transcript_file.write_text("Meeting transcript.", encoding="utf-8")

    with patch(
        "ea_workbench.agents.transcript_classifier.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, str(transcript_file), str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
