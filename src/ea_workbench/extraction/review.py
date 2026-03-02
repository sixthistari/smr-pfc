"""Staging review workflow helpers — approve, reject, and list pending extractions."""

import logging
import os
import shutil

logger = logging.getLogger(__name__)


async def approve_staged_entities(staging_file: str, workspace: str) -> int:
    """Move a staging file to the approved directory.

    Args:
        staging_file: Path to the staging YAML file to approve.
        workspace: Path to the PFC workspace root.

    Returns:
        Number of files moved (1 on success, 0 if already absent).

    Raises:
        FileNotFoundError: If staging_file does not exist.
    """
    if not os.path.exists(staging_file):
        raise FileNotFoundError(f"Staging file not found: {staging_file}")

    approved_dir = os.path.join(workspace, ".staging", "approved")
    os.makedirs(approved_dir, exist_ok=True)

    filename = os.path.basename(staging_file)
    dest = os.path.join(approved_dir, filename)
    shutil.move(staging_file, dest)
    logger.info("Approved: %s → %s", staging_file, dest)
    return 1


async def reject_staged_entities(staging_file: str) -> None:
    """Delete a staging file (reject the extraction).

    Args:
        staging_file: Path to the staging YAML file to delete.

    Raises:
        FileNotFoundError: If staging_file does not exist.
    """
    if not os.path.exists(staging_file):
        raise FileNotFoundError(f"Staging file not found: {staging_file}")

    os.remove(staging_file)
    logger.info("Rejected and deleted: %s", staging_file)


async def list_pending(workspace: str) -> dict[str, int]:
    """Count pending staging files by directory.

    Args:
        workspace: Path to the PFC workspace root.

    Returns:
        Dict mapping directory name to file count.
    """
    staging_base = os.path.join(workspace, ".staging")
    subdirs = ["entities", "relationships", "work", "sessions"]
    result: dict[str, int] = {}

    for subdir in subdirs:
        dirpath = os.path.join(staging_base, subdir)
        if os.path.exists(dirpath):
            yaml_files = [
                f for f in os.listdir(dirpath)
                if f.endswith(".yaml") and not f.startswith(".")
            ]
            result[subdir] = len(yaml_files)
        else:
            result[subdir] = 0

    return result
