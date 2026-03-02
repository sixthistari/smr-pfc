"""Agent protocol definition and manifest writing utilities."""

import json
import logging
import os
from typing import Protocol, runtime_checkable

from ea_workbench.models.config import AgentConfig
from ea_workbench.models.manifests import RunManifest

logger = logging.getLogger(__name__)


@runtime_checkable
class AgentProtocol(Protocol):
    """Structural protocol that all batch agent modules must satisfy."""

    async def run(
        self,
        config: AgentConfig,
        prompt: str,
        workspace: str,
    ) -> RunManifest:
        """Execute the agent and return a run manifest.

        Args:
            config: The agent's configuration from config.yaml.
            prompt: The user prompt or input path to process.
            workspace: Path to the PFC workspace root.

        Returns:
            A completed RunManifest describing the run.
        """
        ...


def write_manifest(manifest: RunManifest, runs_dir: str) -> str:
    """Serialise a RunManifest to JSON and write it to the runs directory.

    Args:
        manifest: The run manifest to persist.
        runs_dir: Path to the .agents/runs/ directory.

    Returns:
        Path to the written manifest file.
    """
    os.makedirs(runs_dir, exist_ok=True)
    filename = f"{manifest.agent_id}_{manifest.run_id}.json"
    filepath = os.path.join(runs_dir, filename)
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(manifest.model_dump(), fh, indent=2)
    logger.info("Manifest written: %s", filepath)
    return filepath
