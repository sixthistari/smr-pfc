"""Tests for the domain knowledge spec drafter (UC-11)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.domain_knowledge_spec import (
    AGENT_ID,
    _DEFAULT_TEMPLATE,
    _load_spec_template,
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
        name="Domain Knowledge Spec Drafter",
        use_case="UC-11",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/domain-knowledge-spec.md",
        input_type="file",
        output_dir="output/specs",
        extracts_entities=False,
        tools=["Read", "Write"],
    )


# ---------------------------------------------------------------------------
# _load_spec_template
# ---------------------------------------------------------------------------

def test_load_spec_template_missing(tmp_path: Path) -> None:
    """Returns default template when custom template file does not exist."""
    result = _load_spec_template(str(tmp_path))
    assert result == _DEFAULT_TEMPLATE


def test_load_spec_template_from_file(tmp_path: Path) -> None:
    """Reads template from custom file when it exists."""
    templates_dir = tmp_path / "specs" / "_templates"
    templates_dir.mkdir(parents=True)
    template_file = templates_dir / "domain-knowledge-spec.md"
    template_file.write_text("# Custom Template\n\n{{DOMAIN_NAME}}", encoding="utf-8")

    result = _load_spec_template(str(tmp_path))
    assert "Custom Template" in result


# ---------------------------------------------------------------------------
# run() — with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_writes_spec(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() writes the draft spec to output/specs/dk-{slug}.md."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    prompt_file = tmp_path / ".agents" / "prompts" / "domain-knowledge-spec.md"
    prompt_file.write_text("Draft a domain knowledge spec.", encoding="utf-8")

    source_file = tmp_path / "safety-data-sources.yaml"
    source_file.write_text("domain: safety\nsources:\n  - IRS\n", encoding="utf-8")

    draft_content = "---\ntitle: Safety — Domain Knowledge Spec\n---\n\n# Safety DK Spec"

    async def _fake_gen(**kwargs):
        msg = MagicMock(spec=__import__("claude_code_sdk").ResultMessage)
        msg.result = draft_content
        msg.usage = {"input_tokens": 300, "output_tokens": 150}
        msg.is_error = False
        yield msg

    with patch(
        "ea_workbench.agents.domain_knowledge_spec.query",
        side_effect=lambda **kw: _fake_gen(**kw),
    ):
        manifest = await run(agent_config, str(source_file), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID

    output_dir = tmp_path / "output" / "specs"
    output_files = list(output_dir.glob("dk-*.md"))
    assert len(output_files) == 1


@pytest.mark.asyncio
async def test_run_sdk_error(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() returns failed status on SDK error."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    source_file = tmp_path / "source.yaml"
    source_file.write_text("domain: test\n", encoding="utf-8")

    with patch(
        "ea_workbench.agents.domain_knowledge_spec.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, str(source_file), str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None
