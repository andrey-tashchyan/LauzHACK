"""
Conversation session manager for multi-turn agent interactions.

Stores conversation history per session to enable:
- Follow-up questions ("show me more details")
- Context-aware responses ("what about their company?")
- Cross-agent context sharing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)  # routing info, agent used, etc.

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class ConversationSession:
    """Manages conversation history for a single session."""

    def __init__(self, session_id: str, max_history: int = 20):
        self.session_id = session_id
        self.max_history = max_history
        self.messages: List[Message] = []
        self.context: Dict = {}  # Shared context (e.g., last resolved partner_id)

    def add_message(self, role: str, content: str, **metadata) -> None:
        """Add a message to the conversation history."""
        msg = Message(role=role, content=content, metadata=metadata)
        self.messages.append(msg)

        # Keep only the last N messages to avoid context overflow
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def get_recent_messages(self, n: int = 5) -> List[Message]:
        """Get the N most recent messages."""
        return self.messages[-n:] if self.messages else []

    def get_context_for_llm(self, n: int = 5) -> List[Dict[str, str]]:
        """
        Get recent messages in LLM-compatible format.
        Returns list of {"role": "user/assistant", "content": "..."}
        """
        recent = self.get_recent_messages(n)
        return [{"role": msg.role, "content": msg.content} for msg in recent]

    def set_context(self, key: str, value: any) -> None:
        """Store context that persists across turns (e.g., last partner_id)."""
        self.context[key] = value

    def get_context(self, key: str, default=None) -> any:
        """Retrieve stored context."""
        return self.context.get(key, default)

    def clear(self) -> None:
        """Clear the conversation history."""
        self.messages.clear()
        self.context.clear()

    def to_dict(self) -> Dict:
        """Serialize the session for storage."""
        return {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "context": self.context,
        }


class SessionManager:
    """
    Global session manager for all conversations.

    In-memory storage with optional Redis backend for production.
    """

    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}

    def get_session(self, session_id: str) -> ConversationSession:
        """Get or create a conversation session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(session_id)
        return self._sessions[session_id]

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def clear_all(self) -> None:
        """Clear all sessions (useful for testing)."""
        self._sessions.clear()


# Global instance
_global_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    return _global_session_manager
