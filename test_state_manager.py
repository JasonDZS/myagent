#!/usr/bin/env python3
"""
Simple test for StateManager functionality.

This test verifies the core state management features:
- State signing and verification
- State serialization and sanitization
- Error handling and validation
"""

import json
import time
from datetime import datetime
from unittest.mock import Mock

from myagent.ws.state_manager import StateManager


def test_state_signing_and_verification():
    """Test state signing and verification."""
    print("🧪 Testing state signing and verification...")
    
    # Create state manager
    secret_key = "test-secret-key-for-testing-only"
    state_manager = StateManager(secret_key)
    
    # Create test state data
    test_state = {
        "session_id": "test-session-123",
        "current_step": 5,
        "agent_state": "idle",
        "created_at": datetime.now().isoformat(),
        "memory_snapshot": json.dumps([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]),
        "tool_states": {"weather_tool": {"name": "weather_tool"}},
        "metadata": {"agent_name": "TestAgent"}
    }
    
    # Sign the state
    signed_state = state_manager.sign_state(test_state)
    
    # Verify required fields are present
    assert "state" in signed_state
    assert "timestamp" in signed_state
    assert "signature" in signed_state
    assert "version" in signed_state
    assert "checksum" in signed_state
    
    print("✅ State signing successful")
    
    # Verify the state
    is_valid, recovered_state, error_msg = state_manager.verify_state(signed_state)
    
    assert is_valid, f"State verification failed: {error_msg}"
    assert recovered_state == test_state
    assert error_msg == ""
    
    print("✅ State verification successful")
    
    # Test invalid signature
    tampered_state = signed_state.copy()
    tampered_state["signature"] = "invalid-signature"
    
    is_valid, _, error_msg = state_manager.verify_state(tampered_state)
    assert not is_valid
    assert "signature" in error_msg.lower()
    
    print("✅ Invalid signature detection successful")
    
    # Test expired state
    old_state = signed_state.copy()
    old_state["timestamp"] = int(time.time()) - 86400 * 8  # 8 days ago
    
    is_valid, _, error_msg = state_manager.verify_state(old_state)
    assert not is_valid
    assert "expired" in error_msg.lower()
    
    print("✅ Expired state detection successful")


def test_state_sanitization():
    """Test state data sanitization."""
    print("\n🧪 Testing state sanitization...")
    
    state_manager = StateManager("test-key")
    
    # Create state with sensitive data
    test_state = {
        "session_id": "test-session",
        "current_step": 1,
        "agent_state": "idle",
        "created_at": datetime.now().isoformat(),
        "memory_snapshot": json.dumps([{"role": "user", "content": "test"}]),
        "tool_states": {
            "api_tool": {
                "name": "api_tool",
                "api_key": "secret-key-123",
                "access_token": "token-456",
                "password": "secret-password"
            }
        }
    }
    
    # Sanitize the state
    sanitized = state_manager._sanitize_state(test_state)
    
    # Check that sensitive fields are removed
    api_tool_state = sanitized["tool_states"]["api_tool"]
    assert "api_key" not in api_tool_state
    assert "access_token" not in api_tool_state
    assert "password" not in api_tool_state
    assert api_tool_state["name"] == "api_tool"  # Non-sensitive data preserved
    
    print("✅ Sensitive data removal successful")


def test_mock_session_restoration():
    """Test session restoration with mock objects."""
    print("\n🧪 Testing session restoration...")
    
    state_manager = StateManager("test-key")
    
    # Create mock session and agent
    mock_session = Mock()
    mock_session.session_id = "new-session-123"
    mock_session.step_counter = 0
    mock_session.state = "idle"
    
    mock_agent = Mock()
    mock_agent.state = Mock()
    mock_session.agent = mock_agent
    
    # Test state data
    state_data = {
        "session_id": "original-session-456",
        "current_step": 3,
        "agent_state": "idle",
        "created_at": datetime.now().isoformat(),
        "memory_snapshot": "[]",
        "tool_states": {},
        "pending_confirmations": [],
        "metadata": {"session_state": "idle"}
    }
    
    # Restore session from state
    success = state_manager.restore_session_from_state(mock_session, state_data)
    
    # Verify restoration
    assert success
    assert mock_session.step_counter == 3
    assert mock_session.state == "idle"
    
    print("✅ Session restoration successful")


def test_validation():
    """Test state validation."""
    print("\n🧪 Testing state validation...")
    
    state_manager = StateManager("test-key")
    
    # Test missing required fields
    invalid_state = {
        "session_id": "test",
        # missing current_step, agent_state, created_at
    }
    
    error = state_manager._validate_state_structure(invalid_state)
    assert error is not None
    assert "required" in error.lower()
    
    print("✅ Missing field validation successful")
    
    # Test invalid field types
    invalid_state = {
        "session_id": "test",
        "current_step": "not-a-number",  # Should be int
        "agent_state": "idle",
        "created_at": datetime.now().isoformat()
    }
    
    error = state_manager._validate_state_structure(invalid_state)
    assert error is not None
    assert "integer" in error.lower()
    
    print("✅ Type validation successful")
    
    # Test valid state
    valid_state = {
        "session_id": "test",
        "current_step": 5,
        "agent_state": "idle",
        "created_at": datetime.now().isoformat(),
        "memory_snapshot": "[]"
    }
    
    error = state_manager._validate_state_structure(valid_state)
    assert error is None
    
    print("✅ Valid state validation successful")


def main():
    """Run all tests."""
    print("🚀 Starting StateManager tests")
    print("=" * 50)
    
    try:
        test_state_signing_and_verification()
        test_state_sanitization()
        test_mock_session_restoration()
        test_validation()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed!")
        print("✅ State signing and verification working")
        print("✅ State sanitization working")
        print("✅ Session restoration working")
        print("✅ State validation working")
        print("\n🔧 Ready for integration testing with:")
        print("   python examples/state_test_server.py")
        print("   python examples/client_state_demo.py")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())