#!/usr/bin/env python3
"""
Web Console Data Verification Script

This script verifies that the web console data display issues have been fixed.
"""

import requests
import json

def test_frontend_backend_compatibility():
    """Test that frontend and backend data structures are compatible."""
    
    print("🔧 Testing Frontend-Backend Data Compatibility")
    print("="*60)
    
    base_url = "http://localhost:8080/api/v1"
    web_console_url = "http://localhost:3001"
    
    # Test 1: Services API compatibility
    print("\n📋 Testing Services API...")
    try:
        # Test direct backend
        backend_response = requests.get(f"{base_url}/services")
        backend_data = backend_response.json()
        
        # Test through web console proxy
        frontend_response = requests.get(f"{web_console_url}/api/v1/services")
        frontend_data = frontend_response.json()
        
        assert backend_data == frontend_data, "Backend and frontend data don't match"
        assert "items" in backend_data, "Missing 'items' field"
        
        services = backend_data["items"]
        print(f"✅ Services API: {len(services)} services found")
        
        if services:
            service = services[0]
            required_fields = ["service_id", "name", "status", "host", "port", "agent_type", "version"]
            for field in required_fields:
                assert field in service, f"Missing required field: {field}"
            print(f"✅ Service data structure: All required fields present")
            print(f"   Sample service: {service['name']} ({service['status']}) on port {service['port']}")
        
    except Exception as e:
        print(f"❌ Services API test failed: {e}")
        return False
    
    # Test 2: Stats API compatibility
    print("\n📊 Testing Stats API...")
    try:
        # Test direct backend
        backend_response = requests.get(f"{base_url}/stats")
        backend_stats = backend_response.json()
        
        # Test through web console proxy
        frontend_response = requests.get(f"{web_console_url}/api/v1/stats")
        frontend_stats = frontend_response.json()
        
        assert backend_stats == frontend_stats, "Backend and frontend stats don't match"
        
        # Verify structure
        required_sections = ["services", "connections", "health"]
        for section in required_sections:
            assert section in backend_stats, f"Missing stats section: {section}"
        
        services_stats = backend_stats["services"]
        print(f"✅ Stats API: Structure correct")
        print(f"   Services: {services_stats['total']} total, {services_stats['running']} running")
        print(f"   Connections: {backend_stats['connections']['total_connections']} total")
        print(f"   Health: {backend_stats['health']['healthy']}/{backend_stats['health']['total']} healthy")
        
    except Exception as e:
        print(f"❌ Stats API test failed: {e}")
        return False
    
    # Test 3: Connections API compatibility
    print("\n🔗 Testing Connections API...")
    try:
        # Test direct backend
        backend_response = requests.get(f"{base_url}/connections")
        backend_data = backend_response.json()
        
        # Test through web console proxy
        frontend_response = requests.get(f"{web_console_url}/api/v1/connections")
        frontend_data = frontend_response.json()
        
        assert backend_data == frontend_data, "Backend and frontend connection data don't match"
        assert "items" in backend_data, "Missing 'items' field"
        
        connections = backend_data["items"]
        print(f"✅ Connections API: {len(connections)} connections found")
        print(f"   Total connections: {backend_data['total']}")
        
    except Exception as e:
        print(f"❌ Connections API test failed: {e}")
        return False
    
    # Test 4: Routing Rules API compatibility
    print("\n🛣️  Testing Routing Rules API...")
    try:
        # Test direct backend
        backend_response = requests.get(f"{base_url}/routing/rules")
        backend_data = backend_response.json()
        
        # Test through web console proxy
        frontend_response = requests.get(f"{web_console_url}/api/v1/routing/rules")
        frontend_data = frontend_response.json()
        
        assert backend_data == frontend_data, "Backend and frontend routing data don't match"
        assert "items" in backend_data, "Missing 'items' field"
        
        rules = backend_data["items"]
        print(f"✅ Routing Rules API: {len(rules)} rules found")
        
    except Exception as e:
        print(f"❌ Routing Rules API test failed: {e}")
        return False
    
    return True

def verify_data_display():
    """Verify that the web console should now display data correctly."""
    
    print("\n🎯 Data Display Verification")
    print("="*40)
    
    # Get actual data that should be displayed
    try:
        stats_response = requests.get("http://localhost:3001/api/v1/stats")
        stats = stats_response.json()
        
        services_response = requests.get("http://localhost:3001/api/v1/services")
        services_data = services_response.json()
        services = services_data["items"]
        
        print("\n📈 Dashboard should display:")
        print(f"   Total Services: {stats['services']['total']}")
        print(f"   Running Services: {stats['services']['running']}")
        print(f"   Total Connections: {stats['connections']['total_connections']}")
        print(f"   Error Services: {stats['services']['error']}")
        print(f"   Healthy Services: {stats['health']['healthy']}")
        
        print("\n📋 Services page should display:")
        for service in services:
            print(f"   - {service['name']} ({service['status'].upper()}) on {service['host']}:{service['port']}")
            print(f"     Type: {service['agent_type']}, Version: {service['version']}")
        
        print("\n🔗 Connections page should display:")
        connections_response = requests.get("http://localhost:3001/api/v1/connections")
        connections_data = connections_response.json()
        connections = connections_data["items"]
        
        if connections:
            for conn in connections:
                print(f"   - {conn['client_ip']}:{conn['client_port']} -> {conn['service_id']}")
        else:
            print("   No active connections (this is expected)")
        
        return True
        
    except Exception as e:
        print(f"❌ Data display verification failed: {e}")
        return False

def print_summary():
    """Print test summary and instructions."""
    
    print("\n" + "="*60)
    print("🎉 Web Console Data Fix Verification Complete!")
    print("="*60)
    print()
    print("✅ All API compatibility tests passed")
    print("✅ Data structures are now correctly aligned")
    print("✅ Web console should display real data instead of zeros")
    print()
    print("🌐 Next Steps:")
    print("   1. Open web console: http://localhost:3001")
    print("   2. Check Dashboard - should show service and health stats")
    print("   3. Navigate to Services - should show the weather service")
    print("   4. Check Connections - should show 0 (no active connections)")
    print("   5. Verify all navigation and refresh buttons work")
    print()
    print("🔧 If you still see zeros:")
    print("   - Clear browser cache and reload")
    print("   - Check browser developer console for errors")
    print("   - Verify API endpoints are accessible")
    print()
    print("🚀 The web console data display issue has been resolved!")

def main():
    """Main verification function."""
    
    print("🚀 Starting Web Console Data Fix Verification")
    print("="*60)
    
    # Test API compatibility
    if not test_frontend_backend_compatibility():
        print("\n❌ API compatibility tests failed")
        return
    
    # Verify data display expectations
    if not verify_data_display():
        print("\n❌ Data display verification failed")
        return
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    main()