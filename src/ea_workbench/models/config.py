"""Pydantic models for workbench and agent configuration."""

from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration for a single batch agent from config.yaml."""

    id: str
    name: str
    use_case: str | None = None
    description: str | None = None
    model: str
    prompt: str
    input_type: str = "file"  # "file" | "directory" | "stdin"
    output_dir: str | None = None
    extracts_entities: bool = False
    extracts_relationships: bool = False
    tools: list[str] = []
    schedule: str | None = None
    pipeline: str | None = None
    trigger: str | None = None


class WorkbenchDefaults(BaseModel):
    """Default model and endpoint settings."""

    endpoint: str = ""
    judgment_model: str = "claude-sonnet-4-6"
    extraction_model: str = "gemini-2.5-flash"
    authoring_model: str = "claude-sonnet-4-6"


class WorkbenchConfig(BaseModel):
    """Top-level workbench configuration loaded from config.yaml."""

    version: str = "1.0"
    last_updated: str | None = None
    defaults: WorkbenchDefaults = WorkbenchDefaults()
    agents: dict[str, AgentConfig] = {}
