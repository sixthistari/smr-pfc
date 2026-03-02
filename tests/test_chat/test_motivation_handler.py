"""Tests for motivation_handler — Need, Engagement, and Requirement persistence."""

from pathlib import Path

import pytest
import yaml

from ea_workbench.chat.motivation_handler import write_engagement, write_need, write_requirement
from ea_workbench.models.motivation import Engagement, Need, Requirement


# ---------------------------------------------------------------------------
# write_need
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_need_creates_file(tmp_path: Path) -> None:
    """write_need creates a YAML file under needs/by-domain/{domain}.yaml."""
    need = Need(
        id="need-001",
        statement="Users need single sign-on across all enterprise applications.",
        domain="security",
        stakeholders=["CISO", "Enterprise Architect"],
        priority="high",
    )

    path = await write_need(need, str(tmp_path))
    assert Path(path).exists()
    assert Path(path).name == "security.yaml"
    assert "needs/by-domain" in path


@pytest.mark.asyncio
async def test_write_need_valid_yaml(tmp_path: Path) -> None:
    """Written file is parseable YAML containing the need."""
    need = Need(
        id="need-002",
        statement="The system must support offline operation.",
        domain="resilience",
    )
    path = await write_need(need, str(tmp_path))

    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    assert isinstance(data, list)
    assert any(item.get("id") == "need-002" for item in data)


@pytest.mark.asyncio
async def test_write_need_appends_multiple(tmp_path: Path) -> None:
    """Writing two needs to the same domain appends both to the same file."""
    need1 = Need(id="need-a", statement="First need.", domain="enterprise")
    need2 = Need(id="need-b", statement="Second need.", domain="enterprise")

    await write_need(need1, str(tmp_path))
    await write_need(need2, str(tmp_path))

    file_path = tmp_path / "needs" / "by-domain" / "enterprise.yaml"
    with file_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    ids = [item["id"] for item in data]
    assert "need-a" in ids
    assert "need-b" in ids


# ---------------------------------------------------------------------------
# write_engagement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_engagement_creates_file(tmp_path: Path) -> None:
    """write_engagement creates a YAML file under needs/engagements/{id}.yaml."""
    eng = Engagement(
        id="eng-001",
        title="IAM Workshop",
        date="2026-03-01",
        type="workshop",
        participants=[{"name": "Jane Smith", "role": "CISO"}],
        context="Initial discovery session for IAM capability.",
    )

    path = await write_engagement(eng, str(tmp_path))
    assert Path(path).exists()
    assert Path(path).name == "eng-001.yaml"
    assert "engagements" in path


@pytest.mark.asyncio
async def test_write_engagement_parseable(tmp_path: Path) -> None:
    """Engagement file is parseable and contains expected fields."""
    eng = Engagement(
        id="eng-002",
        title="Security Review",
        date="2026-03-15",
        type="review",
    )
    path = await write_engagement(eng, str(tmp_path))

    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    assert isinstance(data, dict)
    assert data["id"] == "eng-002"
    assert data["title"] == "Security Review"
    assert data["type"] == "review"


# ---------------------------------------------------------------------------
# write_requirement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_requirement_creates_file(tmp_path: Path) -> None:
    """write_requirement creates a file under requirements/by-domain/{domain}.yaml."""
    req = Requirement(
        id="req-001",
        traces_to_need="need-001",
        statement="The system shall authenticate users via MFA.",
        domain="security",
        type="functional",
        acceptance_criteria=["MFA prompts on every login", "Supports TOTP and SMS"],
    )

    path = await write_requirement(req, str(tmp_path))
    assert Path(path).exists()
    assert Path(path).name == "security.yaml"
    assert "requirements/by-domain" in path


@pytest.mark.asyncio
async def test_write_requirement_traces_to_need(tmp_path: Path) -> None:
    """Requirement YAML contains traces_to_need field correctly."""
    req = Requirement(
        id="req-002",
        traces_to_need="need-003",
        statement="Response time under 2 seconds.",
        domain="performance",
        type="non-functional",
    )
    path = await write_requirement(req, str(tmp_path))

    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    assert isinstance(data, list)
    req_data = next(item for item in data if item["id"] == "req-002")
    assert req_data["traces_to_need"] == "need-003"


@pytest.mark.asyncio
async def test_write_requirement_appends(tmp_path: Path) -> None:
    """Multiple requirements for same domain are appended to the same file."""
    req1 = Requirement(id="req-x", traces_to_need="n1", statement="Req X.", domain="safety")
    req2 = Requirement(id="req-y", traces_to_need="n1", statement="Req Y.", domain="safety")

    await write_requirement(req1, str(tmp_path))
    await write_requirement(req2, str(tmp_path))

    file_path = tmp_path / "requirements" / "by-domain" / "safety.yaml"
    with file_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    ids = [item["id"] for item in data]
    assert "req-x" in ids
    assert "req-y" in ids
