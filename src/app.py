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
from utils.session_manager import get_session_manager  # noqa: E402

router = AgentRouter()
session_manager = get_session_manager()


@cl.on_chat_start
async def on_chat_start():
    """Called when a new chat session starts."""
    # The UBS logo will be injected into the header via custom CSS and JavaScript
    # from public/ubs-theme.css and public/ubs-custom.js

    # Initialize conversation session for this user
    session_id = cl.user_session.get("id")
    if not session_id:
        # Generate a unique session ID if not present
        import uuid
        session_id = str(uuid.uuid4())
        cl.user_session.set("id", session_id)

    # Get or create conversation session
    conversation_session = session_manager.get_session(session_id)
    cl.user_session.set("conversation_session", conversation_session)

    # Welcome message
    await cl.Message(
        content="Welcome to the UBS AML Intelligence System! Ask me about companies, accounts, or suspicious activities."
    ).send()


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
    """
    Route incoming user messages to the right specialist agent with streaming.
    """
    # Get the conversation session
    conversation_session = cl.user_session.get("conversation_session")

    # Create a message object to stream tokens into
    msg = cl.Message(content="")
    await msg.send()

    # Stream the response
    loop = asyncio.get_running_loop()
    full_response = ""

    try:
        # Run the streaming generator in the executor
        async def stream_response():
            nonlocal full_response
            # Execute in thread pool to avoid blocking
            for chunk in await loop.run_in_executor(
                None,
                lambda: list(router.route_and_execute_stream(
                    message.content,
                    session=conversation_session
                ))
            ):
                full_response += chunk
                await msg.stream_token(chunk)

        await stream_response()

    except Exception as e:
        error_msg = f"\n\n[Error] {str(e)}"
        full_response += error_msg
        await msg.stream_token(error_msg)

    # Update the message with the complete content
    msg.content = full_response
    await msg.update()


@cl.on_chat_end
async def on_chat_end():
    """
    Called when a chat session ends. Clean up the session.
    """
    session_id = cl.user_session.get("id")
    if session_id:
        # Optional: delete session to free memory
        # Uncomment if you want to clear sessions on chat end
        # session_manager.delete_session(session_id)
        pass
