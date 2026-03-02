"""Transcript → ArchiMate Classifier Agent — UC-1.

Reads a stakeholder meeting transcript, maps content against the capability model
and element registry, extracts ArchiMate elements, and produces staged entities
plus a classification report.
"""

import logging
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from claude_code_sdk import ClaudeCodeOptions, ResultMessage, query

from ea_workbench.agents.base import write_manifest
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest

logger = logging.getLogger(__name__)

AGENT_ID = "transcript-classifier"


def _load_transcript(path: str) -> str:
    """Read a transcript file and return its content.

    Args:
        path: Absolute or relative path to the transcript file.

    Returns:
        File content as a string, or a placeholder if the file is missing.
    """
    p = Path(path)
    if not p.exists():
        return "(not found)"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not read transcript %s: %s", path, exc)
        return "(not found)"


def _extract_yaml_block(text: str) -> dict:
    """Parse the first fenced YAML block from agent output.

    Args:
        text: Raw text output from the agent.

    Returns:
        Parsed dict from the YAML block, or empty dict if none found.
    """
    pattern = r"```yaml\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("Could not parse YAML block: %s", exc)
        return {}


def _load_capability_model(workspace: str) -> str:
    """Load the capability model summary for template substitution.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Capability model content or placeholder.
    """
    cap_path = Path(workspace) / "capabilities" / "capability-model.yaml"
    if not cap_path.exists():
        return "(capability model not found)"
    try:
        lines = cap_path.read_text(encoding="utf-8").splitlines()[:50]
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Could not load capability model: %s", exc)
        return "(could not load capability model)"


def _load_element_registry_summary(workspace: str) -> str:
    """Load a brief element registry summary for template substitution.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Summary text or placeholder.
    """
    reg_path = Path(workspace) / "registry.db"
    if not reg_path.exists():
        return "(element registry not initialised)"
    return "(element registry available — use Read tool to query)"


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the transcript classifier for a single transcript file.

    `prompt` is treated as the transcript file path (relative to workspace or absolute).

    Args:
        config: Agent configuration from config.yaml.
        prompt: File path of the transcript to classify.
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Staged entities written to .staging/entities/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    # Resolve the transcript file path
    transcript_path = (
        Path(prompt) if Path(prompt).is_absolute() else Path(workspace) / prompt
    )

    # Load context for template substitution
    capability_model = _load_capability_model(workspace)
    element_registry_summary = _load_element_registry_summary(workspace)

    # Load and populate system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are an ArchiMate entity extractor. "
            "Read the transcript and extract entities and relationships."
        )

    system_prompt = system_prompt.replace("{{CAPABILITY_MODEL}}", capability_model)
    system_prompt = system_prompt.replace(
        "{{ELEMENT_REGISTRY_SUMMARY}}", element_registry_summary
    )

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Classify the stakeholder transcript at '{transcript_path}'. "
        "Read the file, extract ArchiMate entities and relationships, "
        "produce a YAML extraction block and classification report."
    )

    result_text = ""
    run_status = "completed"
    error_msg: str | None = None
    tokens_consumed = 0

    try:
        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            allowed_tools=config.tools or ["Read", "Write"],
            cwd=workspace,
            model=model,
            max_turns=8,
            permission_mode="acceptEdits",
        )
        async for message in query(prompt=agent_prompt, options=options):
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
        logger.error("Transcript classifier SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)
        result_text = f"## Classification Report\n\n⚠️ Agent error: {exc}"

    # Parse extracted entities and relationships
    extracted = _extract_yaml_block(result_text)
    entities = extracted.get("entities", []) if isinstance(extracted, dict) else []
    relationships = (
        extracted.get("relationships", []) if isinstance(extracted, dict) else []
    )

    # Write staged entities to .staging/entities/
    staging_dir = Path(workspace) / ".staging" / "entities"
    staging_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"transcript-classifier_{run_id}.yaml"
    output_file = staging_dir / output_filename

    staged_data = {
        "source_agent": AGENT_ID,
        "run_id": run_id,
        "transcript": str(transcript_path),
        "entities": entities,
        "relationships": relationships,
    }
    output_file.write_text(
        yaml.dump(staged_data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    duration = time.monotonic() - start
    manifest = RunManifest(
        agent_id=AGENT_ID,
        run_id=run_id,
        triggered_by="manual",
        timestamp=timestamp,
        duration_seconds=duration,
        model_used=model,
        tokens_consumed=tokens_consumed,
        status=run_status,
        inputs=[str(transcript_path)],
        outputs=[str(output_file)],
        entities_extracted=len(entities),
        relationships_extracted=len(relationships),
        summary={
            "entities_extracted": len(entities),
            "relationships_extracted": len(relationships),
            "transcript_file": str(transcript_path),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
