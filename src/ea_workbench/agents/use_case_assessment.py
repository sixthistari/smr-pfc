"""Use-Case Assessment Agent — UC-2.

Takes a structured use-case submission markdown and produces a scored assessment
matching the AI CoE template. Judgment only — the architect decides.
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

AGENT_ID = "use-case-assessment"

_DEFAULT_CRITERIA = """
## Assessment Criteria

- **Business Value** (25%): Measurable outcomes, stakeholder benefit, ROI potential
- **Feasibility** (20%): Technical feasibility, team capability, timeline realism
- **Data Readiness** (20%): Data availability, quality, governance compliance
- **Risk** (15%): Ethical, operational, and compliance risks (lower score = higher risk)
- **Strategic Alignment** (20%): Alignment with EA roadmap, AI CoE priorities
"""


def _load_assessment_criteria(workspace: str) -> str:
    """Read the assessment criteria file or return embedded defaults.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Assessment criteria content string.
    """
    criteria_path = Path(workspace) / "specs" / "_assessment-criteria.md"
    if criteria_path.exists():
        try:
            return criteria_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not read assessment criteria: %s", exc)
    return _DEFAULT_CRITERIA


def _extract_recommendation(result_text: str) -> str:
    """Extract the recommendation keyword from agent output.

    Args:
        result_text: Raw text output from the agent.

    Returns:
        One of 'Approve', 'Conditional', 'Defer', 'Reject', or 'unknown'.
    """
    match = re.search(
        r"\b(Approve|Conditional|Defer|Reject)\b", result_text, re.IGNORECASE
    )
    if match:
        return match.group(1).capitalize()
    return "unknown"


def _slug_from_path(path: str) -> str:
    """Normalise a file path to a slug suitable for output filenames.

    Args:
        path: File path string.

    Returns:
        Slug string (lowercase, hyphens, no extension).
    """
    name = Path(path).stem
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "submission"


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the use-case assessment for a single submission file.

    `prompt` is treated as the submission file path (relative to workspace or absolute).

    Args:
        config: Agent configuration from config.yaml.
        prompt: File path of the use-case submission to assess.
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Assessment written to output/assessments/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    # Resolve file path
    submission_path = (
        Path(prompt) if Path(prompt).is_absolute() else Path(workspace) / prompt
    )
    slug = _slug_from_path(str(submission_path))

    # Load context
    criteria = _load_assessment_criteria(workspace)
    roadmap_path = Path(workspace) / "specs" / "_roadmap-summary.md"
    roadmap_summary = (
        roadmap_path.read_text(encoding="utf-8")
        if roadmap_path.exists()
        else "(roadmap not available)"
    )

    # Load and populate system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are an AI CoE use-case assessor. "
            "Score the submission and produce a structured assessment."
        )

    system_prompt = system_prompt.replace("{{ROADMAP_SUMMARY}}", roadmap_summary)
    system_prompt = system_prompt.replace("{{ASSESSMENT_CRITERIA}}", criteria)

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Assess the use-case submission at '{submission_path}'. "
        "Read the file, score it against the criteria, and produce a structured assessment "
        "with a clear recommendation (Approve / Conditional / Defer / Reject)."
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
        logger.error("Use-case assessment SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)
        result_text = f"## Assessment\n\n⚠️ Agent error: {exc}"

    recommendation = _extract_recommendation(result_text)

    # Write assessment output
    output_dir = Path(workspace) / "output" / "assessments"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{slug}-assessment.md"

    if not result_text:
        result_text = f"## Use-Case Assessment — {slug}\n\nNo assessment produced."

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
        inputs=[str(submission_path)],
        outputs=[str(output_file)],
        summary={
            "recommendation": recommendation,
            "submission_file": str(submission_path),
            "output_file": str(output_file),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
