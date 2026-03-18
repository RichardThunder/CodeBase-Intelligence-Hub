"""Simple in-memory session storage with limited history."""

from collections import deque
from threading import Lock
from typing import Optional


class SessionMemory:
    """Thread-safe session memory with circular buffer.

    Stores last N turns of conversation per session.
    """

    def __init__(self, max_history: int = 5):
        """Initialize session memory.

        Args:
            max_history: Maximum turns to keep per session (default 5)
        """
        self.max_history = max_history
        self._sessions: dict[str, deque] = {}
        self._lock = Lock()

    def get_history(self, session_id: str) -> list[dict]:
        """Get conversation history for session.

        Args:
            session_id: Session identifier

        Returns:
            List of [{"role": "user"/"assistant", "content": str}, ...]
        """
        with self._lock:
            if session_id not in self._sessions:
                return []
            return list(self._sessions[session_id])

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Add a conversation turn to session.

        Args:
            session_id: Session identifier
            role: "user" or "assistant"
            content: Message content
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = deque(maxlen=self.max_history)

            self._sessions[session_id].append({
                "role": role,
                "content": content,
            })

    def clear_session(self, session_id: str) -> None:
        """Clear history for a session.

        Args:
            session_id: Session identifier
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    def cleanup_old_sessions(self, max_sessions: int = 100) -> None:
        """Remove oldest sessions if count exceeds limit.

        Args:
            max_sessions: Maximum sessions to keep
        """
        with self._lock:
            if len(self._sessions) > max_sessions:
                # Keep the most recent sessions
                sessions_list = list(self._sessions.keys())
                for session_id in sessions_list[:-max_sessions]:
                    del self._sessions[session_id]


# Global memory instance
_memory = SessionMemory(max_history=5)


def get_session_history(session_id: str) -> list[dict]:
    """Get conversation history for session.

    Args:
        session_id: Session identifier

    Returns:
        List of conversation turns
    """
    return _memory.get_history(session_id)


def update_session_history(
    session_id: str,
    role: str,
    content: str,
) -> None:
    """Update session history with new turn.

    Args:
        session_id: Session identifier
        role: "user" or "assistant"
        content: Message content
    """
    _memory.add_turn(session_id, role, content)


def clear_session(session_id: str) -> None:
    """Clear session history.

    Args:
        session_id: Session identifier
    """
    _memory.clear_session(session_id)
