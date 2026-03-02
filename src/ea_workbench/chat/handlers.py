"""MCP connection and tool call handlers for the EA Workbench chat."""

import logging

import chainlit as cl

logger = logging.getLogger(__name__)

# Tools that write to wiki or repo — require human confirmation before execution
_WIKI_WRITE_TOOLS = {
    "wiki_create_page",
    "wiki_update_page",
    "wiki_delete_page",
    "create_page",
    "update_page",
    "delete_page",
}


async def on_mcp_connect(connection: object, session_name: str) -> None:  # type: ignore[type-arg]
    """Handle MCP server connection event.

    Args:
        connection: The MCP connection object provided by Chainlit.
        session_name: Name of the MCP session (e.g. 'ado-wiki', 'element-registry').
    """
    logger.info("MCP connected: %s", session_name)
    await cl.Message(content=f"🔌 MCP connected: **{session_name}**").send()


async def process_tool_call(tool_name: str, tool_input: dict[str, object]) -> str:
    """Dispatch a tool call to the appropriate handler.

    Wiki write operations are intercepted and require user confirmation
    before proceeding.

    Args:
        tool_name: The MCP tool name to invoke.
        tool_input: The input parameters for the tool.

    Returns:
        The tool result as a string.
    """
    if _is_wiki_write(tool_name):
        return await _handle_wiki_write(tool_name, tool_input)

    # Stub: ADO MCP not connected
    logger.debug("Tool call stub: %s(%s)", tool_name, tool_input)
    return (
        f"Tool '{tool_name}' is not available — ADO MCP not configured in this session. "
        "Wiki and work-item operations require ADO MCP connection."
    )


def _is_wiki_write(tool_name: str) -> bool:
    """Return True if the tool name is a wiki write operation."""
    lower = tool_name.lower()
    return any(write_tool in lower for write_tool in _WIKI_WRITE_TOOLS)


async def _handle_wiki_write(tool_name: str, tool_input: dict[str, object]) -> str:
    """Intercept a wiki write call and require user confirmation.

    Presents the proposed content in a Chainlit step for review.
    Only proceeds after explicit user confirmation.

    Args:
        tool_name: The wiki write tool name.
        tool_input: The tool input containing proposed content.

    Returns:
        Result string — either confirmation of write or cancellation notice.
    """
    proposed_content = tool_input.get("content", tool_input.get("body", ""))
    page_path = tool_input.get("path", tool_input.get("title", "unknown page"))

    async with cl.Step(name="Wiki Write Review", show_input=True) as step:
        step.input = f"**Tool**: {tool_name}\n**Page**: {page_path}"
        step.output = present_wiki_diff(
            current="",  # No existing content in stub
            proposed=str(proposed_content),
        )

    # In stub mode, ADO MCP is not connected — always deny
    await cl.Message(
        content=(
            f"⚠️ **Wiki Write Blocked**: ADO MCP is not configured in this session.\n\n"
            f"Proposed write to `{page_path}` has been logged above for review. "
            "Connect ADO MCP to enable wiki writes."
        )
    ).send()

    return f"Wiki write to '{page_path}' blocked — ADO MCP not configured."


def present_wiki_diff(current: str, proposed: str) -> str:
    """Format a before/after diff for wiki content review.

    Args:
        current: The current page content (empty string for new pages).
        proposed: The proposed new or replacement content.

    Returns:
        Formatted markdown string showing the change.
    """
    if not current:
        return f"**New page — proposed content:**\n\n```markdown\n{proposed}\n```"

    return (
        f"**Current content:**\n\n```markdown\n{current}\n```\n\n"
        f"**Proposed content:**\n\n```markdown\n{proposed}\n```"
    )
