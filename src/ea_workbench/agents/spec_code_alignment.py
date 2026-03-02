"""Spec-to-Code Alignment Checker — UC-8.

Compares a PR diff against a linked design spec, identifying new services not in
spec, schema drift, missing coverage, and unexpected dependencies.
Trigger: pr-created (alongside UC-3 architecture review).
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

AGENT_ID = "spec-code-alignment"


def _parse_input_paths(prompt: str) -> tuple[str, str]:
    """Split a '::' separated prompt into diff path and spec path.

    Args:
        prompt: Input string in format 'diff_path::spec_path'.

    Returns:
        Tuple of (diff_path, spec_path). If separator not found,
        returns (prompt, "") where the second element is empty.
    """
    if "::" in prompt:
        parts = prompt.split("::", 1)
        return parts[0].strip(), parts[1].strip()
    return prompt.strip(), ""


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the spec-to-code alignment check.

    `prompt` is expected in format 'diff_path::spec_path'.

    Args:
        config: Agent configuration from config.yaml.
        prompt: 'diff_path::spec_path' formatted string.
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Alignment report written to output/reviews/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    review_date = datetime.now(UTC).strftime("%Y-%m-%d")

    diff_path, spec_path = _parse_input_paths(prompt)

    # Resolve paths
    diff_abs = (
        Path(diff_path) if Path(diff_path).is_absolute()
        else Path(workspace) / diff_path
    )
    spec_abs = (
        Path(spec_path) if (spec_path and Path(spec_path).is_absolute())
        else (Path(workspace) / spec_path if spec_path else None)
    )

    # Load system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are a spec-to-code alignment checker. "
            "Compare the PR diff against the design spec and report mismatches."
        )

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    spec_desc = str(spec_abs) if spec_abs else "(no spec provided)"
    agent_prompt = (
        f"Check alignment between the PR diff at '{diff_abs}' "
        f"and the design spec at '{spec_desc}'. "
        f"Review date: {review_date}. "
        "Identify new services not in spec, schema drift, missing coverage, "
        "and unexpected dependencies."
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
        logger.error("Spec-code alignment SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)
        result_text = f"# Spec-to-Code Alignment\n\n⚠️ Agent error: {exc}"

    # Write output
    output_dir = Path(workspace) / "output" / "reviews"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"alignment-{run_id}.md"

    if not result_text:
        result_text = f"# Spec-to-Code Alignment — {run_id}\n\nNo findings."

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
        inputs=[str(diff_abs), spec_desc],
        outputs=[str(output_file)],
        summary={
            "diff_file": str(diff_abs),
            "spec_file": spec_desc,
            "output_file": str(output_file),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
