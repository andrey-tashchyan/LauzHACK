import chainlit as cl
import asyncio
import json
import os


@cl.on_chat_start
async def on_chat_start():
    """
    Called when a new chat session starts.
    """
    # The UBS logo will be injected into the header via custom CSS and JavaScript
    # from public/ubs-theme.css and public/ubs-custom.js

    await cl.Message(
        content="Welcome to UBS-X-LauzHack Financial Intelligence Assistant. How may I assist you today?"
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
    Called when a user sends a message.
    """
    # Simulate latency for reasoning
    await asyncio.sleep(1)

    # Echo the message back for now (placeholder)
    response = f"You said: {message.content}"

    # Create an action button for visualizing transactions
    actions = [
        cl.Action(
            name="visualize_transactions",
            value="show",
            label="Visualize Transactions",
            description="View transaction graph visualization",
            payload={}
        )
    ]

    await cl.Message(
        content=response,
        actions=actions
    ).send()


@cl.on_chat_end
async def on_chat_end():
    """
    Called when a chat session ends.
    """
    pass
