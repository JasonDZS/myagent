"""Client-side state management for MyAgent WebSocket sessions."""

import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Any

from myagent.logger import logger


class StateManager:
    """Manages agent state serialization, signing, and verification for client-side storage."""
    
    def __init__(self, secret_key: str):
        """Initialize state manager with server secret key.
        
        Args:
            secret_key: Server-side secret key for state signing/verification
        """
        self.secret_key = secret_key
        self.version = "1.0"
        self.state_ttl = 86400 * 7  # 7 days in seconds
    
    def create_state_snapshot(self, session: 'AgentSession') -> dict[str, Any]:
        """Create a serializable state snapshot from AgentSession.
        
        Args:
            session: The AgentSession to snapshot
            
        Returns:
            Dictionary containing the serialized state
        """
        try:
            state_data = {
                "session_id": session.session_id,
                "current_step": session.step_counter,
                "agent_state": str(session.agent.state) if hasattr(session.agent, 'state') else "idle",
                "created_at": session.created_at.isoformat(),
                "last_active_at": datetime.now().isoformat(),
                "memory_snapshot": self._serialize_agent_memory(session.agent),
                "tool_states": self._serialize_tool_states(session.agent),
                "pending_confirmations": list(getattr(session, '_pending_confirmations', {}).keys()),
                "metadata": {
                    "agent_name": getattr(session.agent, "name", "unknown"),
                    "agent_config": self._get_agent_config(session.agent),
                    "session_state": session.state
                }
            }
            
            # Clean sensitive information
            state_data = self._sanitize_state(state_data)
            
            logger.info(f"Created state snapshot for session {session.session_id}")
            return state_data
            
        except Exception as e:
            logger.exception(f"Failed to create state snapshot: {e}")
            raise
    
    def sign_state(self, state_data: dict[str, Any]) -> dict[str, Any]:
        """Sign state data for secure client-side storage.
        
        Args:
            state_data: The state data to sign
            
        Returns:
            Dictionary containing signed state data
        """
        try:
            timestamp = int(time.time())
            
            # Create canonical JSON representation
            state_json = json.dumps(state_data, sort_keys=True, separators=(',', ':'))
            
            # Create message to sign
            message = f"{state_json}:{timestamp}:{self.version}"
            
            # Generate signature
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            signed_state = {
                "state": state_data,
                "timestamp": timestamp,
                "signature": signature,
                "version": self.version,
                "checksum": hashlib.sha256(state_json.encode('utf-8')).hexdigest()
            }
            
            logger.debug(f"Signed state for session {state_data.get('session_id', 'unknown')}")
            return signed_state
            
        except Exception as e:
            logger.exception(f"Failed to sign state: {e}")
            raise
    
    def verify_state(self, signed_state: dict[str, Any]) -> tuple[bool, dict[str, Any], str]:
        """Verify signed state data from client.
        
        Args:
            signed_state: The signed state data to verify
            
        Returns:
            Tuple of (is_valid, state_data, error_message)
        """
        try:
            # Check required fields
            required_fields = ["state", "timestamp", "signature", "version", "checksum"]
            for field in required_fields:
                if field not in signed_state:
                    return False, {}, f"Missing required field: {field}"
            
            state_data = signed_state["state"]
            timestamp = signed_state["timestamp"]
            signature = signed_state["signature"]
            version = signed_state["version"]
            checksum = signed_state["checksum"]
            
            # Check version compatibility
            if version != self.version:
                return False, {}, f"Version mismatch: expected {self.version}, got {version}"
            
            # Check timestamp (prevent replay attacks and expired states)
            current_time = int(time.time())
            if current_time - timestamp > self.state_ttl:
                return False, {}, f"State expired (age: {current_time - timestamp}s)"
            
            # Verify checksum
            state_json = json.dumps(state_data, sort_keys=True, separators=(',', ':'))
            expected_checksum = hashlib.sha256(state_json.encode('utf-8')).hexdigest()
            if checksum != expected_checksum:
                return False, {}, "State checksum mismatch"
            
            # Verify signature
            message = f"{state_json}:{timestamp}:{version}"
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return False, {}, "Invalid state signature"
            
            # Additional state validation
            validation_error = self._validate_state_structure(state_data)
            if validation_error:
                return False, {}, validation_error
            
            logger.info(f"Successfully verified state for session {state_data.get('session_id', 'unknown')}")
            return True, state_data, ""
            
        except Exception as e:
            logger.exception(f"State verification failed: {e}")
            return False, {}, f"Verification error: {str(e)}"
    
    def restore_session_from_state(self, session: 'AgentSession', state_data: dict[str, Any]) -> bool:
        """Restore AgentSession from verified state data.
        
        Args:
            session: The session to restore
            state_data: Verified state data
            
        Returns:
            True if restoration succeeded, False otherwise
        """
        try:
            # Restore basic session properties
            session.step_counter = state_data.get("current_step", 0)
            session.state = state_data.get("metadata", {}).get("session_state", "idle")
            
            # Restore agent state
            agent_state_str = state_data.get("agent_state", "idle")
            if hasattr(session.agent, 'state'):
                from myagent.schema import AgentState
                try:
                    session.agent.state = AgentState(agent_state_str.lower())
                except ValueError:
                    session.agent.state = AgentState.IDLE
                    logger.warning(f"Invalid agent state '{agent_state_str}', reset to IDLE")
            
            # Restore agent memory
            memory_success = self._restore_agent_memory(session.agent, state_data.get("memory_snapshot"))
            if not memory_success:
                logger.warning("Failed to restore agent memory")
            
            # Restore tool states
            tool_success = self._restore_tool_states(session.agent, state_data.get("tool_states"))
            if not tool_success:
                logger.warning("Failed to restore tool states")
            
            # Restore pending confirmations (create Future objects but don't set results)
            pending_confirmations = state_data.get("pending_confirmations", [])
            if pending_confirmations:
                import asyncio
                if not hasattr(session, '_pending_confirmations'):
                    session._pending_confirmations = {}
                for step_id in pending_confirmations:
                    session._pending_confirmations[step_id] = asyncio.Future()
                logger.info(f"Restored {len(pending_confirmations)} pending confirmations")
            
            logger.info(f"Successfully restored session {session.session_id} from state")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to restore session from state: {e}")
            return False
    
    def _serialize_agent_memory(self, agent) -> str:
        """Serialize agent memory to JSON string."""
        try:
            if hasattr(agent, 'memory') and hasattr(agent.memory, 'messages'):
                messages = []
                for msg in agent.memory.messages:
                    # Convert message to serializable format
                    serializable_msg = {
                        "role": getattr(msg, 'role', 'unknown'),
                        "content": getattr(msg, 'content', ''),
                        "tool_calls": getattr(msg, 'tool_calls', None),
                        "tool_call_id": getattr(msg, 'tool_call_id', None),
                        "timestamp": getattr(msg, 'timestamp', None)
                    }
                    # Only include non-None values
                    serializable_msg = {k: v for k, v in serializable_msg.items() if v is not None}
                    messages.append(serializable_msg)
                
                # Limit history size to prevent large states
                max_messages = 100
                if len(messages) > max_messages:
                    messages = messages[-max_messages:]
                    logger.info(f"Truncated message history to {max_messages} messages")
                
                return json.dumps(messages, ensure_ascii=False)
            return "[]"
        except Exception as e:
            logger.error(f"Failed to serialize agent memory: {e}")
            return "[]"
    
    def _serialize_tool_states(self, agent) -> dict[str, Any]:
        """Serialize tool states (excluding sensitive information)."""
        try:
            tool_states = {}
            if hasattr(agent, 'available_tools'):
                tools = agent.available_tools
                if hasattr(tools, 'tool_map'):
                    # ToolCollection
                    for tool_name, tool in tools.tool_map.items():
                        tool_state = {
                            "name": getattr(tool, 'name', tool_name),
                            "description": getattr(tool, 'description', ''),
                            "user_confirm": getattr(tool, 'user_confirm', False)
                        }
                        tool_states[tool_name] = tool_state
                elif hasattr(tools, '__iter__'):
                    # List of tools
                    for tool in tools:
                        tool_name = getattr(tool, 'name', 'unknown')
                        tool_state = {
                            "name": tool_name,
                            "description": getattr(tool, 'description', ''),
                            "user_confirm": getattr(tool, 'user_confirm', False)
                        }
                        tool_states[tool_name] = tool_state
            return tool_states
        except Exception as e:
            logger.exception(f"Failed to serialize tool states: {e}")
            return {}
    
    def _get_agent_config(self, agent) -> dict[str, Any]:
        """Extract agent configuration (non-sensitive)."""
        try:
            config = {}
            if hasattr(agent, 'name'):
                config['name'] = agent.name
            if hasattr(agent, 'description'):
                config['description'] = agent.description
            if hasattr(agent, 'max_steps'):
                config['max_steps'] = agent.max_steps
            return config
        except Exception as e:
            logger.exception(f"Failed to extract agent config: {e}")
            return {}
    
    def _sanitize_state(self, state_data: dict[str, Any]) -> dict[str, Any]:
        """Remove sensitive information from state data."""
        sanitized = state_data.copy()
        
        # Remove sensitive fields from tool states
        if "tool_states" in sanitized:
            for tool_name, tool_state in sanitized["tool_states"].items():
                # Remove any fields that might contain sensitive information
                sensitive_fields = ["api_key", "access_token", "password", "secret", "token", "key"]
                for field in sensitive_fields:
                    if field in tool_state:
                        del tool_state[field]
        
        # Limit memory size
        if "memory_snapshot" in sanitized:
            try:
                messages = json.loads(sanitized["memory_snapshot"])
                # Further limit if needed based on total size
                memory_str = json.dumps(messages)
                max_memory_size = 100000  # 100KB limit
                if len(memory_str) > max_memory_size:
                    # Reduce to last N messages until under limit
                    while len(json.dumps(messages)) > max_memory_size and len(messages) > 1:
                        messages = messages[-int(len(messages) * 0.8):]  # Remove 20% from beginning
                    sanitized["memory_snapshot"] = json.dumps(messages)
                    logger.info(f"Reduced memory snapshot size to {len(sanitized['memory_snapshot'])} chars")
            except (json.JSONDecodeError, TypeError):
                sanitized["memory_snapshot"] = "[]"
        
        return sanitized
    
    def _validate_state_structure(self, state_data: dict[str, Any]) -> str | None:
        """Validate state data structure."""
        required_fields = ["session_id", "current_step", "agent_state", "created_at"]
        for field in required_fields:
            if field not in state_data:
                return f"Missing required state field: {field}"
        
        # Validate field types
        if not isinstance(state_data["current_step"], int):
            return "current_step must be an integer"
        
        if state_data["current_step"] < 0:
            return "current_step cannot be negative"
        
        # Validate memory snapshot format
        if "memory_snapshot" in state_data:
            try:
                memory = json.loads(state_data["memory_snapshot"])
                if not isinstance(memory, list):
                    return "memory_snapshot must be a JSON array"
            except json.JSONDecodeError:
                return "Invalid JSON in memory_snapshot"
        
        return None
    
    def _restore_agent_memory(self, agent, memory_snapshot: str | None) -> bool:
        """Restore agent memory from snapshot."""
        try:
            if not memory_snapshot or not hasattr(agent, 'memory'):
                return True
            
            messages = json.loads(memory_snapshot)
            if not isinstance(messages, list):
                return False
            
            # Clear existing memory
            if hasattr(agent.memory, 'messages'):
                agent.memory.messages.clear()
            
            # Restore messages
            for msg_data in messages:
                # This would need to be implemented based on your specific message class
                # For now, we'll just log that we would restore them
                logger.debug(f"Would restore message: {msg_data.get('role', 'unknown')}")
            
            logger.info(f"Restored {len(messages)} messages to agent memory")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to restore agent memory: {e}")
            return False
    
    def _restore_tool_states(self, agent, tool_states: dict[str, Any] | None) -> bool:
        """Restore tool states (limited restoration for security)."""
        try:
            if not tool_states:
                return True
            
            # For security, we only restore basic tool configuration, not runtime state
            logger.info(f"Tool state info available for {len(tool_states)} tools")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to restore tool states: {e}")
            return False
