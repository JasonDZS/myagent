#!/usr/bin/env python3
"""
Test server for demonstrating client-side state management.

This creates a simple WebSocket server with a mock agent for testing
the client state management functionality.

Usage:
    python examples/state_test_server.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from myagent.agent.factory import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult
from myagent.ws.server import AgentWebSocketServer
from myagent.logger import logger
from myagent.llm import LLM
from myagent.config import LLMSettings


class MockWeatherTool(BaseTool):
    """Mock weather tool for testing."""
    
    name: str = "get_weather"
    description: str = "Get current weather information for a location"
    
    async def execute(self, location: str = "San Francisco") -> ToolResult:
        """Mock weather data."""
        weather_data = {
            "location": location,
            "temperature": "22°C",
            "condition": "Sunny",
            "humidity": "60%",
            "wind": "Light breeze"
        }
        
        return ToolResult(
            output=f"Weather in {location}: {weather_data['temperature']}, {weather_data['condition']}. "
                   f"Humidity: {weather_data['humidity']}, Wind: {weather_data['wind']}",
            data=weather_data
        )


class MockJokeTool(BaseTool):
    """Mock joke tool for testing."""
    
    name: str = "tell_joke"
    description: str = "Tell a random joke"
    
    async def execute(self, topic: str = "general") -> ToolResult:
        """Mock joke."""
        jokes = {
            "general": "Why don't scientists trust atoms? Because they make up everything!",
            "programming": "Why do programmers prefer dark mode? Because light attracts bugs!",
            "ai": "Why did the neural network go to therapy? It had too many deep issues!",
        }
        
        joke = jokes.get(topic, jokes["general"])
        return ToolResult(
            output=f"Here's a {topic} joke: {joke}",
            data={"joke": joke, "topic": topic}
        )


def create_test_agent():
    """Create a test agent with mock tools."""
    # Mock LLM config (won't actually call LLM in this demo)
    llm_settings = LLMSettings(
        model="mock-model",
        api_key="mock-key",
        temperature=0.7
    )
    llm = LLM("test", llm_settings)
    
    # Create tools
    tools = [
        MockWeatherTool(),
        MockJokeTool(),
    ]
    
    # Create agent
    agent = create_react_agent(tools=tools, llm=llm)
    
    # Override the agent's run method for testing
    original_run = agent.run if hasattr(agent, 'run') else agent.arun
    
    async def mock_run(user_input: str):
        """Mock agent run that simulates responses without calling LLM."""
        user_input_lower = user_input.lower()
        
        if "weather" in user_input_lower:
            # Simulate weather query
            weather_tool = next(tool for tool in tools if tool.name == "get_weather")
            result = await weather_tool.execute("San Francisco")
            agent.final_response = result.output
            return result.output
        
        elif "joke" in user_input_lower:
            # Simulate joke request
            joke_tool = next(tool for tool in tools if tool.name == "tell_joke")
            result = await joke_tool.execute("general")
            agent.final_response = result.output
            return result.output
        
        elif "remember" in user_input_lower or "previous" in user_input_lower:
            # Simulate memory query
            response = ("Yes, I remember our conversation! We talked about the weather "
                       "and I told you a joke. This shows that the session state was "
                       "successfully restored and I can access our conversation history.")
            agent.final_response = response
            return response
        
        else:
            # Default response
            response = f"I understand you said: '{user_input}'. How can I help you today?"
            agent.final_response = response
            return response
    
    # Replace the run method
    if hasattr(agent, 'arun'):
        agent.arun = mock_run
    else:
        agent.run = mock_run
    
    return agent


async def main():
    """Start the test server."""
    print("🚀 Starting MyAgent WebSocket test server with state management...")
    print("=" * 60)
    
    # Create server with state management
    server = AgentWebSocketServer(
        agent_factory_func=create_test_agent,
        host="localhost",
        port=8080,
        state_secret_key="test-secret-key-for-demo-only-do-not-use-in-production"
    )
    
    print("📡 Server configuration:")
    print(f"  Host: {server.host}")
    print(f"  Port: {server.port}")
    print(f"  State management: Enabled")
    print(f"  WebSocket URL: ws://{server.host}:{server.port}")
    
    print("\n🔧 Available mock tools:")
    print("  - get_weather: Returns mock weather data")
    print("  - tell_joke: Returns mock jokes")
    
    print("\n💡 To test client state management:")
    print("  1. Run this server")
    print("  2. In another terminal, run: python examples/client_state_demo.py")
    print("  3. Watch the demo of state export, disconnect, and restore")
    
    print("\n🎯 Supported client events:")
    print("  - user.create_session: Create new session")
    print("  - user.message: Send message to agent")
    print("  - user.request_state: Export current session state")
    print("  - user.reconnect_with_state: Restore session from state")
    print("  - user.cancel: Cancel current operation")
    
    print("\n" + "=" * 60)
    print("🎉 Server ready! Press Ctrl+C to stop.")
    print("=" * 60)
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        logger.exception("Server error")
    finally:
        print("🧹 Cleaning up...")
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())