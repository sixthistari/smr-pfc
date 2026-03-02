"""Tests for the spec decomposition agent."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ea_workbench.agents.spec_decomposition import (
    AGENT_ID,
    _load_parent_page,
    _load_wiki_tree,
    run,
)
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "specs"


@pytest.fixture()
def agent_config() -> AgentConfig:
    return AgentConfig(
        id=AGENT_ID,
        name="Spec Decomposition Agent",
        use_case="UC-6",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/spec-decomposition.md",
        input_type="file",
        output_dir="specs/tier2",
        extracts_entities=True,
        tools=["Read", "Write"],
    )


@pytest.fixture()
def workspace_with_spec(tmp_path: Path) -> tuple[Path, Path]:
    """Set up a minimal workspace with a parent spec."""
    (tmp_path / ".agents" / "runs").mkdir(parents=True)
    (tmp_path / ".agents" / "prompts").mkdir(parents=True)
    (tmp_path / "specs" / "tier1").mkdir(parents=True)
    (tmp_path / "specs" / "tier2").mkdir(parents=True)

    # Copy fixture spec into workspace
    fixture_spec = FIXTURES_DIR / "sample-parent-spec.md"
    spec_content = fixture_spec.read_text(encoding="utf-8") if fixture_spec.exists() else "# Parent Spec\n\nContent."
    parent_spec = tmp_path / "specs" / "tier1" / "iam.md"
    parent_spec.write_text(spec_content, encoding="utf-8")

    # Minimal prompt file
    prompt = tmp_path / ".agents" / "prompts" / "spec-decomposition.md"
    prompt.write_text(
        "Decompose the spec. Parent: {{PARENT_PAGE_CONTENT}} Tree: {{WIKI_TREE_SUMMARY}} "
        "Caps: {{CAPABILITY_MODEL}} Registry: {{ELEMENT_REGISTRY_SUMMARY}}",
        encoding="utf-8",
    )

    return tmp_path, parent_spec


# ---------------------------------------------------------------------------
# _load_wiki_tree
# ---------------------------------------------------------------------------

def test_load_wiki_tree_empty_workspace(tmp_path: Path) -> None:
    result = _load_wiki_tree(str(tmp_path))
    assert "not found" in result or "empty" in result


def test_load_wiki_tree_with_files(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "index.md").write_text("# Index")
    tier1 = specs / "tier1"
    tier1.mkdir()
    (tier1 / "iam.md").write_text("# IAM")

    result = _load_wiki_tree(str(tmp_path), max_depth=2)
    assert "specs/" in result
    assert "index.md" in result
    assert "iam.md" in result


def test_load_wiki_tree_respects_max_depth(tmp_path: Path) -> None:
    """Files deeper than max_depth are excluded."""
    specs = tmp_path / "specs"
    deep = specs / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (specs / "top.md").write_text("# top")
    (deep / "deep.md").write_text("# deep")

    result = _load_wiki_tree(str(tmp_path), max_depth=1)
    assert "top.md" in result
    assert "deep.md" not in result


# ---------------------------------------------------------------------------
# _load_parent_page
# ---------------------------------------------------------------------------

def test_load_parent_page_existing_file(tmp_path: Path) -> None:
    spec = tmp_path / "my-spec.md"
    spec.write_text("# My Spec\n\nContent.", encoding="utf-8")
    result = _load_parent_page(str(tmp_path), "my-spec.md")
    assert "My Spec" in result


def test_load_parent_page_missing_file(tmp_path: Path) -> None:
    result = _load_parent_page(str(tmp_path), "nonexistent.md")
    assert "not found" in result.lower() or "nonexistent" in result


# ---------------------------------------------------------------------------
# run() — mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_returns_manifest(
    workspace_with_spec: tuple[Path, Path], agent_config: AgentConfig
) -> None:
    """run() returns a RunManifest."""
    tmp_path, parent_spec = workspace_with_spec

    with patch("ea_workbench.agents.spec_decomposition.query", side_effect=lambda **kw: _empty_gen()):
        manifest = await run(agent_config, str(parent_spec), str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID
    assert manifest.status == "completed"


@pytest.mark.asyncio
async def test_run_sdk_error_status_failed(
    workspace_with_spec: tuple[Path, Path], agent_config: AgentConfig
) -> None:
    """SDK error results in failed status manifest."""
    tmp_path, parent_spec = workspace_with_spec

    with patch(
        "ea_workbench.agents.spec_decomposition.query",
        side_effect=RuntimeError("SDK unavailable"),
    ):
        manifest = await run(agent_config, str(parent_spec), str(tmp_path))

    assert manifest.status == "failed"
    assert manifest.error is not None


async def _empty_gen():
    """Empty async generator to simulate no SDK messages."""
    return
    yield
