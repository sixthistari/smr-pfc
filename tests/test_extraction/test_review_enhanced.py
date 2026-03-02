"""Tests for the enhanced staging review workflow — approve_to_registry."""

from pathlib import Path

import pytest
import yaml

from ea_workbench.extraction.review import approve_to_registry
from ea_workbench.registry.db import get_connection, initialise_schema
from ea_workbench.registry.queries import get_element


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_staging_file(staging_dir: Path, entities: list[dict]) -> Path:
    """Write a staging YAML file with the given entities."""
    staging_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "metadata": {
            "extracted_by": "test",
            "run_id": "test-001",
            "timestamp": "2026-01-01T00:00:00Z",
            "source": "test.md",
        },
        "entities": entities,
    }
    staging_file = staging_dir / "staging_test.yaml"
    staging_file.write_text(yaml.dump(data), encoding="utf-8")
    return staging_file


# ---------------------------------------------------------------------------
# approve_to_registry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_to_registry_upserts_elements(tmp_path: Path) -> None:
    """Approved entities are upserted into the registry and staging file is moved."""
    staging_dir = tmp_path / ".staging" / "entities"
    db_path = str(tmp_path / "registry.db")

    staging_file = _write_staging_file(
        staging_dir,
        [
            {
                "name": "Authentication Service",
                "archimate_type": "application-service",
                "domain": "security",
                "confidence": 0.9,
                "description": "Handles user authentication",
            },
            {
                "name": "Identity Store",
                "archimate_type": "data-object",
                "domain": "security",
                "confidence": 0.85,
            },
        ],
    )

    await initialise_schema(db_path)
    count = await approve_to_registry(str(staging_file), str(tmp_path), db_path)

    assert count == 2
    # Staging file should be moved (no longer in entities/)
    assert not staging_file.exists()
    # File should be in approved/
    approved = tmp_path / ".staging" / "approved" / "staging_test.yaml"
    assert approved.exists()

    # Verify elements appear in registry
    async with get_connection(db_path) as conn:
        import uuid
        auth_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "element:Authentication Service"))
        elem = await get_element(conn, auth_id)
    assert elem is not None
    assert elem.name == "Authentication Service"
    assert elem.archimate_type == "application-service"
    assert elem.domain == "security"


@pytest.mark.asyncio
async def test_approve_to_registry_missing_file(tmp_path: Path) -> None:
    """FileNotFoundError raised when staging file does not exist."""
    db_path = str(tmp_path / "registry.db")
    with pytest.raises(FileNotFoundError):
        await approve_to_registry(
            str(tmp_path / "nonexistent.yaml"), str(tmp_path), db_path
        )


@pytest.mark.asyncio
async def test_approve_to_registry_empty_entities(tmp_path: Path) -> None:
    """Empty entities list: file is approved but 0 elements upserted."""
    staging_dir = tmp_path / ".staging" / "entities"
    db_path = str(tmp_path / "registry.db")
    staging_file = _write_staging_file(staging_dir, [])

    await initialise_schema(db_path)
    count = await approve_to_registry(str(staging_file), str(tmp_path), db_path)

    assert count == 0
    assert not staging_file.exists()
    approved = tmp_path / ".staging" / "approved" / "staging_test.yaml"
    assert approved.exists()


@pytest.mark.asyncio
async def test_approve_to_registry_returns_count(tmp_path: Path) -> None:
    """Return value matches number of entities in staging file."""
    staging_dir = tmp_path / ".staging" / "entities"
    db_path = str(tmp_path / "registry.db")

    entities = [
        {"name": f"Element {i}", "archimate_type": "goal", "domain": "strategy", "confidence": 0.8}
        for i in range(5)
    ]
    staging_file = _write_staging_file(staging_dir, entities)

    await initialise_schema(db_path)
    count = await approve_to_registry(str(staging_file), str(tmp_path), db_path)

    assert count == 5
