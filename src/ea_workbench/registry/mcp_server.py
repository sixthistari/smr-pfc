"""Minimal stdio MCP server wrapping the element registry queries.

Run as:
    uv run python -m ea_workbench.registry.mcp_server

Or register in .chainlit/config.toml as a stdio MCP server.

All tools are read-only. Writes to the registry go through the staging
approval flow only.
"""

import json
import logging
import os
from typing import Any

from mcp.server import FastMCP

from ea_workbench.registry.db import get_connection, initialise_schema
from ea_workbench.registry.queries import (
    domain_summary,
    find_orphan_elements,
    get_element,
    list_capabilities,
    search_elements,
)

logger = logging.getLogger(__name__)

_DB_PATH = os.environ.get(
    "REGISTRY_DB_PATH",
    os.path.join(
        os.environ.get("PFC_WORKSPACE", "stanmore-pfc"),
        "elements",
        "registry.db",
    ),
)

mcp = FastMCP("element-registry")


@mcp.tool()
async def search_elements_tool(
    query: str,
    domain: str | None = None,
    archimate_type: str | None = None,
) -> str:
    """Search architectural elements by name or description.

    Args:
        query: Search term matched against name and description.
        domain: Optional domain filter (e.g. 'safety', 'knowledge-infrastructure').
        archimate_type: Optional ArchiMate type filter (e.g. 'application-component').

    Returns:
        JSON array of matching elements.
    """
    await initialise_schema(_DB_PATH)
    async with get_connection(_DB_PATH) as conn:
        elements = await search_elements(conn, query, domain=domain, archimate_type=archimate_type)
    return json.dumps([e.model_dump() for e in elements], indent=2)


@mcp.tool()
async def get_element_tool(element_id: str) -> str:
    """Get full details of an element by ID.

    Args:
        element_id: The element's primary key identifier.

    Returns:
        JSON object with element details, or error message if not found.
    """
    await initialise_schema(_DB_PATH)
    async with get_connection(_DB_PATH) as conn:
        element = await get_element(conn, element_id)
    if element is None:
        return json.dumps({"error": f"Element '{element_id}' not found"})
    return json.dumps(element.model_dump(), indent=2)


@mcp.tool()
async def list_capabilities_tool(
    parent_id: str | None = None,
    max_level: int | None = None,
) -> str:
    """List capabilities, optionally filtered by parent or depth.

    Args:
        parent_id: Optional parent capability ID (omit for root level).
        max_level: Maximum hierarchy depth to return.

    Returns:
        JSON array of capabilities.
    """
    await initialise_schema(_DB_PATH)
    async with get_connection(_DB_PATH) as conn:
        caps = await list_capabilities(conn, parent_id=parent_id, max_level=max_level)
    return json.dumps([c.model_dump() for c in caps], indent=2)


@mcp.tool()
async def find_orphan_elements_tool() -> str:
    """Find architectural elements not linked to any capability.

    Returns:
        JSON array of orphan elements.
    """
    await initialise_schema(_DB_PATH)
    async with get_connection(_DB_PATH) as conn:
        orphans = await find_orphan_elements(conn)
    return json.dumps([e.model_dump() for e in orphans], indent=2)


@mcp.tool()
async def domain_summary_tool(domain: str | None = None) -> str:
    """Get element counts grouped by domain, type, and status.

    Args:
        domain: Optional domain filter.

    Returns:
        JSON array of summary rows.
    """
    await initialise_schema(_DB_PATH)
    async with get_connection(_DB_PATH) as conn:
        summary = await domain_summary(conn, domain=domain)
    return json.dumps(summary, indent=2)


if __name__ == "__main__":
    mcp.run()
