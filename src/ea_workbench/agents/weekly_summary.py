"""Weekly Summary Agent.

Aggregates session records and agent run manifests into a week-in-review
planning document using Claude to synthesise the narrative.
"""

import json
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

AGENT_ID = "weekly-summary"


def _load_session_records(workspace: str, max_records: int = 20) -> list[dict]:
    """Read .staging/sessions/*.yaml files and return parsed dicts sorted by date.

    Args:
        workspace: Path to the PFC workspace root.
        max_records: Maximum number of records to return.

    Returns:
        List of session record dicts, sorted by started_at descending.
    """
    sessions_dir = Path(workspace) / ".staging" / "sessions"
    if not sessions_dir.exists():
        return []

    records: list[dict] = []
    for path in sorted(sessions_dir.glob("*.yaml"), reverse=True)[:max_records]:
        try:
            with path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if isinstance(data, dict):
                records.append(data)
        except Exception as exc:
            logger.warning("Could not read session record %s: %s", path, exc)

    return records


def _load_agent_run_summary(workspace: str, max_runs: int = 10) -> list[dict]:
    """Read .agents/runs/*.json files and return summary fields only.

    Args:
        workspace: Path to the PFC workspace root.
        max_runs: Maximum number of run manifests to return.

    Returns:
        List of run summary dicts (agent_id, status, timestamp, tokens_consumed).
    """
    runs_dir = Path(workspace) / ".agents" / "runs"
    if not runs_dir.exists():
        return []

    summaries: list[dict] = []
    run_files = sorted(runs_dir.glob("*.json"), reverse=True)[:max_runs]
    for path in run_files:
        try:
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            summaries.append(
                {
                    "agent_id": data.get("agent_id", "?"),
                    "status": data.get("status", "?"),
                    "timestamp": data.get("timestamp", "")[:16],
                    "tokens_consumed": data.get("tokens_consumed", 0),
                    "entities_extracted": data.get("entities_extracted", 0),
                }
            )
        except Exception as exc:
            logger.warning("Could not read run manifest %s: %s", path, exc)

    return summaries


def _format_sessions_text(records: list[dict]) -> str:
    """Render session records as a bullet list for the agent prompt.

    Args:
        records: List of session record dicts.

    Returns:
        Multi-line string, or placeholder if empty.
    """
    if not records:
        return "(no session records found)"

    lines: list[str] = []
    for r in records:
        session_id = r.get("session_id", "?")
        summary = r.get("summary", "(no summary)")
        started = str(r.get("started_at", ""))[:16]
        lines.append(f"- **{session_id}** ({started}): {summary}")
    return "\n".join(lines)


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the weekly summary agent.

    Args:
        config: Agent configuration from config.yaml.
        prompt: Ignored for this agent (uses workspace directly).
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Summary written to output/weekly-summaries/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    week_date = datetime.now(UTC).strftime("%Y%m%d")

    # Load session records and agent run summaries
    session_records = _load_session_records(workspace)
    agent_run_summaries = _load_agent_run_summary(workspace)

    sessions_text = _format_sessions_text(session_records)
    runs_text = (
        "\n".join(
            f"- {r['agent_id']} ({r['status']}) @ {r['timestamp']} "
            f"— {r['tokens_consumed']} tokens"
            for r in agent_run_summaries
        )
        if agent_run_summaries
        else "(no agent runs recorded)"
    )

    # Load and populate system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are an EA week-in-review synthesiser. "
            "Produce a structured weekly summary from the session and run data provided."
        )

    system_prompt = system_prompt.replace("{{SESSION_RECORDS}}", sessions_text)
    system_prompt = system_prompt.replace("{{AGENT_RUN_SUMMARY}}", runs_text)

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Produce the EA week-in-review summary for week ending {week_date}. "
        "Synthesise the session records and agent run data into a structured planning document."
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
            max_turns=5,
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
        logger.error("Weekly summary SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)
        result_text = f"# EA Week in Review\n\n⚠️ Agent error: {exc}"

    # Write output to output/weekly-summaries/
    output_dir = Path(workspace) / "output" / "weekly-summaries"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"week-{week_date}.md"
    output_file = output_dir / output_filename

    if not result_text:
        result_text = f"# EA Week in Review — {week_date}\n\nNo data available."

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
        inputs=[workspace],
        outputs=[str(output_file)],
        summary={
            "sessions_included": len(session_records),
            "agents_summarised": len(agent_run_summaries),
            "output_file": str(output_file),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
