"""Slash command implementations for the EA Workbench chat interface."""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import chainlit as cl

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH_FROM_WORKSPACE = ".agents/config.yaml"


async def handle_command(content: str, workspace: str) -> None:
    """Dispatch a slash command to the appropriate handler.

    Args:
        content: The raw message content starting with '/'.
        workspace: Path to the PFC workspace root.
    """
    parts = content.strip().split(None, 2)
    command = parts[0].lower()

    if command == "/run":
        await _cmd_run(parts[1:], workspace)
    elif command == "/status":
        await _cmd_status(workspace)
    elif command == "/staging":
        await _cmd_staging(workspace)
    elif command == "/health":
        await _cmd_health(workspace)
    elif command == "/triage":
        await _cmd_triage(workspace)
    elif command == "/wrap":
        await _cmd_wrap(workspace)
    elif command == "/help":
        await _cmd_help()
    else:
        await cl.Message(
            content=f"Unknown command: `{command}`. Type `/help` for available commands."
        ).send()


async def _cmd_run(args: list[str], workspace: str) -> None:
    """Execute a batch agent.

    Usage: /run <agent-id> [input-path]
    """
    if not args:
        await cl.Message(content="Usage: `/run <agent-id> [input-path]`").send()
        return

    agent_id = args[0]
    input_path = args[1] if len(args) > 1 else ""
    config_path = os.path.join(workspace, _DEFAULT_CONFIG_PATH_FROM_WORKSPACE)

    async with cl.Step(name=f"Running {agent_id}", show_input=True) as step:
        step.input = f"Agent: `{agent_id}`\nInput: `{input_path or '(none)'}`"

        try:
            from ea_workbench.agents.runner import run_batch_agent

            manifest = await run_batch_agent(
                agent_id=agent_id,
                prompt=input_path or f"Run {agent_id}",
                workspace=workspace,
                config_path=config_path,
            )
            status_icon = "✅" if manifest.status == "completed" else "⚠️"
            step.output = (
                f"{status_icon} **{manifest.status.upper()}** — "
                f"{manifest.duration_seconds:.1f}s — "
                f"{manifest.tokens_consumed} tokens\n\n"
                f"Run ID: `{manifest.run_id}`"
            )
        except Exception as exc:
            step.output = f"❌ Error: {exc}"
            logger.error("Run command failed for %s: %s", agent_id, exc)
            return

    summary_lines = [
        f"**Agent run complete**: `{agent_id}` — `{manifest.status}`",
        f"- Duration: {manifest.duration_seconds:.1f}s",
        f"- Tokens: {manifest.tokens_consumed}",
        f"- Entities extracted: {manifest.entities_extracted}",
        f"- Outputs: {len(manifest.outputs)} file(s)",
    ]
    if manifest.error:
        summary_lines.append(f"- Error: {manifest.error}")
    await cl.Message(content="\n".join(summary_lines)).send()


async def _cmd_status(workspace: str) -> None:
    """Show recent agent run summaries."""
    runs_dir = os.path.join(workspace, ".agents", "runs")

    if not os.path.exists(runs_dir):
        await cl.Message(content="No agent runs found (`.agents/runs/` does not exist).").send()
        return

    run_files = sorted(
        [f for f in os.listdir(runs_dir) if f.endswith(".json")],
        reverse=True,
    )[:10]

    if not run_files:
        await cl.Message(content="No agent runs recorded yet.").send()
        return

    rows = ["| Agent | Status | Timestamp | Duration | Tokens |", "|---|---|---|---|---|"]
    for fname in run_files:
        try:
            with open(os.path.join(runs_dir, fname), encoding="utf-8") as fh:
                data = json.load(fh)
            status_icon = "✅" if data.get("status") == "completed" else "⚠️"
            rows.append(
                f"| `{data.get('agent_id', '?')}` "
                f"| {status_icon} {data.get('status', '?')} "
                f"| {data.get('timestamp', '')[:16]} "
                f"| {data.get('duration_seconds', 0):.1f}s "
                f"| {data.get('tokens_consumed', 0)} |"
            )
        except Exception as exc:
            logger.warning("Could not read manifest %s: %s", fname, exc)

    await cl.Message(content="**Recent Agent Runs**\n\n" + "\n".join(rows)).send()


async def _cmd_staging(workspace: str) -> None:
    """Show staging area statistics."""
    from ea_workbench.extraction.review import list_pending

    counts = await list_pending(workspace)

    lines = ["**Staging Area**\n"]
    total = 0
    for subdir, count in counts.items():
        icon = "📁" if count > 0 else "  "
        lines.append(f"- {icon} `.staging/{subdir}/`: **{count}** file(s)")
        total += count
    lines.append(f"\n**Total pending**: {total}")

    await cl.Message(content="\n".join(lines)).send()


async def _cmd_health(workspace: str) -> None:
    """Show latest wiki integrity check results."""
    runs_dir = os.path.join(workspace, ".agents", "runs")

    if not os.path.exists(runs_dir):
        await cl.Message(content="No agent runs found.").send()
        return

    # Find latest wiki-integrity manifest
    integrity_files = sorted(
        [
            f
            for f in os.listdir(runs_dir)
            if f.startswith("wiki-integrity") and f.endswith(".json")
        ],
        reverse=True,
    )

    if not integrity_files:
        await cl.Message(
            content=(
                "No wiki integrity check results found.\n\n"
                "Run `/run wiki-integrity` to generate a health report."
            )
        ).send()
        return

    with open(os.path.join(runs_dir, integrity_files[0]), encoding="utf-8") as fh:
        data = json.load(fh)

    summary = data.get("summary", {})
    status = data.get("status", "unknown")
    status_icon = "✅" if status == "completed" else "⚠️"

    lines = [
        f"**Wiki Health** {status_icon} — last run: {data.get('timestamp', '')[:16]}",
        "",
        f"- Pages scanned: {summary.get('pages_scanned', '?')}",
        f"- Violations: {summary.get('violations_found', '?')}",
        f"- Warnings: {summary.get('warnings_found', '?')}",
        f"- Top issue: `{summary.get('top_violation_type', 'none')}`",
    ]

    await cl.Message(content="\n".join(lines)).send()


async def _cmd_triage(workspace: str) -> None:
    """Present staged work items for review."""
    work_dir = os.path.join(workspace, ".staging", "work")

    if not os.path.exists(work_dir):
        await cl.Message(content="No staged work items found.").send()
        return

    import yaml

    work_files = sorted(f for f in os.listdir(work_dir) if f.endswith(".yaml"))
    if not work_files:
        await cl.Message(content="No staged work items pending triage.").send()
        return

    lines = [f"**Triage Queue** — {len(work_files)} file(s)\n"]
    for fname in work_files:
        try:
            with open(os.path.join(work_dir, fname), encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            items = data.get("items", [])
            lines.append(f"**{fname}** ({len(items)} item(s)):")
            for item in items:
                lines.append(
                    f"  - [{item.get('type', '?').upper()}] **{item.get('title', '?')}** "
                    f"({item.get('priority', '')})"
                )
        except Exception as exc:
            logger.warning("Could not read work file %s: %s", fname, exc)

    lines.append(
        "\n_To push items to DevOps, connect ADO MCP and use the approve workflow._"
    )
    await cl.Message(content="\n".join(lines)).send()


async def _cmd_wrap(workspace: str) -> None:
    """Generate and persist a session summary."""
    import uuid

    import yaml as yaml_lib

    from ea_workbench.models.work import SessionRecord

    session_id = cl.user_session.get("id", str(uuid.uuid4())[:8])
    history: list[dict[str, str]] = cl.user_session.get("message_history", [])

    if not history:
        await cl.Message(content="Nothing to wrap — conversation is empty.").send()
        return

    # Build a basic session summary from conversation
    topics: list[str] = []
    for msg in history:
        if msg["role"] == "user" and len(msg["content"]) < 200:
            topics.append(msg["content"][:80])

    topics = topics[:5]  # Keep top 5 user messages as topic hints

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    record = SessionRecord(
        session_id=session_id,
        started_at=cl.user_session.get("started_at", now),
        ended_at=now,
        session_link=f"/chat/{session_id}",
        intent=cl.user_session.get("intent", ""),
        summary=f"Session with {len(history)} exchanges covering: {'; '.join(topics[:3])}",
        artefacts_produced={},
        topics_discussed=topics,
    )

    sessions_dir = os.path.join(workspace, ".staging", "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    session_file = os.path.join(sessions_dir, f"{session_id}.yaml")

    with open(session_file, "w", encoding="utf-8") as fh:
        yaml_lib.dump(record.model_dump(), fh, default_flow_style=False, allow_unicode=True)

    await cl.Message(
        content=(
            f"**Session wrapped** and saved to `{session_file}`.\n\n"
            f"- Exchanges: {len(history)}\n"
            f"- Topics: {', '.join(topics[:3]) or '(none recorded)'}"
        )
    ).send()


async def _cmd_help() -> None:
    """Show available slash commands."""
    help_text = """**EA Workbench Commands**

| Command | Description |
|---|---|
| `/run <agent-id> [input-path]` | Execute a batch agent |
| `/status` | Show recent agent run summaries |
| `/staging` | Show staging area statistics |
| `/health` | Show latest wiki integrity results |
| `/triage` | Review staged work items |
| `/wrap` | Generate session summary and persist |
| `/help` | Show this help |
"""
    await cl.Message(content=help_text).send()
