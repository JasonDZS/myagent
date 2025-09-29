"""Demo script for MyAgent WebSocket Management System."""

import asyncio
import time
from pathlib import Path

from myagent.manager import AgentManager
from myagent.manager.storage.models import ServiceConfig


async def demo():
    """Demonstrate the WebSocket management system."""
    print("🚀 MyAgent WebSocket Management System Demo")
    print("=" * 50)
    
    # Create manager
    manager = AgentManager("demo_manager.db")
    
    try:
        # Start manager
        print("\n1. Starting manager...")
        await manager.start(health_check_interval=5)
        print("   ✅ Manager started")
        
        # Get path to weather agent example
        weather_agent_path = Path(__file__).parent / "ws_weather_agent.py"
        if not weather_agent_path.exists():
            print(f"   ⚠️  Weather agent not found at {weather_agent_path}")
            print("   Creating a simple agent for demo...")
            # Create a simple demo agent
            demo_agent_path = Path(__file__).parent / "demo_simple_agent.py"
            _create_demo_agent(demo_agent_path)
            weather_agent_path = demo_agent_path
        
        # Register services
        print("\n2. Registering services...")
        
        # Service 1: Weather Agent
        config1 = ServiceConfig(
            agent_factory_path=str(weather_agent_path),
            max_sessions=10,
            auto_restart=True,
            health_check_enabled=True,
        )
        
        service1 = await manager.register_service(
            name="weather-service",
            agent_factory_path=str(weather_agent_path),
            description="Weather information agent",
            tags={"weather", "information"},
            config=config1,
            auto_start=True,
        )
        
        if service1:
            print(f"   ✅ Registered weather-service at {service1.endpoint}")
        else:
            print("   ❌ Failed to register weather-service")
            return
        
        # Service 2: Another instance
        service2 = await manager.register_service(
            name="weather-service-2",
            agent_factory_path=str(weather_agent_path),
            description="Weather information agent (backup)",
            tags={"weather", "backup"},
            auto_start=True,
        )
        
        if service2:
            print(f"   ✅ Registered weather-service-2 at {service2.endpoint}")
        
        # List services
        print("\n3. Listing services...")
        services = manager.list_services()
        for service in services:
            print(f"   - {service.name}: {service.status.value} at {service.endpoint}")
        
        # Wait a bit for services to start up
        print("\n4. Waiting for services to start...")
        await asyncio.sleep(3)
        
        # Check health
        print("\n5. Checking service health...")
        health_results = await manager.check_all_services_health()
        for result in health_results:
            service = manager.get_service(result.service_id)
            print(f"   - {service.name}: {result.status.value} ({result.response_time_ms:.2f}ms)")
        
        # Show statistics
        print("\n6. System statistics...")
        stats = manager.get_system_stats()
        print(f"   - Total services: {stats['services']['total']}")
        print(f"   - Running services: {stats['services']['running']}")
        print(f"   - Total connections: {stats['connections']['total_connections']}")
        
        # Demonstrate routing
        print("\n7. Testing connection routing...")
        for i in range(5):
            target_service = await manager.route_connection(
                client_ip=f"192.168.1.{i+10}",
                client_port=8000 + i,
                user_agent="Demo Client",
            )
            if target_service:
                print(f"   - Connection {i+1} routed to: {target_service.name}")
        
        print("\n8. Demo completed successfully! 🎉")
        print("\nYou can now:")
        print("- Use the CLI: python -m myagent.manager.cli.manager list")
        print("- Start the proxy: python -m myagent.manager.cli.proxy")
        print("- Connect clients to: ws://localhost:9090")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        print("\n9. Cleaning up...")
        await manager.stop()
        print("   ✅ Manager stopped")


def _create_demo_agent(path: Path):
    """Create a simple demo agent file."""
    demo_agent_code = '''"""Simple demo agent for WebSocket management system."""

from myagent import create_react_agent
from myagent.tool import BaseTool, ToolResult


class EchoTool(BaseTool):
    """Simple echo tool for demo."""
    
    name: str = "echo"
    description: str = "Echo back the input message"
    
    async def execute(self, message: str) -> ToolResult:
        return ToolResult(
            success=True,
            content=f"Echo: {message}",
            metadata={"original_message": message}
        )


def create_agent():
    """Create demo agent."""
    return create_react_agent(
        name="demo-agent",
        tools=[EchoTool()],
        system_prompt="You are a simple demo agent that can echo messages.",
    )
'''
    
    path.write_text(demo_agent_code)
    print(f"   ✅ Created demo agent at {path}")


if __name__ == "__main__":
    asyncio.run(demo())