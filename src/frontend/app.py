import chainlit as cl
import asyncio


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


@cl.on_message
async def on_message(message: cl.Message):
    """
    Called when a user sends a message.
    """
    # Simulate latency for reasoning
    await asyncio.sleep(1)

    # Echo the message back for now (placeholder)
    response = f"You said: {message.content}"

    await cl.Message(
        content=response
    ).send()


@cl.on_chat_end
async def on_chat_end():
    """
    Called when a chat session ends.
    """
    pass
