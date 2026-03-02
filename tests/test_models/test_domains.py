"""Tests for the Domain model."""

import pytest

from ea_workbench.models.domains import Domain


def test_domain_create_minimal() -> None:
    """Domain creates with only required fields."""
    d = Domain(id="dom-safety", name="Safety Management")
    assert d.id == "dom-safety"
    assert d.name == "Safety Management"


def test_domain_default_values() -> None:
    """Domain has correct defaults for optional fields."""
    d = Domain(id="dom-test", name="Test Domain")
    assert d.maturity == "initial"
    assert d.autonomy_ceiling == "L5"
    assert d.track_default == "Track1"
    assert d.priority == 0
    assert d.description == ""
    assert d.owner_role == ""


def test_domain_serialise() -> None:
    """Domain serialises to dict via model_dump."""
    d = Domain(
        id="dom-geology",
        name="Geology",
        description="Geological survey domain",
        priority=2,
        maturity="managed",
        autonomy_ceiling="L3",
        track_default="Track2",
        owner_role="Chief Geologist",
    )
    data = d.model_dump()
    assert data["id"] == "dom-geology"
    assert data["maturity"] == "managed"
    assert data["autonomy_ceiling"] == "L3"
    assert data["owner_role"] == "Chief Geologist"
