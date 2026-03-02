"""Tests for the wiki integrity agent."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ea_workbench.agents.wiki_integrity import AGENT_ID, _check_page, _scan_specs, run
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def valid_spec(tmp_path: Path) -> Path:
    """A well-formed spec page with a parent link in frontmatter."""
    specs = tmp_path / "specs" / "tier1"
    specs.mkdir(parents=True)
    page = specs / "my-spec.md"
    page.write_text(
        "---\nparent: index\ntitle: My Spec\n---\n\n# My Spec\n\nSome content here.\n",
        encoding="utf-8",
    )
    return page


@pytest.fixture()
def missing_parent_spec(tmp_path: Path) -> Path:
    """A spec page with no parent reference."""
    specs = tmp_path / "specs" / "tier1"
    specs.mkdir(parents=True)
    page = specs / "orphan.md"
    page.write_text("# Orphan Page\n\nNo parent link here.\n", encoding="utf-8")
    return page


@pytest.fixture()
def oversized_spec(tmp_path: Path) -> Path:
    """A spec page with more than 300 lines — triggers oversized-page."""
    specs = tmp_path / "specs" / "tier1"
    specs.mkdir(parents=True)
    page = specs / "big-spec.md"
    lines = ["---", "parent: index", "---", "# Big Spec", ""]
    lines += [f"Line {i}" for i in range(310)]
    page.write_text("\n".join(lines), encoding="utf-8")
    return page


@pytest.fixture()
def agent_config() -> AgentConfig:
    return AgentConfig(
        id=AGENT_ID,
        name="Wiki Structure Integrity Agent",
        use_case="UC-13",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/wiki-integrity.md",
        input_type="workspace",
        output_dir=".agents/runs",
        extracts_entities=False,
        tools=["Read"],
    )


# ---------------------------------------------------------------------------
# _scan_specs
# ---------------------------------------------------------------------------

def test_scan_specs_empty_workspace(tmp_path: Path) -> None:
    """Returns empty list when specs/ does not exist."""
    result = _scan_specs(str(tmp_path))
    assert result == []


def test_scan_specs_finds_markdown(tmp_path: Path) -> None:
    """Returns all .md files under specs/."""
    specs = tmp_path / "specs" / "tier1"
    specs.mkdir(parents=True)
    (specs / "a.md").write_text("# A")
    (specs / "b.md").write_text("# B")
    (specs / "b.txt").write_text("not markdown")

    result = _scan_specs(str(tmp_path))
    names = {p.name for p in result}
    assert names == {"a.md", "b.md"}


# ---------------------------------------------------------------------------
# _check_page
# ---------------------------------------------------------------------------

def test_check_page_valid_no_violations(valid_spec: Path, tmp_path: Path) -> None:
    content = valid_spec.read_text(encoding="utf-8")
    violations = _check_page(valid_spec, content, str(tmp_path))
    types = {v["type"] for v in violations}
    assert "missing-parent-link" not in types


def test_check_page_missing_parent(missing_parent_spec: Path, tmp_path: Path) -> None:
    content = missing_parent_spec.read_text(encoding="utf-8")
    violations = _check_page(missing_parent_spec, content, str(tmp_path))
    types = {v["type"] for v in violations}
    assert "missing-parent-link" in types
    violation = next(v for v in violations if v["type"] == "missing-parent-link")
    assert violation["severity"] == "error"


def test_check_page_oversized(oversized_spec: Path, tmp_path: Path) -> None:
    content = oversized_spec.read_text(encoding="utf-8")
    violations = _check_page(oversized_spec, content, str(tmp_path))
    types = {v["type"] for v in violations}
    assert "oversized-page" in types
    violation = next(v for v in violations if v["type"] == "oversized-page")
    assert violation["severity"] == "warning"
    assert "300" in violation["message"]


def test_check_page_broken_link(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    page = specs / "page.md"
    page.write_text(
        "---\nparent: index\n---\n\n# Page\n\nSee [[NonExistentTarget]] for details.\n",
        encoding="utf-8",
    )
    violations = _check_page(page, page.read_text(), str(tmp_path))
    types = {v["type"] for v in violations}
    assert "broken-link" in types


def test_check_page_valid_link_not_broken(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    page = specs / "page.md"
    other = specs / "other.md"
    other.write_text("# Other")
    page.write_text(
        "---\nparent: index\n---\n\n# Page\n\nSee [[other]] for details.\n",
        encoding="utf-8",
    )
    violations = _check_page(page, page.read_text(), str(tmp_path))
    types = {v["type"] for v in violations}
    assert "broken-link" not in types


# ---------------------------------------------------------------------------
# run() — empty specs/
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_empty_specs(tmp_path: Path, agent_config: AgentConfig) -> None:
    """run() with empty specs/ produces a manifest with pages_scanned=0."""
    runs_dir = tmp_path / ".agents" / "runs"
    runs_dir.mkdir(parents=True)

    with patch("ea_workbench.agents.wiki_integrity.query") as mock_query:
        mock_result = MagicMock()
        mock_result.__class__ = type(
            "ResultMessage", (), {"result": "", "usage": None, "is_error": False}
        )

        async def fake_query(*args, **kwargs):
            return
            yield  # make it an async generator

        mock_query.return_value = fake_query()

        manifest = await run(agent_config, ".", str(tmp_path))

    assert isinstance(manifest, RunManifest)
    assert manifest.agent_id == AGENT_ID
    assert manifest.status == "completed"
    assert manifest.summary["pages_scanned"] == 0
    assert manifest.summary["violations_found"] == 0
    assert manifest.summary["warnings_found"] == 0
    assert manifest.summary["top_violation_type"] == "none"


@pytest.mark.asyncio
async def test_run_summary_keys_match_health_command(
    tmp_path: Path, agent_config: AgentConfig
) -> None:
    """Summary dict keys must include all keys expected by /health command."""
    runs_dir = tmp_path / ".agents" / "runs"
    runs_dir.mkdir(parents=True)

    with patch("ea_workbench.agents.wiki_integrity.query") as mock_query:
        async def fake_query(*args, **kwargs):
            return
            yield

        mock_query.return_value = fake_query()

        manifest = await run(agent_config, ".", str(tmp_path))

    required_keys = {"pages_scanned", "violations_found", "warnings_found", "top_violation_type"}
    assert required_keys.issubset(manifest.summary.keys())
