"""Design-Time Guardrail Agent — UC-7.

Checks a changed spec/wiki page against principles, standards, NFRs and the
element registry. Produces a review comment markdown file in .staging/work/.
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

AGENT_ID = "guardrail"


def _load_index_summary(index_path: str) -> str:
    """Read an _index.yaml and render it as a short human-readable list.

    Args:
        index_path: Absolute path to the _index.yaml file.

    Returns:
        Multi-line string summary, or empty string if file is missing/invalid.
    """
    path = Path(index_path)
    if not path.exists():
        return "(not available)"

    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as exc:
        logger.warning("Could not load index %s: %s", index_path, exc)
        return "(could not load)"

    if not isinstance(data, dict):
        return "(empty)"

    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"- **{key}**: {', '.join(str(v) for v in value[:5])}")
        elif isinstance(value, dict):
            lines.append(f"- **{key}**: {len(value)} entries")
        else:
            lines.append(f"- **{key}**: {value}")
    return "\n".join(lines) if lines else "(empty)"


def _load_text_summary(file_path: str, max_lines: int = 30) -> str:
    """Load the first max_lines of a text file as a summary.

    Args:
        file_path: Path to the file.
        max_lines: Maximum number of lines to return.

    Returns:
        Truncated file content, or a placeholder if not found.
    """
    path = Path(file_path)
    if not path.exists():
        return "(not available)"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[:max_lines]
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Could not read %s: %s", file_path, exc)
        return "(could not load)"


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the guardrail check for a single spec file.

    `prompt` is treated as the file path to check (relative to workspace or absolute).

    Args:
        config: Agent configuration from config.yaml.
        prompt: File path of the spec to review (relative or absolute).
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Review comment written to .staging/work/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    # Resolve the file path to check
    target_path = Path(prompt) if Path(prompt).is_absolute() else Path(workspace) / prompt

    # Load context summaries for template substitution
    standards_summary = _load_text_summary(
        str(Path(workspace) / "specs" / "_standards_index.yaml"), max_lines=20
    )
    nfr_summary = _load_text_summary(
        str(Path(workspace) / "specs" / "_nfr_index.yaml"), max_lines=20
    )
    principles_summary = _load_text_summary(
        str(Path(workspace) / "specs" / "_principles_index.yaml"), max_lines=20
    )

    # Load system prompt and populate template variables
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = "You are a design-time guardrail. Review the file for standards compliance."

    system_prompt = system_prompt.replace("{{STANDARDS_SUMMARY}}", standards_summary)
    system_prompt = system_prompt.replace("{{NFR_SUMMARY}}", nfr_summary)
    system_prompt = system_prompt.replace("{{PRINCIPLES_SUMMARY}}", principles_summary)

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Review the spec file at '{target_path}'. "
        "Read its content and produce a guardrail review comment following the output format."
    )

    result_text = ""
    run_status = "completed"
    error_msg: str | None = None
    tokens_consumed = 0

    try:
        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            allowed_tools=["Read"],
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
        logger.error("Guardrail SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)
        result_text = f"## Guardrail Review\n\n⚠️ Agent error: {exc}"

    # Write review comment to .staging/work/
    work_dir = Path(workspace) / ".staging" / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    output_file = work_dir / f"guardrail_{run_id}.md"

    if not result_text:
        result_text = f"## Guardrail Review — {target_path.name}\n\nNo findings."

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
        inputs=[str(target_path)],
        outputs=[str(output_file)],
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
