"""Motivation layer capture handlers — write Need, Engagement, and Requirement records.

These handlers persist structured motivation layer artefacts to the workspace
using the models from ea_workbench.models.motivation.
"""

import logging
import os
from pathlib import Path

import yaml

from ea_workbench.models.motivation import Engagement, Need, Requirement

logger = logging.getLogger(__name__)


async def write_need(need: Need, workspace: str) -> str:
    """Append a Need to needs/by-domain/{domain}.yaml.

    Args:
        need: The Need model to persist.
        workspace: Path to the PFC workspace root.

    Returns:
        Absolute path to the file that was written/appended.
    """
    domain_dir = Path(workspace) / "needs" / "by-domain"
    domain_dir.mkdir(parents=True, exist_ok=True)
    file_path = domain_dir / f"{need.domain}.yaml"

    existing: list[dict] = []
    if file_path.exists():
        try:
            with file_path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if isinstance(data, list):
                existing = data
        except Exception as exc:
            logger.warning("Could not read existing needs file %s: %s", file_path, exc)

    existing.append(need.model_dump())

    with file_path.open("w", encoding="utf-8") as fh:
        yaml.dump(existing, fh, default_flow_style=False, allow_unicode=True)

    logger.info("Need %s written to %s", need.id, file_path)
    return str(file_path)


async def write_engagement(eng: Engagement, workspace: str) -> str:
    """Write an Engagement record to needs/engagements/{id}.yaml.

    Args:
        eng: The Engagement model to persist.
        workspace: Path to the PFC workspace root.

    Returns:
        Absolute path to the written file.
    """
    engagements_dir = Path(workspace) / "needs" / "engagements"
    engagements_dir.mkdir(parents=True, exist_ok=True)
    file_path = engagements_dir / f"{eng.id}.yaml"

    with file_path.open("w", encoding="utf-8") as fh:
        yaml.dump(eng.model_dump(), fh, default_flow_style=False, allow_unicode=True)

    logger.info("Engagement %s written to %s", eng.id, file_path)
    return str(file_path)


async def write_requirement(req: Requirement, workspace: str) -> str:
    """Append a Requirement to requirements/by-domain/{domain}.yaml.

    Args:
        req: The Requirement model to persist.
        workspace: Path to the PFC workspace root.

    Returns:
        Absolute path to the file that was written/appended.
    """
    domain_dir = Path(workspace) / "requirements" / "by-domain"
    domain_dir.mkdir(parents=True, exist_ok=True)
    file_path = domain_dir / f"{req.domain}.yaml"

    existing: list[dict] = []
    if file_path.exists():
        try:
            with file_path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if isinstance(data, list):
                existing = data
        except Exception as exc:
            logger.warning("Could not read existing requirements file %s: %s", file_path, exc)

    existing.append(req.model_dump())

    with file_path.open("w", encoding="utf-8") as fh:
        yaml.dump(existing, fh, default_flow_style=False, allow_unicode=True)

    logger.info("Requirement %s written to %s", req.id, file_path)
    return str(file_path)
