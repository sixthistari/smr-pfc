"""Architecture Review Gate Agent — UC-3.

Checks a PR diff or solution spec against the Standards Register and NFR baseline.
Produces a compliance report — flags only, not a merge gate.
Trigger: pr-created.
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

AGENT_ID = "architecture-review"


def _load_standards_summary(workspace: str, max_lines: int = 30) -> str:
    """Load the standards index summary.

    Args:
        workspace: Path to the PFC workspace root.
        max_lines: Maximum lines to return.

    Returns:
        Standards summary string or placeholder.
    """
    path = Path(workspace) / "specs" / "_standards_index.yaml"
    if not path.exists():
        return "(standards index not found)"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[:max_lines]
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Could not read standards index: %s", exc)
        return "(could not load standards)"


def _load_nfr_summary(workspace: str, max_lines: int = 20) -> str:
    """Load the NFR index summary.

    Args:
        workspace: Path to the PFC workspace root.
        max_lines: Maximum lines to return.

    Returns:
        NFR summary string or placeholder.
    """
    path = Path(workspace) / "specs" / "_nfr_index.yaml"
    if not path.exists():
        return "(NFR index not found)"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[:max_lines]
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Could not read NFR index: %s", exc)
        return "(could not load NFRs)"


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the architecture review gate.

    `prompt` is treated as the PR diff or spec file path.

    Args:
        config: Agent configuration from config.yaml.
        prompt: File path of the PR diff or spec to review.
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Compliance report written to output/reviews/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    review_date = datetime.now(UTC).strftime("%Y-%m-%d")

    # Resolve file path
    input_path = (
        Path(prompt) if Path(prompt).is_absolute() else Path(workspace) / prompt
    )

    # Load context
    standards_summary = _load_standards_summary(workspace)
    nfr_summary = _load_nfr_summary(workspace)

    # Load system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are an architecture review gate. "
            "Check the input against standards and produce a compliance report."
        )

    system_prompt = system_prompt.replace("{{STANDARDS_SUMMARY}}", standards_summary)
    system_prompt = system_prompt.replace("{{NFR_SUMMARY}}", nfr_summary)

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Review the input at '{input_path}' against the Standards Register and NFR baseline. "
        f"Review date: {review_date}. Produce a compliance report with pass/fail/review-needed "
        "for each applicable check. Do not block — flag only."
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
        logger.error("Architecture review SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)
        result_text = f"# Architecture Review\n\n⚠️ Agent error: {exc}"

    # Write output
    output_dir = Path(workspace) / "output" / "reviews"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"arch-review-{run_id}.md"

    if not result_text:
        result_text = f"# Architecture Review — {run_id}\n\nNo findings."

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
        inputs=[str(input_path)],
        outputs=[str(output_file)],
        summary={
            "input_file": str(input_path),
            "output_file": str(output_file),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
