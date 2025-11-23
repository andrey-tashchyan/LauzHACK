import asyncio
import sys
from pathlib import Path

import chainlit as cl

# Ensure the repo root is importable so we can access the router module.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from agent_router import AgentRouter  # noqa: E402

router = AgentRouter()


@cl.on_chat_start
async def on_chat_start():
    """Called when a new chat session starts."""
    await cl.Message(
        content=(
            "Welcome to UBS-X-LauzHack Financial Intelligence Assistant.\n"
            "I will route your request to the best agent (suspicious activity, company info, or account activity)."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Route incoming user messages to the right specialist agent."""
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None, router.route_and_execute, message.content
    )
    await cl.Message(content=response).send()


@cl.on_chat_end
async def on_chat_end():
    """Called when a chat session ends."""
    pass
