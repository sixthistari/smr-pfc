"""Orbus Sync Intelligence Agent — UC-9.

Reads completed work items, linked wiki specs, and the element registry to produce
a structured change set YAML for Orbus synchronisation. Weekly schedule.
"""

import logging
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

AGENT_ID = "orbus-sync"


def _load_completed_work_items(workspace: str) -> str:
    """Load completed work items from staging or workspace.

    Looks for YAML work item files in staging or work items directory.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Work items content as a string, or placeholder if none found.
    """
    # Try staging/work-items first, then work-items directory
    candidate_dirs = [
        Path(workspace) / ".staging" / "work-items",
        Path(workspace) / "work-items",
        Path(workspace) / "staging" / "work-items",
    ]

    all_items: list[str] = []
    for candidate_dir in candidate_dirs:
        if candidate_dir.exists():
            for path in sorted(candidate_dir.glob("*.yaml"))[:10]:
                try:
                    content = path.read_text(encoding="utf-8")
                    all_items.append(f"# {path.name}\n{content}")
                except Exception as exc:
                    logger.warning("Could not read work items %s: %s", path, exc)

    if not all_items:
        return "(no completed work items found)"

    return "\n\n---\n\n".join(all_items)


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the Orbus sync intelligence agent.

    Args:
        config: Agent configuration from config.yaml.
        prompt: Ignored — agent reads workspace directly.
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Change set written to output/orbus-sync/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    sync_date = datetime.now(UTC).strftime("%Y-%m-%d")

    # Load work items
    work_items = _load_completed_work_items(workspace)

    # Load system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are an Orbus sync agent. "
            "Produce a YAML change set from the completed work items."
        )

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Produce an Orbus change set for {sync_date}. "
        f"Work items available:\n\n{work_items}\n\n"
        f"Write the change set to 'output/orbus-sync/changeset-{sync_date}.yaml' "
        f"in workspace '{workspace}'."
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
        logger.error("Orbus sync SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)

    # Write output
    output_dir = Path(workspace) / "output" / "orbus-sync"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"changeset-{sync_date}.yaml"

    if not output_file.exists():
        # Write a minimal change set if agent didn't write it
        minimal = {
            "changeset_date": sync_date,
            "generated_by": AGENT_ID,
            "note": result_text[:500] if result_text else "No change set produced.",
        }
        output_file.write_text(
            yaml.dump(minimal, default_flow_style=False, allow_unicode=True),
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
        inputs=[workspace],
        outputs=[str(output_file)],
        summary={
            "sync_date": sync_date,
            "output_file": str(output_file),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
