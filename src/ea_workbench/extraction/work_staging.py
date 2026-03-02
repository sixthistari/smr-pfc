"""Work artefact staging file writer."""

import logging
import os
from datetime import UTC, datetime

import yaml

from ea_workbench.models.work import StagedWorkItem, StagingWorkFile, StagingWorkMetadata

logger = logging.getLogger(__name__)


async def stage_work_items(
    items: list[StagedWorkItem],
    session_id: str,
    sequence: int,
    workspace: str,
) -> str:
    """Validate and write work items to the staging area.

    Args:
        items: List of staged work items to write.
        session_id: The chat session that produced these items.
        sequence: Sequential counter for this session (zero-padded to 3 digits).
        workspace: Path to the PFC workspace root.

    Returns:
        Path to the written staging file.

    Raises:
        ValueError: If any item is missing a provenance block.
    """
    # Validate provenance presence on all items
    for item in items:
        if not item.provenance:
            raise ValueError(
                f"Work item '{item.title}' is missing a required provenance block."
            )

    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    metadata = StagingWorkMetadata(
        extracted_by="chat-agent",
        session_id=session_id,
        timestamp=timestamp,
    )

    staging_file = StagingWorkFile(metadata=metadata, items=items)

    work_dir = os.path.join(workspace, ".staging", "work")
    os.makedirs(work_dir, exist_ok=True)

    filename = f"chat_{session_id}_{sequence:03d}.yaml"
    filepath = os.path.join(work_dir, filename)

    with open(filepath, "w", encoding="utf-8") as fh:
        yaml.dump(staging_file.model_dump(), fh, default_flow_style=False, allow_unicode=True)

    logger.info("Staged %d work items to %s", len(items), filepath)
    return filepath
