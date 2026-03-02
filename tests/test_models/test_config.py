"""Tests for workbench and agent configuration models."""

import pytest

from ea_workbench.models.config import AgentConfig, WorkbenchConfig, WorkbenchDefaults


def test_agent_config_valid() -> None:
    """AgentConfig with required fields validates."""
    cfg = AgentConfig(
        id="adr-generator",
        name="ADR Generator",
        model="claude-sonnet-4-6",
        prompt=".agents/prompts/adr-generator.md",
        extracts_entities=True,
    )
    assert cfg.input_type == "file"
    assert cfg.tools == []


def test_workbench_config_valid() -> None:
    """WorkbenchConfig validates with agents dict."""
    cfg = WorkbenchConfig(
        version="1.0",
        defaults=WorkbenchDefaults(
            judgment_model="claude-sonnet-4-6",
            extraction_model="gemini-2.5-flash",
            authoring_model="claude-sonnet-4-6",
        ),
        agents={
            "adr-generator": AgentConfig(
                id="adr-generator",
                name="ADR Generator",
                model="claude-sonnet-4-6",
                prompt=".agents/prompts/adr-generator.md",
            )
        },
    )
    assert "adr-generator" in cfg.agents
    assert cfg.defaults.judgment_model == "claude-sonnet-4-6"


def test_workbench_config_defaults() -> None:
    """WorkbenchConfig has sensible defaults."""
    cfg = WorkbenchConfig()
    assert cfg.agents == {}
    assert cfg.defaults.judgment_model == "claude-sonnet-4-6"


def test_agent_config_missing_required_raises() -> None:
    """Missing model raises ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        AgentConfig.model_validate({"id": "x", "name": "y"})  # missing model, prompt
