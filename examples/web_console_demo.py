#!/usr/bin/env python3
"""
Web Console Demo Script

This script demonstrates the complete web console functionality by:
1. Starting the API server
2. Setting up demo services
3. Providing instructions for web console testing

Usage:
    python examples/web_console_demo.py
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add the parent directory to the path so we can import myagent
sys.path.insert(0, str(Path(__file__).parent.parent))

from myagent.manager.core.manager import AgentManager
from myagent.manager.storage.models import ServiceConfig


async def setup_demo_services():
    """Setup demo services for web console testing."""
    print("🔧 Setting up demo services...")
    
    manager = AgentManager()
    async with manager:
        # Create a simple weather agent service
        weather_config = ServiceConfig(
            max_connections=10,
            timeout=30,
            restart_policy="on_failure",
            env_vars={"DEMO_MODE": "true"},
            args=[]
        )
        
        try:
            weather_service = await manager.registry.register_service(
                name="weather-demo",
                agent_factory_path="examples/ws_weather_agent.py",
                description="Demo weather agent for web console testing",
                port=8881,
                tags={"demo", "weather"},
                config=weather_config
            )
            print(f"✅ Registered weather demo service: {weather_service.service_id}")
            
            # Start the service
            started_service = await manager.registry.start_service(weather_service.service_id)
            print(f"🚀 Started weather demo service on port {started_service.port}")
            
        except Exception as e:
            print(f"⚠️  Weather service setup failed (might already exist): {e}")
        
        # Create a simple echo agent service
        try:
            echo_service = await manager.registry.register_service(
                name="echo-demo",
                agent_factory_path="examples/simple_test_agent.py", 
                description="Demo echo agent for web console testing",
                port=8882,
                tags={"demo", "echo"},
                config=weather_config
            )
            print(f"✅ Registered echo demo service: {echo_service.service_id}")
            
            # Start the service
            started_service = await manager.registry.start_service(echo_service.service_id)
            print(f"🚀 Started echo demo service on port {started_service.port}")
            
        except Exception as e:
            print(f"⚠️  Echo service setup failed (might already exist): {e}")
        
        # List all services
        services = await manager.registry.get_services()
        print(f"\n📋 Total services registered: {len(services)}")
        for service in services:
            print(f"   - {service.name} ({service.status}) on port {service.port}")


def start_api_server():
    """Start the API server in a subprocess."""
    print("🚀 Starting API server on port 8080...")
    
    # Start API server with proxy
    cmd = [
        sys.executable, "-m", "myagent.manager.cli.api",
        "--port", "8080",
        "--proxy-port", "9090"
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if it's still running
        if process.poll() is None:
            print("✅ API server started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ API server failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return None


def start_web_console():
    """Start the web console development server."""
    console_dir = Path(__file__).parent.parent / "myagent" / "web-console"
    
    if not console_dir.exists():
        print("❌ Web console directory not found!")
        return None
    
    print("🌐 Starting web console development server...")
    
    # Check if node_modules exists
    if not (console_dir / "node_modules").exists():
        print("📦 Installing web console dependencies...")
        install_cmd = ["npm", "install"]
        try:
            subprocess.run(install_cmd, cwd=console_dir, check=True)
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return None
    
    # Start development server
    cmd = ["npm", "run", "dev"]
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=console_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        time.sleep(5)
        
        # Check if it's still running
        if process.poll() is None:
            print("✅ Web console started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Web console failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
    except Exception as e:
        print(f"❌ Failed to start web console: {e}")
        return None


def print_instructions():
    """Print instructions for testing the web console."""
    print("\n" + "="*60)
    print("🎉 MyAgent Web Console Demo Setup Complete!")
    print("="*60)
    print()
    print("📍 Access Points:")
    print("   • Web Console:    http://localhost:3000")
    print("   • API Server:     http://localhost:8080")
    print("   • API Docs:       http://localhost:8080/docs")
    print("   • WebSocket Proxy: ws://localhost:9090")
    print()
    print("🧪 Testing Checklist:")
    print("   1. Open web console at http://localhost:3000")
    print("   2. Check Dashboard - should show system overview")
    print("   3. Go to Services - should show 2 demo services")
    print("   4. Test service start/stop/restart operations")
    print("   5. Check Connections - monitor active connections")
    print("   6. Go to Routing - create and test routing rules")
    print()
    print("🔗 WebSocket Testing:")
    print("   • Connect to ws://localhost:9090 with any WebSocket client")
    print("   • Messages will be routed to available services")
    print("   • Monitor connections in real-time via web console")
    print()
    print("🛠️  Manual Testing Commands:")
    print("   # List services via API")
    print("   curl http://localhost:8080/api/v1/services")
    print()
    print("   # Get system stats")
    print("   curl http://localhost:8080/api/v1/stats")
    print()
    print("   # WebSocket test with wscat (if installed)")
    print("   wscat -c ws://localhost:9090")
    print()
    print("⚠️  Note: Keep this terminal open to maintain the demo environment")
    print("   Press Ctrl+C to stop all services")


async def main():
    """Main demo function."""
    print("🚀 Starting MyAgent Web Console Demo")
    print("="*50)
    
    # Setup demo services first
    await setup_demo_services()
    
    # Start API server
    api_process = start_api_server()
    if not api_process:
        print("❌ Cannot continue without API server")
        return
    
    # Start web console
    console_process = start_web_console()
    
    # Print instructions
    print_instructions()
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down demo environment...")
        
        # Cleanup processes
        if api_process:
            api_process.terminate()
            api_process.wait()
            print("✅ API server stopped")
        
        if console_process:
            console_process.terminate()
            console_process.wait()
            print("✅ Web console stopped")
        
        print("👋 Demo environment stopped successfully")


if __name__ == "__main__":
    asyncio.run(main())