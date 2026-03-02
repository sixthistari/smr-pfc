"""Chainlit chat application entry point for the EA Workbench."""

import logging
import os
from pathlib import Path

import chainlit as cl
from anthropic import AsyncAnthropic

from ea_workbench.utils.yaml_loader import load_capability_summary, load_glossary_summary

logger = logging.getLogger(__name__)

# Resolve workspace root from environment or relative to this file
_WORKSPACE = os.environ.get(
    "PFC_WORKSPACE",
    str(Path(__file__).parent.parent.parent.parent / "stanmore-pfc"),
)
_PROMPT_PATH = os.path.join(_WORKSPACE, ".agents", "prompts", "chat-agent.md")
_CAPABILITIES_PATH = os.path.join(_WORKSPACE, "capabilities", "capability-model.yaml")
_GLOSSARY_PATH = os.path.join(_WORKSPACE, "vocabulary", "enterprise-glossary.yaml")
_DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "claude-sonnet-4-6")


def _make_client() -> AsyncAnthropic:
    """Build the Anthropic client, routing to Azure AI Foundry if configured."""
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if azure_endpoint:
        return AsyncAnthropic(base_url=azure_endpoint, api_key=api_key)
    return AsyncAnthropic(api_key=api_key)


def _load_system_prompt() -> str:
    """Load and populate the system prompt template with live context.

    Returns:
        Fully populated system prompt string.
    """
    try:
        template = Path(_PROMPT_PATH).read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("System prompt not found at %s", _PROMPT_PATH)
        template = "You are the Stanmore PFC assistant."

    capabilities = load_capability_summary(_CAPABILITIES_PATH, max_depth=2)
    glossary = load_glossary_summary(_GLOSSARY_PATH, max_terms=50)

    system_prompt = template.replace("{{CAPABILITY_MODEL_SUMMARY}}", capabilities)
    system_prompt = system_prompt.replace("{{GLOSSARY_SUMMARY}}", glossary)
    system_prompt = system_prompt.replace(
        "{{WIKI_TREE_SUMMARY}}", "_Wiki not connected (ADO MCP not configured)._"
    )
    return system_prompt


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialise a new chat session with system prompt and empty history."""
    system_prompt = _load_system_prompt()
    cl.user_session.set("system_prompt", system_prompt)
    cl.user_session.set("message_history", [])
    cl.user_session.set("client", _make_client())

    logger.info("New chat session started; system prompt loaded (%d chars)", len(system_prompt))
    await cl.Message(
        content=(
            "**Stanmore PFC** ready. Wiki and element registry tools will appear "
            "here when MCP servers are connected.\n\n"
            "Type a message to start, or `/help` for slash commands."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle an incoming user message, dispatch slash commands, or call the LLM."""
    content = message.content.strip()

    # Dispatch slash commands
    if content.startswith("/"):
        from ea_workbench.chat.commands import handle_command

        await handle_command(content, _WORKSPACE)
        return

    # Standard LLM conversation
    history: list[dict[str, str]] = cl.user_session.get("message_history", [])
    history.append({"role": "user", "content": content})

    system_prompt: str = cl.user_session.get("system_prompt", "")
    client: AsyncAnthropic = cl.user_session.get("client")

    response_msg = cl.Message(content="")
    await response_msg.send()

    full_response = ""
    try:
        async with client.messages.stream(
            model=_DEFAULT_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=history,  # type: ignore[arg-type]
        ) as stream:
            async for text in stream.text_stream:
                full_response += text
                await response_msg.stream_token(text)
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        await response_msg.update()
        error_msg = cl.Message(content=f"⚠️ LLM error: {exc}")
        await error_msg.send()
        return

    history.append({"role": "assistant", "content": full_response})
    cl.user_session.set("message_history", history)
    await response_msg.update()
