"""Spec Decomposition Agent — UC-6.

Decomposes a parent spec page into draft child pages with entity staging.
Writes child pages to specs/tier2/{slug}/index.md in the workspace.
"""

import logging
import re
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

AGENT_ID = "spec-decomposition"


def _load_parent_page(workspace: str, prompt: str) -> str:
    """Load the content of the parent spec page.

    Args:
        workspace: Path to the PFC workspace root.
        prompt: File path (relative to workspace or absolute).

    Returns:
        File content as string, or placeholder if not found.
    """
    path = Path(prompt) if Path(prompt).is_absolute() else Path(workspace) / prompt
    if not path.exists():
        return f"(Parent page not found: {path})"
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"(Could not read parent page: {exc})"


def _load_wiki_tree(workspace: str, max_depth: int = 2) -> str:
    """Walk the specs/ tree and return a structured summary up to max_depth.

    Args:
        workspace: Path to the PFC workspace root.
        max_depth: Maximum directory depth to include (relative to specs/).

    Returns:
        Multi-line text tree summary.
    """
    specs_dir = Path(workspace) / "specs"
    if not specs_dir.exists():
        return "(specs/ directory not found)"

    lines: list[str] = ["specs/"]
    for md_path in sorted(specs_dir.rglob("*.md")):
        rel = md_path.relative_to(specs_dir)
        parts = rel.parts
        depth = len(parts) - 1  # depth relative to specs/
        if depth > max_depth:
            continue
        indent = "  " * depth
        lines.append(f"{indent}├── {rel}")

    if len(lines) == 1:
        lines.append("  (empty)")
    return "\n".join(lines)


def _load_capability_summary(workspace: str) -> str:
    """Load a brief capability model summary.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Short text summary of top-level capabilities.
    """
    cap_path = Path(workspace) / "capabilities" / "capability-model.yaml"
    if not cap_path.exists():
        return "(capability model not found)"
    try:
        with cap_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        caps = data.get("capabilities", [])
        lines = []
        for cap in caps[:10]:
            lines.append(f"- {cap.get('name', '?')} (level {cap.get('level', '?')})")
            for child in cap.get("children", [])[:3]:
                lines.append(f"  - {child.get('name', '?')}")
        return "\n".join(lines) if lines else "(no capabilities)"
    except Exception as exc:
        logger.warning("Could not load capability model: %s", exc)
        return "(could not load capability model)"


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the spec decomposition agent.

    Takes the parent page at `prompt` and produces draft child pages in
    specs/tier2/. Also triggers entity staging if extraction blocks are found.

    Args:
        config: Agent configuration from config.yaml.
        prompt: File path of the parent spec (relative to workspace or absolute).
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest with outputs listing written child pages.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    # Load context for template variables
    parent_content = _load_parent_page(workspace, prompt)
    wiki_tree = _load_wiki_tree(workspace, max_depth=2)
    capability_summary = _load_capability_summary(workspace)

    # Load and populate system prompt
    prompt_path = Path(workspace) / config.prompt
    try:
        system_prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        system_prompt = "You are a spec decomposition agent. Write child pages from the parent spec."

    system_prompt = system_prompt.replace("{{CAPABILITY_MODEL}}", capability_summary)
    system_prompt = system_prompt.replace("{{PARENT_PAGE_CONTENT}}", parent_content)
    system_prompt = system_prompt.replace("{{ELEMENT_REGISTRY_SUMMARY}}", "(registry not loaded)")
    system_prompt = system_prompt.replace("{{WIKI_TREE_SUMMARY}}", wiki_tree)

    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    target_path = Path(prompt) if Path(prompt).is_absolute() else Path(workspace) / prompt
    agent_prompt = (
        f"Decompose the parent spec at '{target_path}' into child pages. "
        "Write each child page to specs/tier2/{{slug}}/index.md. "
        "Include extraction YAML blocks for any new entities identified."
    )

    result_text = ""
    run_status = "completed"
    error_msg: str | None = None
    tokens_consumed = 0

    # Snapshot of tier2 before run to find new files
    tier2_dir = Path(workspace) / "specs" / "tier2"
    tier2_dir.mkdir(parents=True, exist_ok=True)
    before_files = set(tier2_dir.rglob("*.md"))

    try:
        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            allowed_tools=["Read", "Write"],
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
        logger.error("Spec decomposition SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)

    # Discover written child pages
    after_files = set(tier2_dir.rglob("*.md"))
    new_files = sorted(str(f) for f in (after_files - before_files))

    # Stage any entities found in extraction blocks in the new files
    entities_staged = 0
    staging_dir = Path(workspace) / ".staging" / "entities"
    staging_dir.mkdir(parents=True, exist_ok=True)

    for child_file in new_files:
        try:
            content = Path(child_file).read_text(encoding="utf-8")
            extraction_match = re.search(
                r"```ya?ml\s*\n(.*?extraction:.*?)```", content, re.DOTALL
            )
            if extraction_match:
                extraction_data = yaml.safe_load(extraction_match.group(1))
                if isinstance(extraction_data, dict) and "extraction" in extraction_data:
                    entities = extraction_data["extraction"].get("entities", [])
                    if entities:
                        staging_file = staging_dir / f"spec-decomp_{run_id}_{Path(child_file).stem}.yaml"
                        staging_payload = {
                            "metadata": {
                                "extracted_by": AGENT_ID,
                                "run_id": run_id,
                                "timestamp": timestamp,
                                "source": child_file,
                            },
                            "entities": entities,
                        }
                        with staging_file.open("w", encoding="utf-8") as fh:
                            yaml.dump(staging_payload, fh, default_flow_style=False)
                        entities_staged += len(entities)
        except Exception as exc:
            logger.warning("Could not stage entities from %s: %s", child_file, exc)

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
        outputs=new_files,
        entities_extracted=entities_staged,
        summary={"child_pages_written": len(new_files), "entities_staged": entities_staged},
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
