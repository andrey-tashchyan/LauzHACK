import chainlit as cl
import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in project root
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Ensure the repo root is importable so we can access the router module.
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from agent_router import AgentRouter  # noqa: E402

router = AgentRouter()


@cl.on_chat_start
async def on_chat_start():
    """Called when a new chat session starts."""
    # The UBS logo will be injected into the header via custom CSS and JavaScript
    # from public/ubs-theme.css and public/ubs-custom.js
    pass


def load_transactions():
    """Load transactions from the JSON file"""
    try:
        # Get the path to transactions_complete.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'transactions_complete.json')

        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading transactions: {e}")
        return []


@cl.action_callback("visualize_transactions")
async def on_action(action: cl.Action):
    """Handle the visualize transactions action"""
    # Load the transactions data
    transactions = load_transactions()

    # Debug logging
    print(f"Loaded {len(transactions)} transactions")

    # Create custom element
    viz = cl.CustomElement(
        name="TransactionGraph",
        props={"transactions": transactions}
    )

    await cl.Message(
        content=f"Transaction Visualization ({len(transactions)} transactions)",
        elements=[viz]
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
    """
    Called when a chat session ends.
    """
    pass
