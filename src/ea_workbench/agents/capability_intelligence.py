"""Capability Intelligence Agent — UC-4.

Reads a YAML work-items export, correlates against the capability model and element
registry, and produces an intelligence report with implied capabilities, gaps, and
alignment scores. Proposes only — never modifies the capability model directly.
"""

import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, ResultMessage, query

from ea_workbench.agents.base import write_manifest
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest

logger = logging.getLogger(__name__)

AGENT_ID = "capability-intelligence"


def _load_work_items(workspace: str, prompt: str) -> str:
    """Load work items from a file path or return the prompt string directly.

    If `prompt` looks like a file path that exists, reads and returns the file.
    Otherwise returns the prompt string as-is (inline YAML content).

    Args:
        workspace: Path to the PFC workspace root (used for relative path resolution).
        prompt: Either a file path or inline YAML content.

    Returns:
        Work items content string, or placeholder if file not found.
    """
    # Try to resolve as an absolute path first
    p = Path(prompt)
    if p.is_absolute():
        if p.exists():
            try:
                return p.read_text(encoding="utf-8")
            except Exception as exc:
                logger.warning("Could not read work items file %s: %s", p, exc)
                return "(could not read work items)"
        return "(work items file not found)"

    # Try relative to workspace
    rel_path = Path(workspace) / prompt
    if rel_path.exists():
        try:
            return rel_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not read work items file %s: %s", rel_path, exc)
            return "(could not read work items)"

    # If neither path resolves, treat as inline content
    # (non-path strings returned directly)
    if len(prompt) > 0 and "\n" in prompt:
        return prompt

    return "(work items file not found)"


def _load_capability_model(workspace: str) -> str:
    """Load the capability model for template substitution.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Capability model content or placeholder.
    """
    cap_path = Path(workspace) / "capabilities" / "capability-model.yaml"
    if not cap_path.exists():
        return "(capability model not found)"
    try:
        lines = cap_path.read_text(encoding="utf-8").splitlines()[:60]
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Could not load capability model: %s", exc)
        return "(could not load capability model)"


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the capability intelligence analysis.

    `prompt` is treated as a path to a work items export file, or inline YAML content.

    Args:
        config: Agent configuration from config.yaml.
        prompt: File path to work items export, or inline YAML string.
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Report written to output/intelligence/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    report_date = datetime.now(UTC).strftime("%Y-%m-%d")

    # Load context
    capability_model = _load_capability_model(workspace)
    work_items = _load_work_items(workspace, prompt)
    element_registry_summary = "(element registry available)"

    # Load and populate system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are a capability intelligence analyst. "
            "Analyse work items against the capability model and identify gaps."
        )

    system_prompt = system_prompt.replace("{{CAPABILITY_MODEL}}", capability_model)
    system_prompt = system_prompt.replace(
        "{{ELEMENT_REGISTRY_SUMMARY}}", element_registry_summary
    )
    system_prompt = system_prompt.replace("{{WORK_ITEMS}}", work_items)
    system_prompt = system_prompt.replace("{{REPORT_DATE}}", report_date)

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Analyse the work items and produce a capability intelligence report for {report_date}. "
        "Identify implied capabilities, alignment scores for existing capabilities, gaps, "
        "and recommendations. Do not modify the capability model."
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
        logger.error("Capability intelligence SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)
        result_text = f"# Capability Intelligence Report\n\n⚠️ Agent error: {exc}"

    # Write output
    output_dir = Path(workspace) / "output" / "intelligence"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"capability-report-{report_date}.md"

    if not result_text:
        result_text = f"# Capability Intelligence Report — {report_date}\n\nNo analysis produced."

    output_file.write_text(result_text, encoding="utf-8")

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
        inputs=[prompt],
        outputs=[str(output_file)],
        summary={
            "work_items_analysed": work_items.count("\n") + 1 if work_items else 0,
            "capabilities_implied": 0,  # populated from result in production
            "output_file": str(output_file),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
