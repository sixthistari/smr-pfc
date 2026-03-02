"""Context bootstrap handlers for pre-loading conversation context.

Supports DevOps work item context pre-loading when the chat is opened
with query parameters such as ?init=devops-item&id=NNN.

Chainlit passes URL query parameters to user_session if configured.
Expected query param names:
  - ``chainlit_init_type``: The bootstrap type (e.g. "devops-item")
  - ``chainlit_init_id``: The item ID to pre-load (e.g. "1234")

These are set via Chainlit's custom_js or by configuring the Chainlit
embedding to pass URL params into the session store.
"""

import logging

logger = logging.getLogger(__name__)


async def bootstrap_from_devops(item_id: str) -> dict:
    """Build pre-load context for an Azure DevOps work item.

    This is a stub implementation. When the ADO MCP server is connected,
    this function will fetch the full work item details (title, description,
    acceptance criteria, linked specs) and return them as context.

    Args:
        item_id: The ADO work item ID (numeric string).

    Returns:
        Context dict with keys:
          - intent: Short description of the session intent
          - context_message: Human-readable message to display at session start
          - item_id: The work item ID
    """
    logger.info("Bootstrapping session context for DevOps item #%s", item_id)

    return {
        "intent": f"devops-item:{item_id}",
        "context_message": (
            f"Session opened for DevOps item **#{item_id}**.\n\n"
            "I'll help you explore the architecture context for this work item. "
            "Once the ADO MCP server is connected, I can fetch the full item details, "
            "linked specs, and relevant capabilities automatically.\n\n"
            f"_Work item ID: {item_id} — context pre-loaded._"
        ),
        "item_id": item_id,
    }
