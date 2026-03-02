"""Wiki Structure Integrity Agent — UC-13.

Scans stanmore-pfc/specs/ for structural violations and produces a health report
manifest compatible with the /health command.
"""

import logging
import re
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml
from claude_code_sdk import ClaudeCodeOptions, ResultMessage, query

from ea_workbench.agents.base import write_manifest
from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest

logger = logging.getLogger(__name__)

AGENT_ID = "wiki-integrity"
_MAX_PAGE_LINES = 300
_LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def _scan_specs(workspace: str) -> list[Path]:
    """Walk specs/**/*.md and return all markdown file paths.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        List of Path objects for all .md files under specs/.
    """
    specs_dir = Path(workspace) / "specs"
    if not specs_dir.exists():
        return []
    return sorted(specs_dir.rglob("*.md"))


def _check_page(path: Path, content: str, workspace: str) -> list[dict]:
    """Check a single page for structural violations.

    Args:
        path: Absolute path to the markdown file.
        content: File content as a string.
        workspace: Path to the PFC workspace root.

    Returns:
        List of violation dicts with keys: type, path, message, severity.
    """
    violations: list[dict] = []
    workspace_path = Path(workspace)
    rel_path = str(path.relative_to(workspace_path))
    lines = content.splitlines()

    # Check 1 — missing-parent-link
    # Look for parent: in frontmatter OR a [[Parent]] link in first 20 lines
    has_parent = False
    in_frontmatter = False
    for i, line in enumerate(lines[:20]):
        if i == 0 and line.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and line.strip() == "---":
            in_frontmatter = False
            continue
        if in_frontmatter and line.startswith("parent:"):
            has_parent = True
            break
        if "[[" in line and "parent" in line.lower():
            has_parent = True
            break

    # Root-level index files are exempt from parent-link requirement
    is_root_index = path.name in ("index.md", "_index.md") and path.parent == Path(workspace) / "specs"
    if not has_parent and not is_root_index:
        violations.append({
            "type": "missing-parent-link",
            "path": rel_path,
            "message": f"Page has no parent: frontmatter or [[parent]] link in first 20 lines.",
            "severity": "error",
        })

    # Check 2 — oversized-page
    if len(lines) > _MAX_PAGE_LINES:
        violations.append({
            "type": "oversized-page",
            "path": rel_path,
            "message": f"Page has {len(lines)} lines (limit: {_MAX_PAGE_LINES}).",
            "severity": "warning",
        })

    # Check 3 — broken-link (wiki-style [[Link]] references)
    specs_dir = Path(workspace) / "specs"
    all_md_names = {p.stem.lower() for p in specs_dir.rglob("*.md")}
    all_md_names |= {p.name.lower() for p in specs_dir.rglob("*.md")}

    for match in _LINK_PATTERN.finditer(content):
        link_target = match.group(1).strip()
        # Strip anchors
        link_slug = link_target.split("|")[0].split("#")[0].strip().lower()
        if link_slug and link_slug not in all_md_names:
            violations.append({
                "type": "broken-link",
                "path": rel_path,
                "message": f"Broken wiki link: [[{link_target}]] — target not found in specs/.",
                "severity": "error",
            })

    return violations


async def run(config: AgentConfig, prompt: str, workspace: str) -> RunManifest:
    """Execute the wiki integrity check.

    Invokes Claude Code SDK with Read tool only, parses the output YAML block,
    and builds a RunManifest with summary keys expected by /health.

    Args:
        config: Agent configuration from config.yaml.
        prompt: Unused (workspace path is the input).
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest.
    """
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = str(Path(workspace) / ".agents" / "runs")

    # Pre-scan locally for fast summary even without SDK
    spec_paths = _scan_specs(workspace)
    local_violations: list[dict] = []
    for spec_path in spec_paths:
        try:
            content = spec_path.read_text(encoding="utf-8")
            local_violations.extend(_check_page(spec_path, content, workspace))
        except OSError as exc:
            logger.warning("Could not read %s: %s", spec_path, exc)

    pages_scanned = len(spec_paths)

    # Attempt SDK run for richer analysis
    sdk_summary: dict = {}
    sdk_violations: list[dict] = []
    model = config.model if "${" not in config.model else "claude-sonnet-4-6"

    prompt_text = (
        f"Scan the workspace at '{workspace}' for wiki structure violations in the specs/ directory. "
        "Output a YAML block with the results."
    )

    try:
        options = ClaudeCodeOptions(
            system_prompt="",
            allowed_tools=["Read"],
            cwd=workspace,
            model=model,
            max_turns=5,
            permission_mode="acceptEdits",
        )
        result_text = ""
        async for message in query(prompt=prompt_text, options=options):
            if isinstance(message, ResultMessage):
                result_text = message.result or ""

        # Parse YAML block from result
        yaml_match = re.search(r"```ya?ml\n(.*?)```", result_text, re.DOTALL)
        if not yaml_match:
            yaml_match = re.search(r"^---\n(.*?)^---", result_text, re.MULTILINE | re.DOTALL)
        if yaml_match:
            parsed = yaml.safe_load(yaml_match.group(1))
            if isinstance(parsed, dict):
                sdk_summary = parsed
                sdk_violations = parsed.get("violations", [])
    except Exception as exc:
        logger.warning("SDK run failed, falling back to local scan: %s", exc)

    # Merge: prefer SDK results if available, else use local
    if sdk_summary and "pages_scanned" in sdk_summary:
        all_violations = sdk_violations
        final_pages = sdk_summary.get("pages_scanned", pages_scanned)
    else:
        all_violations = local_violations
        final_pages = pages_scanned

    errors = [v for v in all_violations if v.get("severity") == "error"]
    warnings = [v for v in all_violations if v.get("severity") == "warning"]

    type_counts: Counter = Counter(v.get("type", "") for v in all_violations)
    top_type = type_counts.most_common(1)[0][0] if type_counts else "none"

    summary: dict[str, object] = {
        "pages_scanned": final_pages,
        "violations_found": len(errors),
        "warnings_found": len(warnings),
        "top_violation_type": top_type,
        "violations": all_violations,
    }

    duration = time.monotonic() - start
    manifest = RunManifest(
        agent_id=AGENT_ID,
        run_id=run_id,
        triggered_by="manual",
        timestamp=timestamp,
        duration_seconds=duration,
        model_used=model,
        tokens_consumed=0,
        status="completed",
        inputs=[workspace],
        outputs=[],
        summary=summary,
    )

    write_manifest(manifest, runs_dir)
    return manifest
