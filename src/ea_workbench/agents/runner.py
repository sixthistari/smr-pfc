"""Batch agent runner — loads config, resolves agents, invokes via Claude Agent SDK."""

import logging
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from claude_code_sdk import ClaudeCodeOptions, ResultMessage, query

from ea_workbench.agents.base import write_manifest
from ea_workbench.models.config import AgentConfig, WorkbenchConfig
from ea_workbench.models.manifests import RunManifest

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> WorkbenchConfig:
    """Load and validate the workbench config from a YAML file.

    Args:
        config_path: Path to .agents/config.yaml.

    Returns:
        Validated WorkbenchConfig instance.

    Raises:
        FileNotFoundError: If config_path does not exist.
        ValueError: If the YAML does not validate against WorkbenchConfig.
    """
    with open(config_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return WorkbenchConfig.model_validate(raw)


def resolve_agent(config: WorkbenchConfig, agent_id: str) -> AgentConfig:
    """Look up an agent by ID in the workbench config.

    Args:
        config: Loaded workbench configuration.
        agent_id: The agent identifier (kebab-case).

    Returns:
        The agent's AgentConfig.

    Raises:
        KeyError: If agent_id is not found in the registry.
    """
    if agent_id not in config.agents:
        available = list(config.agents.keys())
        raise KeyError(
            f"Agent '{agent_id}' not found in config. Available: {available}"
        )
    return config.agents[agent_id]


def load_prompt(prompt_path: str) -> str:
    """Read an agent prompt file from disk.

    Args:
        prompt_path: Path to the .md prompt file.

    Returns:
        Prompt content as a string.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    return Path(prompt_path).read_text(encoding="utf-8")


async def run_batch_agent(
    agent_id: str,
    prompt: str,
    workspace: str,
    config_path: str,
) -> RunManifest:
    """Execute a batch agent and return its run manifest.

    Loads config, resolves the agent, runs it via the Claude Agent SDK,
    and writes the manifest to .agents/runs/.

    Args:
        agent_id: Agent identifier from config.yaml.
        prompt: User prompt or input file path to process.
        workspace: Path to the PFC workspace root.
        config_path: Path to .agents/config.yaml.

    Returns:
        Completed RunManifest.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()

    runs_dir = os.path.join(workspace, ".agents", "runs")

    try:
        config = load_config(config_path)
        agent_config = resolve_agent(config, agent_id)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        duration = time.monotonic() - start
        manifest = RunManifest(
            agent_id=agent_id,
            run_id=run_id,
            triggered_by="manual",
            timestamp=timestamp,
            duration_seconds=duration,
            model_used="unknown",
            tokens_consumed=0,
            status="failed",
            inputs=[],
            outputs=[],
            error=str(exc),
        )
        write_manifest(manifest, runs_dir)
        return manifest

    # Resolve prompt file path relative to workspace if it points to a file
    prompt_file_path = os.path.join(workspace, agent_config.prompt)
    try:
        system_prompt = load_prompt(prompt_file_path)
    except FileNotFoundError:
        logger.warning("Prompt file not found at %s — using empty system prompt", prompt_file_path)
        system_prompt = ""

    # Resolve model (handle ${defaults.xxx} references)
    model = agent_config.model
    if "${" in model:
        model = config.defaults.authoring_model

    options = ClaudeCodeOptions(
        system_prompt=system_prompt,
        allowed_tools=agent_config.tools or ["Read", "Write"],
        cwd=workspace,
        model=model,
        max_turns=10,
        permission_mode="acceptEdits",
    )

    result_text = ""
    tokens_consumed = 0
    model_used = model
    run_status = "completed"
    error_msg: str | None = None

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result_text = message.result or ""
                if message.usage:
                    tokens_consumed = (
                        message.usage.get("input_tokens", 0)
                        + message.usage.get("output_tokens", 0)
                    )
                if message.is_error:
                    run_status = "failed"
                    error_msg = result_text
    except Exception as exc:
        logger.error("Agent SDK error for %s: %s", agent_id, exc)
        run_status = "failed"
        error_msg = str(exc)

    duration = time.monotonic() - start

    # Determine outputs (files written to output_dir)
    outputs: list[str] = []
    if agent_config.output_dir:
        output_dir = os.path.join(workspace, agent_config.output_dir)
        if os.path.exists(output_dir):
            outputs = [
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if f.endswith((".md", ".yaml", ".json"))
            ]

    manifest = RunManifest(
        agent_id=agent_id,
        run_id=run_id,
        triggered_by="manual",
        timestamp=timestamp,
        duration_seconds=duration,
        model_used=model_used,
        tokens_consumed=tokens_consumed,
        status=run_status,
        inputs=[prompt],
        outputs=outputs,
        summary={"result_length": len(result_text)},
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
