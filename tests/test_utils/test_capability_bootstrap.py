"""Tests for capability_bootstrap — validate_capability_model."""

from pathlib import Path

import pytest
import yaml

from ea_workbench.utils.capability_bootstrap import validate_capability_model


_WORKSPACE = str(Path(__file__).parent.parent.parent / "stanmore-pfc")


# ---------------------------------------------------------------------------
# Tests against real capability-model.yaml
# ---------------------------------------------------------------------------

def test_validate_real_capability_model_is_valid() -> None:
    """The real stanmore-pfc capability model validates successfully."""
    result = validate_capability_model(_WORKSPACE)
    assert result["is_valid"] is True
    assert result["capability_count"] > 0


def test_validate_real_capability_model_has_domains() -> None:
    """Real model has at least one domain."""
    result = validate_capability_model(_WORKSPACE)
    assert result["domain_count"] > 0


def test_validate_real_capability_model_max_depth() -> None:
    """Real model has depth >= 1 (has children)."""
    result = validate_capability_model(_WORKSPACE)
    assert result["max_depth"] >= 1


def test_validate_real_capability_model_summary_keys() -> None:
    """Result dict has all required keys."""
    result = validate_capability_model(_WORKSPACE)
    required = {"domain_count", "capability_count", "max_depth", "is_valid"}
    assert required.issubset(result.keys())


# ---------------------------------------------------------------------------
# Tests with synthetic models
# ---------------------------------------------------------------------------

def test_validate_missing_workspace(tmp_path: Path) -> None:
    """Missing workspace returns is_valid=False with zero counts."""
    result = validate_capability_model(str(tmp_path))
    assert result["is_valid"] is False
    assert result["capability_count"] == 0
    assert result["domain_count"] == 0


def test_validate_empty_capabilities(tmp_path: Path) -> None:
    """Model file with empty capabilities list returns is_valid=False."""
    cap_dir = tmp_path / "capabilities"
    cap_dir.mkdir()
    (cap_dir / "capability-model.yaml").write_text(
        yaml.dump({"version": "1.0", "capabilities": []}), encoding="utf-8"
    )
    result = validate_capability_model(str(tmp_path))
    assert result["is_valid"] is False
    assert result["capability_count"] == 0


def test_validate_flat_model(tmp_path: Path) -> None:
    """Flat model (no children) has max_depth=0."""
    cap_dir = tmp_path / "capabilities"
    cap_dir.mkdir()
    model = {
        "capabilities": [
            {"id": "cap-1", "name": "Capability 1", "level": 0, "domain": "tech"},
            {"id": "cap-2", "name": "Capability 2", "level": 0, "domain": "business"},
        ]
    }
    (cap_dir / "capability-model.yaml").write_text(yaml.dump(model), encoding="utf-8")
    result = validate_capability_model(str(tmp_path))
    assert result["is_valid"] is True
    assert result["capability_count"] == 2
    assert result["domain_count"] == 2
    assert result["max_depth"] == 0


def test_validate_nested_model(tmp_path: Path) -> None:
    """Nested model correctly counts capabilities and depth."""
    cap_dir = tmp_path / "capabilities"
    cap_dir.mkdir()
    model = {
        "capabilities": [
            {
                "id": "cap-root",
                "name": "Root",
                "level": 0,
                "domain": "enterprise",
                "children": [
                    {
                        "id": "cap-child",
                        "name": "Child",
                        "level": 1,
                        "domain": "technology",
                        "children": [
                            {"id": "cap-grandchild", "name": "Grandchild", "level": 2}
                        ],
                    }
                ],
            }
        ]
    }
    (cap_dir / "capability-model.yaml").write_text(yaml.dump(model), encoding="utf-8")
    result = validate_capability_model(str(tmp_path))
    assert result["capability_count"] == 3
    assert result["max_depth"] == 2
    assert result["is_valid"] is True
