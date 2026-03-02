"""Tests for context_bootstrap — no Chainlit dependency."""

import pytest

from ea_workbench.chat.context_bootstrap import bootstrap_from_devops


@pytest.mark.asyncio
async def test_bootstrap_from_devops_returns_dict() -> None:
    """bootstrap_from_devops returns a dict."""
    result = await bootstrap_from_devops("123")
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_bootstrap_from_devops_required_keys() -> None:
    """Result contains intent, context_message, and item_id keys."""
    result = await bootstrap_from_devops("456")
    assert "intent" in result
    assert "context_message" in result
    assert "item_id" in result


@pytest.mark.asyncio
async def test_bootstrap_from_devops_intent_format() -> None:
    """Intent field follows the devops-item:<id> format."""
    result = await bootstrap_from_devops("789")
    assert result["intent"] == "devops-item:789"


@pytest.mark.asyncio
async def test_bootstrap_from_devops_item_id_preserved() -> None:
    """item_id matches the supplied argument."""
    result = await bootstrap_from_devops("1234")
    assert result["item_id"] == "1234"


@pytest.mark.asyncio
async def test_bootstrap_from_devops_context_message_contains_id() -> None:
    """context_message references the work item ID."""
    result = await bootstrap_from_devops("999")
    assert "999" in result["context_message"]
