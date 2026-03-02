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
    elif command == "/capture":
        await _cmd_capture(parts[1:], workspace)
    elif command == "/capabilities":
        await _cmd_capabilities(workspace)
    elif command == "/analytics":
        await _cmd_analytics(workspace)
    elif command == "/migrate":
        await _cmd_migrate(workspace)
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
    """Present staged entity files for approve/reject review."""
    entities_dir = os.path.join(workspace, ".staging", "entities")

    import yaml

    if not os.path.exists(entities_dir):
        await cl.Message(content="No staged entity files found.").send()
        return

    entity_files = sorted(f for f in os.listdir(entities_dir) if f.endswith(".yaml"))
    if not entity_files:
        await cl.Message(content="No staged entities pending triage.").send()
        return

    db_path = os.path.join(workspace, "registry.db")

    for fname in entity_files:
        full_path = os.path.join(entities_dir, fname)
        try:
            with open(full_path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            entities = data.get("entities", []) if isinstance(data, dict) else []
            entity_names = [e.get("name", "?") for e in entities if isinstance(e, dict)]
            summary = ", ".join(entity_names[:3])
            if len(entity_names) > 3:
                summary += f" +{len(entity_names) - 3} more"
        except Exception as exc:
            logger.warning("Could not read staging file %s: %s", fname, exc)
            summary = "(unreadable)"

        actions = [
            cl.Action(
                name="approve_staging",
                value=f"{full_path}||{workspace}||{db_path}",
                label="Approve",
                description=f"Approve and upsert {fname} to registry",
            ),
            cl.Action(
                name="reject_staging",
                value=full_path,
                label="Reject",
                description=f"Reject and delete {fname}",
            ),
        ]
        await cl.Message(
            content=f"**{fname}**\n{summary}",
            actions=actions,
        ).send()


@cl.action_callback("approve_staging")
async def on_approve_staging(action: cl.Action) -> None:
    """Handle approval of a staging file — upserts to registry."""
    parts = action.value.split("||")
    if len(parts) != 3:
        await cl.Message(content="⚠️ Malformed action value — cannot approve.").send()
        return
    staging_file, workspace, db_path = parts

    from ea_workbench.extraction.review import approve_to_registry, list_pending

    try:
        count = await approve_to_registry(staging_file, workspace, db_path)
        await cl.Message(content=f"✅ Approved: `{os.path.basename(staging_file)}` — {count} element(s) added to registry.").send()
    except Exception as exc:
        logger.error("Approve action failed: %s", exc)
        await cl.Message(content=f"⚠️ Approval failed: {exc}").send()
        return

    counts = await list_pending(workspace)
    total = sum(counts.values())
    await cl.Message(content=f"_Staging queue: {total} file(s) remaining._").send()


@cl.action_callback("reject_staging")
async def on_reject_staging(action: cl.Action) -> None:
    """Handle rejection of a staging file — deletes it."""
    staging_file = action.value

    from ea_workbench.extraction.review import list_pending, reject_staged_entities

    try:
        await reject_staged_entities(staging_file)
        await cl.Message(content=f"🗑️ Rejected: `{os.path.basename(staging_file)}` deleted.").send()
    except Exception as exc:
        logger.error("Reject action failed: %s", exc)
        await cl.Message(content=f"⚠️ Rejection failed: {exc}").send()
        return

    workspace = os.path.dirname(os.path.dirname(os.path.dirname(staging_file)))
    counts = await list_pending(workspace)
    total = sum(counts.values())
    await cl.Message(content=f"_Staging queue: {total} file(s) remaining._").send()


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


async def _cmd_capture(args: list[str], workspace: str) -> None:
    """Scaffold a motivation layer record for user confirmation.

    Usage: /capture <type> <domain>
      type: need | requirement | engagement
      domain: e.g. safety, enterprise, technology
    """
    import uuid as _uuid
    from datetime import UTC as _UTC
    from datetime import datetime as _datetime

    if len(args) < 2:
        await cl.Message(
            content=(
                "Usage: `/capture <type> <domain>`\n\n"
                "Types: `need`, `requirement`, `engagement`\n"
                "Example: `/capture need safety`"
            )
        ).send()
        return

    record_type = args[0].lower()
    domain = args[1].lower()
    valid_types = {"need", "requirement", "engagement"}

    if record_type not in valid_types:
        await cl.Message(
            content=f"Unknown capture type: `{record_type}`. Valid types: {', '.join(sorted(valid_types))}"
        ).send()
        return

    record_id = f"{record_type[:3]}-{str(_uuid.uuid4())[:8]}"
    now = _datetime.now(_UTC).strftime("%Y-%m-%d")

    if record_type == "need":
        scaffold = (
            f"```yaml\n"
            f"id: {record_id}\n"
            f"domain: {domain}\n"
            f"statement: \"<Describe the stakeholder need here>\"\n"
            f"stakeholders:\n"
            f"  - \"<stakeholder name>\"\n"
            f"drivers: []\n"
            f"outcomes: []\n"
            f"priority: medium\n"
            f"requirements_derived: []\n"
            f"```"
        )
    elif record_type == "requirement":
        scaffold = (
            f"```yaml\n"
            f"id: {record_id}\n"
            f"domain: {domain}\n"
            f"traces_to_need: \"<need-id>\"\n"
            f"statement: \"<Describe the requirement here>\"\n"
            f"type: functional\n"
            f"acceptance_criteria:\n"
            f"  - \"<Criterion 1>\"\n"
            f"realised_by: []\n"
            f"```"
        )
    else:  # engagement
        scaffold = (
            f"```yaml\n"
            f"id: {record_id}\n"
            f"title: \"<Engagement title>\"\n"
            f"date: \"{now}\"\n"
            f"type: workshop\n"
            f"participants:\n"
            f"  - name: \"<Participant Name>\"\n"
            f"    role: \"<role>\"\n"
            f"context: \"<Brief context of the session>\"\n"
            f"needs_identified: []\n"
            f"```"
        )

    async with cl.Step(name=f"Capture {record_type.capitalize()}") as step:
        step.input = f"Type: `{record_type}` | Domain: `{domain}`"
        step.output = f"Scaffold generated — fill in the details below and confirm."

    await cl.Message(
        content=(
            f"**{record_type.capitalize()} scaffold** for domain `{domain}`:\n\n"
            f"{scaffold}\n\n"
            f"_Edit the YAML above, then paste it back with `/capture confirm <yaml>` to save._"
        )
    ).send()


async def _cmd_capabilities(workspace: str) -> None:
    """Show capability model summary — domain count, capability count, max depth."""
    from ea_workbench.utils.capability_bootstrap import validate_capability_model

    try:
        summary = validate_capability_model(workspace)
    except Exception as exc:
        await cl.Message(content=f"⚠️ Could not load capability model: {exc}").send()
        return

    status_icon = "✅" if summary.get("is_valid") else "⚠️"
    lines = [
        f"**Capability Model** {status_icon}",
        "",
        f"- Domains: {summary.get('domain_count', '?')}",
        f"- Total capabilities: {summary.get('capability_count', '?')}",
        f"- Max depth: {summary.get('max_depth', '?')}",
        f"- Valid: {summary.get('is_valid', '?')}",
    ]
    await cl.Message(content="\n".join(lines)).send()


async def _cmd_analytics(workspace: str) -> None:
    """Show practice artefact analytics — counts by type, domain coverage, idea→decision rate."""
    from ea_workbench.utils.practice_analytics import (
        analyse_practice_artefacts,
        format_analytics_report,
    )

    try:
        analytics = analyse_practice_artefacts(workspace)
        report = format_analytics_report(analytics)
    except Exception as exc:
        await cl.Message(content=f"⚠️ Could not compute analytics: {exc}").send()
        return

    await cl.Message(content=report).send()


async def _cmd_migrate(workspace: str) -> None:
    """Run the Phase 0 → Option C schema migration."""
    import os

    db_path = os.path.join(workspace, "registry.db")

    async with cl.Step(name="Schema Migration", show_input=True) as step:
        step.input = f"Database: `{db_path}`"
        try:
            from ea_workbench.registry.migration import migrate_phase0_to_option_c

            result = await migrate_phase0_to_option_c(db_path)
            step.output = (
                f"Migrated: {result['migrated']} | "
                f"Skipped: {result['skipped']} | "
                f"Errors: {len(result['errors'])}"
            )
        except Exception as exc:
            step.output = f"❌ Migration failed: {exc}"
            logger.error("Migration failed: %s", exc)
            return

    lines = [
        "**Phase 0 → Option C Migration Complete**",
        "",
        f"- Elements migrated: {result['migrated']}",
        f"- Elements skipped (unknown type): {result['skipped']}",
        f"- Errors: {len(result['errors'])}",
    ]
    if result["errors"]:
        lines.append("\n**Errors:**")
        for err in result["errors"][:5]:
            lines.append(f"  - {err}")
    await cl.Message(content="\n".join(lines)).send()


async def _cmd_help() -> None:
    """Show available slash commands."""
    help_text = """**EA Workbench Commands**

| Command | Description |
|---|---|
| `/run <agent-id> [input-path]` | Execute a batch agent |
| `/status` | Show recent agent run summaries |
| `/staging` | Show staging area statistics |
| `/health` | Show latest wiki integrity results |
| `/triage` | Review staged entities (Approve/Reject) |
| `/capture <type> <domain>` | Scaffold a motivation record (need/requirement/engagement) |
| `/capabilities` | Show capability model summary |
| `/analytics` | Show practice artefact counts, domain coverage, idea→decision rate |
| `/migrate` | Migrate Phase 0 data to Option C schema |
| `/wrap` | Generate session summary and persist |
| `/help` | Show this help |
"""
    await cl.Message(content=help_text).send()
