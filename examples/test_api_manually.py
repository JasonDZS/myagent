"""Manual test script for the HTTP API server."""

import asyncio
import time

from myagent.manager import AgentManager
from myagent.manager.api.server import APIServer


async def run_manual_api_test():
    """Run API server for manual testing."""
    print("🚀 Starting MyAgent HTTP API Server for manual testing")
    print("=" * 60)
    
    # Create manager and API server
    manager = AgentManager("test_api.db")
    api_server = APIServer(manager)
    
    try:
        # Start manager
        print("\n1. Starting manager...")
        await manager.start(health_check_interval=15)
        print("   ✅ Manager started")
        
        # Start API server
        print("\n2. Starting API server...")
        print("   🌐 API Server: http://localhost:8888")
        print("   📖 Documentation: http://localhost:8888/docs")
        print("   🔧 Admin Interface: http://localhost:8888/redoc")
        
        print("\n3. Available API endpoints:")
        print("   GET  /health                              - Health check")
        print("   GET  /api/v1/info                         - System info")
        print("   GET  /api/v1/services                     - List services")
        print("   POST /api/v1/services                     - Create service")
        print("   GET  /api/v1/services/{id}                - Get service")
        print("   PUT  /api/v1/services/{id}                - Update service")
        print("   DELETE /api/v1/services/{id}              - Delete service")
        print("   POST /api/v1/services/{id}/start          - Start service")
        print("   POST /api/v1/services/{id}/stop           - Stop service")
        print("   POST /api/v1/services/{id}/restart        - Restart service")
        print("   GET  /api/v1/services/{id}/stats          - Service stats")
        print("   GET  /api/v1/services/{id}/health         - Service health")
        print("   GET  /api/v1/stats                        - System stats")
        print("   GET  /api/v1/routing/rules                - List routing rules")
        print("   POST /api/v1/routing/rules                - Create routing rule")
        
        print("\n4. Example curl commands:")
        print("   # Get system info")
        print("   curl http://localhost:8888/api/v1/info")
        print()
        print("   # List services")
        print("   curl http://localhost:8888/api/v1/services")
        print()
        print("   # Create a service")
        print("   curl -X POST http://localhost:8888/api/v1/services \\")
        print("        -H 'Content-Type: application/json' \\")
        print("        -d '{")
        print("          \"name\": \"test-service\",")
        print("          \"agent_factory_path\": \"./ws_weather_agent.py\",")
        print("          \"description\": \"Test service\",")
        print("          \"tags\": [\"test\"],")
        print("          \"auto_start\": true")
        print("        }'")
        print()
        print("   # Get system statistics")
        print("   curl http://localhost:8888/api/v1/stats")
        
        print("\n5. Python client example:")
        print("   import httpx")
        print("   async with httpx.AsyncClient() as client:")
        print("       response = await client.get('http://localhost:8888/api/v1/info')")
        print("       print(response.json())")
        
        print("\n🎉 API Server is running!")
        print("   Press Ctrl+C to stop the server")
        
        # Start API server
        await api_server.start("localhost", 8888)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("🧹 Cleaning up...")
        await manager.stop()
        print("✅ Server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(run_manual_api_test())
    except KeyboardInterrupt:
        print("\n✅ Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")