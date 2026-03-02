"""Stakeholder Communication Generator — UC-5.

Takes any wiki spec and produces three audience-specific communication variants:
framework/governance level, operational impact level, and technical detail level.
No information loss — same decisions, different expressions.
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

AGENT_ID = "stakeholder-comms"


def _load_spec_content(workspace: str, prompt: str) -> str:
    """Load spec content from a file path.

    Args:
        workspace: Path to the PFC workspace root.
        prompt: File path (absolute or relative to workspace).

    Returns:
        Spec content string, or placeholder if not found.
    """
    p = Path(prompt) if Path(prompt).is_absolute() else Path(workspace) / prompt
    if not p.exists():
        return "(spec file not found)"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not read spec %s: %s", p, exc)
        return "(could not read spec)"


def _slug_from_path(path: str) -> str:
    """Normalise a file path to a URL-safe slug.

    Args:
        path: File path string.

    Returns:
        Lowercase hyphenated slug derived from file stem.
    """
    name = Path(path).stem
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "spec"


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the stakeholder comms generator for a single spec file.

    `prompt` is treated as the spec file path (relative to workspace or absolute).

    Args:
        config: Agent configuration from config.yaml.
        prompt: File path of the spec to communicate.
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest. Three variant files written to output/communications/{slug}/.
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

    # Load spec content
    spec_content = _load_spec_content(workspace, prompt)

    # Create output directory
    output_dir = Path(workspace) / "output" / "communications" / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load and populate system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = (
            "You are a stakeholder communication specialist. "
            "Produce three audience-specific variants of the spec."
        )

    system_prompt = system_prompt.replace("{{SPEC_CONTENT}}", spec_content)

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    agent_prompt = (
        f"Produce three communication variants for the spec at '{spec_path}'. "
        f"Write the following files to '{output_dir}/': "
        f"framework-{slug}.md, operational-{slug}.md, technical-{slug}.md. "
        "All three must cover the same architectural decisions."
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
            max_turns=10,
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
        logger.error("Stakeholder comms SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)

    # Discover written variant files
    expected_variants = [
        f"framework-{slug}.md",
        f"operational-{slug}.md",
        f"technical-{slug}.md",
    ]
    variants_written = [f for f in expected_variants if (output_dir / f).exists()]
    output_files = [str(output_dir / f) for f in variants_written]

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
            "variants_written": len(variants_written),
            "spec_slug": slug,
            "output_dir": str(output_dir),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
