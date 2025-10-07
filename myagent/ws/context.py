"""WebSocket session context management.

This module provides context variable management for WebSocket sessions,
allowing agents to access the current WebSocket session for real-time
event streaming without coupling to the trace system.
"""

import contextvars
from typing import Any

# Context variable for WebSocket session
_current_ws_session: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "current_ws_session", default=None
)


def set_ws_session_context(ws_session: Any) -> None:
    """Set WebSocket session in current context.

    Args:
        ws_session: WebSocket session object for streaming support
    """
    _current_ws_session.set(ws_session)


def get_ws_session_context() -> Any | None:
    """Get WebSocket session from current context.

    Returns:
        WebSocket session object or None if not set
    """
    return _current_ws_session.get()


def clear_ws_session_context() -> None:
    """Clear WebSocket session from current context."""
    try:
        _current_ws_session.set(None)
    except LookupError:
        # Context variable not set, ignore
        pass
