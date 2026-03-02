"""Tests for element, relationship, and capability models."""

import pytest

from ea_workbench.models.elements import Capability, Element, ElementCapability, Relationship


def test_element_valid() -> None:
    """Element with all required fields validates correctly."""
    el = Element(
        id="comp-doc-intel",
        name="Document Intelligence Pipeline",
        archimate_type="application-component",
        domain="knowledge-infrastructure",
    )
    assert el.id == "comp-doc-intel"
    assert el.status == "proposed"
    assert el.confidence == 1.0
    data = el.model_dump()
    assert data["id"] == "comp-doc-intel"


def test_element_optional_fields() -> None:
    """Element optional fields default correctly."""
    el = Element(
        id="svc-vector-search",
        name="Vector Search Service",
        archimate_type="application-service",
        domain="knowledge-infrastructure",
        description="Azure AI Search semantic search endpoint",
        source_spec="specs/tier2/knowledge-layer.md",
        source_line=42,
        confidence=0.85,
        created_by="adr-generator_a1b2",
    )
    assert el.description is not None
    assert el.confidence == 0.85


def test_element_model_validate() -> None:
    """Element validates from dict using Pydantic v2 API."""
    data = {
        "id": "node-azure-search",
        "name": "Azure AI Search",
        "archimate_type": "technology-node",
        "domain": "knowledge-infrastructure",
        "status": "approved",
    }
    el = Element.model_validate(data)
    assert el.status == "approved"


def test_relationship_valid() -> None:
    """Relationship with required fields validates."""
    rel = Relationship(
        id="rel-001",
        source_element_id="comp-doc-intel",
        target_element_id="svc-vector-search",
        archimate_type="serving-relationship",
    )
    assert rel.confidence == 1.0
    assert rel.model_dump()["id"] == "rel-001"


def test_capability_valid() -> None:
    """Capability validates correctly."""
    cap = Capability(
        id="cap-doc-ingestion",
        name="Document Ingestion & Processing",
        level=2,
        domain="knowledge-infrastructure",
        maturity="initial",
    )
    assert cap.parent_id is None
    assert cap.level == 2


def test_element_capability_defaults() -> None:
    """ElementCapability has correct default relationship type."""
    ec = ElementCapability(element_id="comp-doc-intel", capability_id="cap-doc-ingestion")
    assert ec.relationship_type == "realizes"


def test_element_missing_required_raises() -> None:
    """Missing required fields raise ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        Element.model_validate({"id": "x"})  # missing name, archimate_type, domain
