"""Standards & Patterns Register Enforcer — UC-15.

Checks a new/changed solution spec against the Standards Register (all pattern pages).
Produces a pattern applicability report and draft skeleton sections for missing patterns.
Trigger: wiki-commit (alongside UC-7 guardrail).
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

AGENT_ID = "standards-enforcer"


def _load_standards_register(workspace: str) -> str:
    """Load the Standards Register summary.

    Reads the standards index and any pattern page summaries.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Standards register content string or placeholder.
    """
    index_path = Path(workspace) / "specs" / "_standards_index.yaml"
    if not index_path.exists():
        return "(standards register not found)"
    try:
        content = index_path.read_text(encoding="utf-8")
        # Also try to include pattern page titles from standards directory
        standards_dir = Path(workspace) / "architecture" / "standards"
        if standards_dir.exists():
            pattern_names = [
                p.stem for p in sorted(standards_dir.glob("*.md"))[:20]
            ]
            if pattern_names:
                content += "\n\n## Available Patterns\n" + "\n".join(
                    f"- {n}" for n in pattern_names
                )
        return content
    except Exception as exc:
        logger.warning("Could not load standards register: %s", exc)
        return "(could not load standards register)"


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the standards enforcer for a single spec file.

    `prompt` is treated as the spec file path.

    Args:
        config: Agent configuration from config.yaml.
        prompt: File path of the spec to check.
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Applicability report written to output/reviews/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    review_date = datetime.now(UTC).strftime("%Y-%m-%d")

    # Resolve spec path
    spec_path = (
        Path(prompt) if Path(prompt).is_absolute() else Path(workspace) / prompt
    )

    # Load context
    standards_register = _load_standards_register(workspace)

    # Load system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are a standards enforcer. "
            "Check the spec against the Standards Register and report pattern applicability."
        )

    system_prompt = system_prompt.replace(
        "{{STANDARDS_REGISTER_SUMMARY}}", standards_register
    )

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Check the spec at '{spec_path}' against the Standards Register. "
        f"Review date: {review_date}. "
        "Produce a pattern applicability report and draft skeleton sections "
        "for any missing patterns."
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
        logger.error("Standards enforcer SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)
        result_text = f"# Standards & Patterns Report\n\n⚠️ Agent error: {exc}"

    # Write output
    output_dir = Path(workspace) / "output" / "reviews"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"standards-{run_id}.md"

    if not result_text:
        result_text = f"# Standards & Patterns Report — {run_id}\n\nNo findings."

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
        inputs=[str(spec_path)],
        outputs=[str(output_file)],
        summary={
            "spec_file": str(spec_path),
            "output_file": str(output_file),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
