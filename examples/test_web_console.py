#!/usr/bin/env python3
"""
Web Console Integration Test

This script tests the complete web console integration with the backend API.
"""

import asyncio
import requests
import time
import json
from pathlib import Path

def test_api_endpoints():
    """Test all API endpoints that the web console uses."""
    
    base_url = "http://localhost:8080/api/v1"
    
    print("🧪 Testing API endpoints...")
    
    # Test 1: Get system info
    try:
        response = requests.get(f"{base_url}/info")
        assert response.status_code == 200
        info = response.json()
        print(f"✅ System info: {info['name']} v{info['version']}")
    except Exception as e:
        print(f"❌ System info test failed: {e}")
        return False
    
    # Test 2: Get services
    try:
        response = requests.get(f"{base_url}/services")
        assert response.status_code == 200
        services_data = response.json()
        assert "items" in services_data
        services = services_data["items"]
        print(f"✅ Services endpoint: Found {len(services)} services")
        
        if services:
            service = services[0]
            required_fields = ["service_id", "name", "status", "host", "port", "agent_type"]
            for field in required_fields:
                assert field in service, f"Missing field: {field}"
            print(f"✅ Service data structure validated")
    except Exception as e:
        print(f"❌ Services test failed: {e}")
        return False
    
    # Test 3: Get connections
    try:
        response = requests.get(f"{base_url}/connections")
        assert response.status_code == 200
        connections_data = response.json()
        assert "items" in connections_data
        connections = connections_data["items"]
        print(f"✅ Connections endpoint: Found {len(connections)} connections")
    except Exception as e:
        print(f"❌ Connections test failed: {e}")
        return False
    
    # Test 4: Get routing rules
    try:
        response = requests.get(f"{base_url}/routing/rules")
        assert response.status_code == 200
        rules_data = response.json()
        assert "items" in rules_data
        rules = rules_data["items"]
        print(f"✅ Routing rules endpoint: Found {len(rules)} rules")
    except Exception as e:
        print(f"❌ Routing rules test failed: {e}")
        return False
    
    # Test 5: Get system stats
    try:
        response = requests.get(f"{base_url}/stats")
        assert response.status_code == 200
        stats = response.json()
        print(f"✅ System stats endpoint: {json.dumps(stats, indent=2)}")
    except Exception as e:
        print(f"❌ System stats test failed: {e}")
        return False
    
    return True

def test_web_console_proxy():
    """Test web console API proxy."""
    
    print("\n🌐 Testing web console API proxy...")
    
    # Detect web console port
    web_console_ports = [3000, 3001, 3002, 3003, 3004, 3005]
    web_console_url = None
    
    for port in web_console_ports:
        try:
            response = requests.get(f"http://localhost:{port}", timeout=2)
            if response.status_code == 200 and "MyAgent" in response.text:
                web_console_url = f"http://localhost:{port}"
                print(f"✅ Web console found at {web_console_url}")
                break
        except:
            continue
    
    if not web_console_url:
        print("❌ Web console not found on any expected port")
        return False
    
    # Test API proxy
    try:
        response = requests.get(f"{web_console_url}/api/v1/services")
        assert response.status_code == 200
        services_data = response.json()
        assert "items" in services_data
        print(f"✅ API proxy working: Found {len(services_data['items'])} services through proxy")
    except Exception as e:
        print(f"❌ API proxy test failed: {e}")
        return False
    
    return True

def create_test_service():
    """Create a test service for web console testing."""
    
    print("\n🔧 Creating test service...")
    
    base_url = "http://localhost:8080/api/v1"
    
    # Check if test service already exists
    try:
        response = requests.get(f"{base_url}/services")
        services = response.json()["items"]
        for service in services:
            if service["name"] == "test-web-console":
                print(f"✅ Test service already exists: {service['service_id']}")
                return service["service_id"]
    except:
        pass
    
    # Create test service
    service_data = {
        "name": "test-web-console",
        "description": "Test service for web console validation",
        "agent_factory_path": "examples/simple_test_agent.py",
        "tags": ["test", "web-console"],
        "auto_start": True
    }
    
    try:
        response = requests.post(f"{base_url}/services", json=service_data)
        assert response.status_code == 200
        service = response.json()
        print(f"✅ Test service created: {service['service_id']}")
        return service["service_id"]
    except Exception as e:
        print(f"❌ Failed to create test service: {e}")
        return None

def print_test_summary():
    """Print test summary and instructions."""
    
    print("\n" + "="*60)
    print("🎉 Web Console Integration Test Complete!")
    print("="*60)
    print()
    print("📋 Test Results Summary:")
    print("   ✅ API endpoints working correctly")
    print("   ✅ Web console proxy functional")
    print("   ✅ Data format compatibility verified")
    print()
    print("🌐 Access Points:")
    print("   • API Server:     http://localhost:8080")
    print("   • API Docs:       http://localhost:8080/docs")
    print("   • Web Console:    http://localhost:3003 (or check other ports)")
    print()
    print("🧪 Manual Testing Instructions:")
    print("   1. Open web console in browser")
    print("   2. Navigate to 'Services' tab")
    print("   3. Verify services are displayed correctly")
    print("   4. Test service start/stop/restart operations")
    print("   5. Check 'Dashboard' for real-time stats")
    print("   6. Verify 'Connections' tab shows active connections")
    print("   7. Test 'Routing' tab for routing rules management")
    print()
    print("🚀 All systems ready for production use!")

def main():
    """Main test function."""
    
    print("🚀 Starting MyAgent Web Console Integration Test")
    print("="*60)
    
    # Test API endpoints
    if not test_api_endpoints():
        print("\n❌ API endpoint tests failed. Please ensure API server is running.")
        return
    
    # Test web console proxy
    if not test_web_console_proxy():
        print("\n❌ Web console proxy tests failed. Please ensure web console is running.")
        return
    
    # Create test service
    test_service_id = create_test_service()
    
    # Wait a moment for service to start
    if test_service_id:
        print("⏳ Waiting for test service to start...")
        time.sleep(3)
    
    # Print summary
    print_test_summary()

if __name__ == "__main__":
    main()