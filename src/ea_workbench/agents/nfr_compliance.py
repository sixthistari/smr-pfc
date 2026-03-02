"""NFR Compliance Report Generator — UC-10.

Reads a solution spec's NFR table and optional metrics, then produces a
compliance scorecard with per-category pass/warn/fail status and trend.
"""

import logging
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from claude_code_sdk import ClaudeCodeOptions, ResultMessage, query

from ea_workbench.agents.base import write_manifest
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest

logger = logging.getLogger(__name__)

AGENT_ID = "nfr-compliance"


def _load_nfr_baseline(workspace: str) -> str:
    """Read the NFR baseline index or return a placeholder.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        NFR baseline content string, or placeholder if not found.
    """
    baseline_path = Path(workspace) / "specs" / "_nfr_index.yaml"
    if baseline_path.exists():
        try:
            return baseline_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not read NFR baseline: %s", exc)
    return "(NFR baseline not found — using spec-defined thresholds only)"


def _count_status(result_text: str) -> tuple[int, int, int]:
    """Count pass/warn/fail occurrences in result text.

    Args:
        result_text: Raw agent output.

    Returns:
        Tuple of (pass_count, warn_count, fail_count).
    """
    text_lower = result_text.lower()
    pass_count = len(re.findall(r"\bpass\b", text_lower))
    warn_count = len(re.findall(r"\bwarn\b", text_lower))
    fail_count = len(re.findall(r"\bfail\b", text_lower))
    return pass_count, warn_count, fail_count


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the NFR compliance report for a spec or metrics file.

    `prompt` is treated as the solution spec or metrics file path.

    Args:
        config: Agent configuration from config.yaml.
        prompt: File path of the spec/metrics to assess.
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Scorecard written to output/compliance/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    report_date = datetime.now(UTC).strftime("%Y-%m-%d")

    # Resolve file path
    spec_path = (
        Path(prompt) if Path(prompt).is_absolute() else Path(workspace) / prompt
    )

    # Load NFR baseline
    nfr_baseline = _load_nfr_baseline(workspace)

    # Load system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are an NFR compliance analyst. "
            "Produce a compliance scorecard from the spec's NFR table."
        )

    system_prompt = system_prompt.replace("{{NFR_BASELINE}}", nfr_baseline)

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Produce an NFR compliance scorecard for the spec at '{spec_path}' "
        f"for report date {report_date}. "
        "Extract all NFR categories, compare against targets, and produce a "
        "compliance table with pass/warn/fail status and trend."
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
            max_turns=6,
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
        logger.error("NFR compliance SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)
        result_text = f"# NFR Compliance Scorecard\n\n⚠️ Agent error: {exc}"

    pass_count, warn_count, fail_count = _count_status(result_text)
    categories_assessed = pass_count + warn_count + fail_count

    # Write output
    output_dir = Path(workspace) / "output" / "compliance"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"nfr-{report_date}.md"

    if not result_text:
        result_text = f"# NFR Compliance Scorecard — {report_date}\n\nNo data produced."

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
            "categories_assessed": categories_assessed,
            "pass_count": pass_count,
            "warn_count": warn_count,
            "fail_count": fail_count,
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
