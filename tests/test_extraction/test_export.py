"""Tests for the ArchiMate XML export function."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import yaml

from ea_workbench.extraction.export import (
    ARCHIMATE_NS,
    export_approved,
    slug_id,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _write_entity_file(approved_dir: Path, name: str, entities: list[dict]) -> None:
    """Helper to write an approved entity YAML file."""
    approved_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "metadata": {"extracted_by": "test", "run_id": "abc", "timestamp": "2026-01-01", "source": "test.md"},
        "entities": entities,
    }
    (approved_dir / f"{name}.yaml").write_text(yaml.dump(data), encoding="utf-8")


def _write_relationship_file(approved_dir: Path, name: str, relationships: list[dict]) -> None:
    """Helper to write an approved relationship YAML file."""
    approved_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "metadata": {"extracted_by": "test", "run_id": "abc", "timestamp": "2026-01-01", "source": "test.md"},
        "relationships": relationships,
    }
    (approved_dir / f"{name}.yaml").write_text(yaml.dump(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# slug_id
# ---------------------------------------------------------------------------

def test_slug_id_stable() -> None:
    """Same name always produces the same ID."""
    assert slug_id("My Service", "id") == slug_id("My Service", "id")


def test_slug_id_normalises_case() -> None:
    """Name is lowercased and slugified."""
    result = slug_id("Application Component", "id")
    assert result == "id-application-component"


def test_slug_id_strips_special_chars() -> None:
    """Special characters are replaced with hyphens."""
    result = slug_id("Foo & Bar (v2)", "id")
    assert " " not in result
    assert "&" not in result
    assert "(" not in result


def test_slug_id_prefix_prepended() -> None:
    assert slug_id("Service", "rel").startswith("rel-")


# ---------------------------------------------------------------------------
# export_approved — element count and structure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_export_empty_approved_dir(tmp_path: Path) -> None:
    """Export with no approved files produces valid XML with 0 elements."""
    output = await export_approved(str(tmp_path), output_path=str(tmp_path / "out.xml"))
    tree = ET.parse(output)
    root = tree.getroot()
    elements_el = root.find(f"{{{ARCHIMATE_NS}}}elements")
    assert elements_el is not None
    assert len(list(elements_el)) == 0


@pytest.mark.asyncio
async def test_export_two_entities(tmp_path: Path) -> None:
    """Export with 2 approved entities produces XML with 2 elements."""
    approved_dir = tmp_path / ".staging" / "approved"
    _write_entity_file(
        approved_dir,
        "entities1",
        [
            {"name": "Auth Service", "archimate_type": "application-service", "confidence": 0.9},
            {"name": "Identity Store", "archimate_type": "data-object", "confidence": 0.8},
        ],
    )

    output = await export_approved(str(tmp_path), output_path=str(tmp_path / "out.xml"))
    tree = ET.parse(output)
    root = tree.getroot()
    elements_el = root.find(f"{{{ARCHIMATE_NS}}}elements")
    assert elements_el is not None
    assert len(list(elements_el)) == 2


@pytest.mark.asyncio
async def test_export_confidence_filter(tmp_path: Path) -> None:
    """Entities below threshold are excluded from the export."""
    approved_dir = tmp_path / ".staging" / "approved"
    _write_entity_file(
        approved_dir,
        "entities1",
        [
            {"name": "High Confidence", "archimate_type": "application-component", "confidence": 0.9},
            {"name": "Low Confidence", "archimate_type": "application-component", "confidence": 0.6},
        ],
    )

    output = await export_approved(
        str(tmp_path), confidence_threshold=0.8, output_path=str(tmp_path / "out.xml")
    )
    tree = ET.parse(output)
    root = tree.getroot()
    elements_el = root.find(f"{{{ARCHIMATE_NS}}}elements")
    assert elements_el is not None
    assert len(list(elements_el)) == 1
    assert list(elements_el)[0].get("name") == "High Confidence"


@pytest.mark.asyncio
async def test_export_motivation_layer_types(tmp_path: Path) -> None:
    """Motivation layer types round-trip correctly to PascalCase XML type attributes."""
    approved_dir = tmp_path / ".staging" / "approved"
    motivation_entities = [
        {"name": "Safety Goal", "archimate_type": "goal", "confidence": 0.9},
        {"name": "Access Requirement", "archimate_type": "requirement", "confidence": 0.9},
        {"name": "Market Driver", "archimate_type": "driver", "confidence": 0.9},
        {"name": "Outcome 1", "archimate_type": "outcome", "confidence": 0.9},
        {"name": "Principle 1", "archimate_type": "principle", "confidence": 0.9},
        {"name": "Constraint 1", "archimate_type": "constraint", "confidence": 0.9},
    ]
    _write_entity_file(approved_dir, "motivation", motivation_entities)

    output = await export_approved(str(tmp_path), output_path=str(tmp_path / "out.xml"))
    tree = ET.parse(output)
    root = tree.getroot()
    elements_el = root.find(f"{{{ARCHIMATE_NS}}}elements")
    assert elements_el is not None

    xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
    types_found = {
        el.get(f"{{{xsi_ns}}}type")
        for el in elements_el
    }
    assert "Goal" in types_found
    assert "Requirement" in types_found
    assert "Driver" in types_found
    assert "Outcome" in types_found
    assert "Principle" in types_found
    assert "Constraint" in types_found


@pytest.mark.asyncio
async def test_export_with_relationship(tmp_path: Path) -> None:
    """Export including relationships writes a relationships element."""
    approved_dir = tmp_path / ".staging" / "approved"
    _write_entity_file(
        approved_dir,
        "entities",
        [
            {"name": "Service A", "archimate_type": "application-service", "confidence": 0.9},
            {"name": "Component B", "archimate_type": "application-component", "confidence": 0.9},
        ],
    )
    _write_relationship_file(
        approved_dir,
        "rels",
        [
            {
                "source_element": "Service A",
                "target_element": "Component B",
                "archimate_type": "serving-relationship",
                "confidence": 0.85,
            }
        ],
    )

    output = await export_approved(str(tmp_path), output_path=str(tmp_path / "out.xml"))
    tree = ET.parse(output)
    root = tree.getroot()

    rels_el = root.find(f"{{{ARCHIMATE_NS}}}relationships")
    assert rels_el is not None
    assert len(list(rels_el)) == 1


@pytest.mark.asyncio
async def test_export_stable_ids(tmp_path: Path) -> None:
    """Running export twice with same data produces identical element identifiers."""
    approved_dir = tmp_path / ".staging" / "approved"
    _write_entity_file(
        approved_dir,
        "entities",
        [{"name": "Stable Service", "archimate_type": "application-service", "confidence": 0.9}],
    )

    out1 = str(tmp_path / "out1.xml")
    out2 = str(tmp_path / "out2.xml")
    await export_approved(str(tmp_path), output_path=out1)
    await export_approved(str(tmp_path), output_path=out2)

    xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
    tree1 = ET.parse(out1)
    tree2 = ET.parse(out2)

    els1 = list(tree1.getroot().find(f"{{{ARCHIMATE_NS}}}elements"))
    els2 = list(tree2.getroot().find(f"{{{ARCHIMATE_NS}}}elements"))

    assert els1[0].get("identifier") == els2[0].get("identifier")


@pytest.mark.asyncio
async def test_export_xml_is_valid(tmp_path: Path) -> None:
    """Output file is parseable well-formed XML."""
    approved_dir = tmp_path / ".staging" / "approved"
    _write_entity_file(
        approved_dir,
        "e",
        [{"name": "Test Elem", "archimate_type": "goal", "confidence": 0.8}],
    )

    output = await export_approved(str(tmp_path), output_path=str(tmp_path / "out.xml"))
    # Should not raise
    ET.parse(output)
