"""ADR Generator batch agent — Use Case 12.

Generates Architecture Decision Records from context documents
(transcripts, meeting notes, discussion threads).
"""

import logging
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ea_workbench.agents.base import write_manifest
from ea_workbench.agents.runner import load_config, load_prompt, resolve_agent
from ea_workbench.extraction.extractor import write_entity_staging
from ea_workbench.models.config import AgentConfig, WorkbenchConfig
from ea_workbench.models.extraction import ExtractionMetadata, StagedEntity
from ea_workbench.models.manifests import RunManifest

logger = logging.getLogger(__name__)

AGENT_ID = "adr-generator"
_ADR_TEMPLATE_MARKER = "## Context"


def _load_adr_index(workspace: str) -> list[dict[str, object]]:
    """Load the ADR _index.yaml and return its items list.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        List of ADR index entries (may be empty).
    """
    index_path = os.path.join(workspace, "architecture", "decisions", "_index.yaml")
    try:
        with open(index_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data.get("items", [])
    except FileNotFoundError:
        logger.warning("ADR index not found at %s", index_path)
        return []


def _next_adr_number(items: list[dict[str, object]]) -> int:
    """Determine the next sequential ADR number.

    Args:
        items: Existing ADR index items.

    Returns:
        Next ADR number (1-indexed).
    """
    if not items:
        return 1
    numbers: list[int] = []
    for item in items:
        adr_id = str(item.get("id", ""))
        match = re.search(r"(\d+)$", adr_id)
        if match:
            numbers.append(int(match.group(1)))
    return (max(numbers) + 1) if numbers else 1


def _is_valid_adr_markdown(content: str) -> bool:
    """Check that the output contains the required ADR structure.

    Args:
        content: The generated markdown content.

    Returns:
        True if the required sections are present.
    """
    required_sections = ["## Context", "## Decision", "## Rationale", "## Consequences"]
    return all(section in content for section in required_sections)


def _extract_staged_entities_from_output(
    output: str,
    run_id: str,
    source: str,
) -> list[StagedEntity]:
    """Parse staged entity YAML blocks from agent output if present.

    The agent may embed a YAML block starting with '```yaml' and containing
    an 'entities:' list.

    Args:
        output: Raw agent output text.
        run_id: The current run ID.
        source: The source file path.

    Returns:
        List of validated StagedEntity objects.
    """
    entities: list[StagedEntity] = []

    # Find YAML code blocks in output
    yaml_blocks = re.findall(r"```yaml\n(.*?)```", output, re.DOTALL)
    for block in yaml_blocks:
        try:
            data = yaml.safe_load(block)
            if isinstance(data, dict) and "entities" in data:
                for raw in data["entities"]:
                    try:
                        entity = StagedEntity.model_validate(raw)
                        if entity.confidence >= 0.5:
                            entities.append(entity)
                    except Exception as exc:
                        logger.warning("Skipping invalid entity in output: %s", exc)
        except yaml.YAMLError as exc:
            logger.debug("YAML block could not be parsed: %s", exc)

    return entities


async def run(
    config: AgentConfig,
    prompt: str,
    workspace: str,
) -> RunManifest:
    """Execute the ADR Generator agent.

    Args:
        config: Agent configuration from config.yaml.
        prompt: Path to the context document (transcript, meeting notes).
        workspace: Path to the PFC workspace root.

    Returns:
        Completed RunManifest.
    """
    import time

    from claude_code_sdk import ClaudeCodeOptions, ResultMessage
    from claude_code_sdk import query as sdk_query

    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    start = time.monotonic()
    runs_dir = os.path.join(workspace, ".agents", "runs")

    # Load ADR index for context
    adr_items = _load_adr_index(workspace)
    next_num = _next_adr_number(adr_items)
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    # Load and populate the system prompt template
    prompt_file = os.path.join(workspace, config.prompt)
    try:
        system_prompt = load_prompt(prompt_file)
    except FileNotFoundError:
        logger.warning("ADR Generator prompt not found at %s — using minimal prompt", prompt_file)
        system_prompt = (
            "Generate an Architecture Decision Record from the provided context document. "
            "Follow the Stanmore ADR template: Context → Decision → Rationale → Consequences."
        )

    # Substitute context into prompt
    system_prompt = system_prompt.replace("{{ADR_INDEX}}", str(adr_items))
    system_prompt = system_prompt.replace("{{CWD}}", workspace)
    system_prompt = system_prompt.replace("{{RUN_ID}}", run_id)
    system_prompt = system_prompt.replace("{{TIMESTAMP}}", timestamp)
    system_prompt = system_prompt.replace("{{SOURCE_PATH}}", prompt)
    system_prompt = system_prompt.replace(
        "{{ADR_INDEX_PATH}}",
        os.path.join(workspace, "architecture", "decisions", "_index.yaml"),
    )

    # Build the user prompt
    user_prompt = (
        f"Generate an Architecture Decision Record from the context document at: {prompt}\n\n"
        f"Next ADR number: ADR-{next_num:03d}\n"
        f"Today's date: {today}\n\n"
        "Read the file, analyse the decision context, and produce a complete ADR "
        "following the Stanmore template. "
        "If architectural elements are mentioned, include a YAML code block with "
        "extracted entities following the staging format."
    )

    model = config.model
    if "${" in model:
        model = "claude-sonnet-4-6"

    options = ClaudeCodeOptions(
        system_prompt=system_prompt,
        allowed_tools=["Read", "Write"],
        cwd=workspace,
        model=model,
        max_turns=5,
        permission_mode="acceptEdits",
    )

    result_text = ""
    tokens_consumed = 0
    run_status = "completed"
    error_msg: str | None = None

    try:
        async for message in sdk_query(prompt=user_prompt, options=options):
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
        logger.error("ADR Generator SDK error: %s", exc)
        run_status = "failed"
        error_msg = str(exc)

    # Write ADR to output directory if result looks like valid ADR markdown
    outputs: list[str] = []
    entities_extracted = 0

    if run_status == "completed" and result_text:
        if _is_valid_adr_markdown(result_text):
            output_dir = os.path.join(workspace, config.output_dir or "architecture/decisions")
            os.makedirs(output_dir, exist_ok=True)
            adr_filename = f"ADR-{next_num:03d}-draft.md"
            adr_path = os.path.join(output_dir, adr_filename)
            with open(adr_path, "w", encoding="utf-8") as fh:
                fh.write(result_text)
            outputs.append(adr_path)
            logger.info("ADR draft written: %s", adr_path)
        else:
            logger.warning("Agent output does not contain required ADR sections — not written")
            run_status = "partial"

        # Extract and stage entities from output
        entities = _extract_staged_entities_from_output(result_text, run_id, prompt)
        if entities:
            try:
                staging_path = await write_entity_staging(
                    entities=entities,
                    relationships=[],
                    agent_id=AGENT_ID,
                    run_id=run_id,
                    source=prompt,
                    workspace=workspace,
                )
                outputs.append(staging_path)
                entities_extracted = len(entities)
            except Exception as exc:
                logger.warning("Entity staging failed: %s", exc)

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
        inputs=[prompt],
        outputs=outputs,
        entities_extracted=entities_extracted,
        summary={
            "adr_number": f"ADR-{next_num:03d}",
            "output_valid": _is_valid_adr_markdown(result_text),
            "result_length": len(result_text),
        },
        error=error_msg,
    )

    write_manifest(manifest, runs_dir)
    return manifest
