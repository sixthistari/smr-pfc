"""Multi-Format Export Agent — UC-14.

Takes a canonical wiki spec page and produces five output formats:
ArchiMate XML, Mermaid diagram, PlantUML diagram, business summary,
and technical summary markdown. All formats must cover the same elements.
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

AGENT_ID = "multi-format-export"


def _slug_from_path(path: str) -> str:
    """Normalise a file path to a URL-safe slug.

    Args:
        path: File path string.

    Returns:
        Lowercase hyphen-separated slug derived from the file stem.
    """
    name = Path(path).stem
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "spec"


def _output_dir_for_spec(workspace: str, slug: str) -> Path:
    """Compute the output directory for a given spec slug.

    Args:
        workspace: Path to the PFC workspace root.
        slug: Normalised spec slug.

    Returns:
        Path to the output directory for this spec's exports.
    """
    return Path(workspace) / "output" / "exports" / slug


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the multi-format export for a single spec file.

    `prompt` is treated as the spec file path (relative to workspace or absolute).

    Args:
        config: Agent configuration from config.yaml.
        prompt: File path of the spec to export.
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Five output files written to output/exports/{slug}/.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    # Resolve the spec file path
    spec_path = (
        Path(prompt) if Path(prompt).is_absolute() else Path(workspace) / prompt
    )
    slug = _slug_from_path(str(spec_path))

    # Create output directory before running the agent
    output_dir = _output_dir_for_spec(workspace, slug)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are an architecture documentation specialist. "
            "Produce five output formats from the spec file provided."
        )

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Export the spec at '{spec_path}' to five formats. "
        f"Write all output files to '{output_dir}/': "
        "archimate.xml, diagram.mmd, diagram.puml, business-summary.md, technical-summary.md. "
        "Ensure semantic equivalence across all formats."
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
            max_turns=15,
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
        logger.error("Multi-format export SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)

    # Discover what files were written
    expected_formats = ["archimate.xml", "diagram.mmd", "diagram.puml",
                        "business-summary.md", "technical-summary.md"]
    formats_written = [f for f in expected_formats if (output_dir / f).exists()]
    output_files = [str(output_dir / f) for f in formats_written]

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
        outputs=output_files,
        summary={
            "formats_written": formats_written,
            "spec_slug": slug,
            "output_dir": str(output_dir),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
