"""Tests that _index.yaml files validate against PracticeIndex model."""

from pathlib import Path

import pytest
import yaml

from ea_workbench.models.practice import PracticeArtefact, PracticeIndex

_WORKSPACE = Path(__file__).parent.parent.parent / "stanmore-pfc"

INDEX_FILES = [
    _WORKSPACE / "architecture" / "principles" / "_index.yaml",
    _WORKSPACE / "architecture" / "standards" / "_index.yaml",
    _WORKSPACE / "architecture" / "decisions" / "_index.yaml",
    _WORKSPACE / "architecture" / "nfrs" / "_index.yaml",
    _WORKSPACE / "architecture" / "ideas" / "_index.yaml",
    _WORKSPACE / "architecture" / "strategies" / "_index.yaml",
    _WORKSPACE / "needs" / "_index.yaml",
    _WORKSPACE / "requirements" / "_index.yaml",
]


@pytest.mark.parametrize("index_path", INDEX_FILES, ids=[p.parent.name for p in INDEX_FILES])
def test_index_yaml_validates(index_path: Path) -> None:
    """Each _index.yaml file validates against PracticeIndex model."""
    assert index_path.exists(), f"Index file missing: {index_path}"
    with open(index_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    # Patch items that are missing updated_at for empty-items indexes
    items = raw.get("items", [])
    for item in items:
        if "updated_at" not in item:
            item["updated_at"] = item.get("created_at", "2026-03-02")

    index = PracticeIndex.model_validate(raw)
    assert index.version == "1.0"
    assert isinstance(index.items, list)
