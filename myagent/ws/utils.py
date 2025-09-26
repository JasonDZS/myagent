"""WebSocket utility functions for cross-version compatibility."""

import json
from typing import Any, Dict, Optional
from websockets.server import WebSocketServerProtocol
from ..logger import logger


def is_websocket_closed(websocket: WebSocketServerProtocol) -> bool:
    """Check if a WebSocket connection is closed in a version-compatible way.
    
    This function handles the differences between websockets library versions:
    - Older versions use the 'closed' property
    - Newer versions use 'close_code' property
    
    Args:
        websocket: The WebSocket connection to check
        
    Returns:
        True if the connection is closed, False otherwise
    """
    # For older versions of websockets library
    if hasattr(websocket, 'closed'):
        return websocket.closed
    
    # For newer versions of websockets library
    return getattr(websocket, 'close_code', None) is not None


async def send_websocket_message(
    websocket: WebSocketServerProtocol, 
    message: Dict[str, Any]
) -> bool:
    """Send a message via WebSocket with error handling.
    
    Args:
        websocket: The WebSocket connection
        message: The message to send (will be JSON-encoded)
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    try:
        if not is_websocket_closed(websocket):
            await websocket.send(json.dumps(message))
            return True
        else:
            logger.debug("WebSocket connection is closed, cannot send message")
            return False
    except Exception as e:
        logger.error(f"Failed to send WebSocket message: {e}")
        return False


async def close_websocket_safely(websocket: WebSocketServerProtocol) -> None:
    """Close a WebSocket connection safely with error handling.
    
    Args:
        websocket: The WebSocket connection to close
    """
    try:
        if not is_websocket_closed(websocket):
            await websocket.close()
    except Exception as e:
        logger.debug(f"Error closing websocket: {e}")


def get_websocket_info(websocket: WebSocketServerProtocol) -> Dict[str, Any]:
    """Get information about a WebSocket connection for debugging.
    
    Args:
        websocket: The WebSocket connection
        
    Returns:
        Dictionary with connection information
    """
    info = {
        "closed": is_websocket_closed(websocket),
        "remote_address": getattr(websocket, 'remote_address', None),
    }
    
    # Add version-specific information
    if hasattr(websocket, 'close_code'):
        info["close_code"] = websocket.close_code
    if hasattr(websocket, 'close_reason'):
        info["close_reason"] = websocket.close_reason
    if hasattr(websocket, 'state'):
        info["state"] = str(websocket.state)
        
    return info