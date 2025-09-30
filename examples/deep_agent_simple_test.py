#!/usr/bin/env python3
"""
Simple Deep Agent Test

A basic test to verify Deep Agent functionality without external dependencies.
Tests core capabilities: planning, filesystem, and basic workflows.
"""

import asyncio
import sys
import os

# Add the parent directory to path to import myagent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from myagent.middleware.deep_agent import create_deep_agent
    from myagent.tool.base_tool import BaseTool, ToolResult
    print("✅ Successfully imported Deep Agent components")
except ImportError as e:
    print(f"❌ Failed to import Deep Agent components: {e}")
    sys.exit(1)


class SimpleMockTool(BaseTool):
    """Simple mock tool for testing."""
    
    name: str = "mock_calculator"
    description: str = "Perform basic calculations"
    parameters: dict = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Operation to perform",
                "enum": ["add", "subtract", "multiply", "divide"]
            },
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"}
        },
        "required": ["operation", "a", "b"]
    }

    async def execute(self, operation: str, a: float, b: float, **kwargs) -> ToolResult:
        """Perform calculation."""
        try:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    return ToolResult(error="Division by zero")
                result = a / b
            else:
                return ToolResult(error=f"Unknown operation: {operation}")
            
            return ToolResult(
                output=f"🧮 Calculation: {a} {operation} {b} = {result}",
                system=f"Performed {operation} operation successfully"
            )
        except Exception as e:
            return ToolResult(error=f"Calculation failed: {e}")


async def test_basic_functionality():
    """Test basic Deep Agent functionality."""
    print("\n🧪 Testing Basic Deep Agent Functionality...")
    print("=" * 60)
    
    try:
        # Create a Deep Agent with minimal configuration
        agent = create_deep_agent(
            tools=[SimpleMockTool()],
            name="test_agent",
            description="Simple test agent"
        )
        
        print("✅ Deep Agent created successfully")
        print(f"Agent name: {agent.name}")
        print(f"Agent description: {agent.description}")
        
        # Test basic prompt structure
        if agent.system_prompt:
            print("✅ System prompt configured")
            print(f"Prompt length: {len(agent.system_prompt)} characters")
        else:
            print("⚠️  No system prompt found")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


async def test_planning_tool():
    """Test the planning tool specifically."""
    print("\n📋 Testing Planning Tool...")
    print("=" * 60)
    
    try:
        agent = create_deep_agent(
            tools=[SimpleMockTool()],
            name="planning_test_agent"
        )
        
        # Look for planning tool in agent tools
        planning_tool = None
        if hasattr(agent, 'available_tools') and hasattr(agent.available_tools, 'tool_map'):
            for tool in agent.available_tools.tool_map.values():
                if hasattr(tool, 'name') and tool.name == "write_todos":
                    planning_tool = tool
                    break
        
        if planning_tool:
            print("✅ Planning tool found in agent")
            
            # Test planning tool directly
            test_todos = [
                {
                    "content": "Test task 1",
                    "status": "pending",
                    "activeForm": "Testing task 1",
                    "priority": "high"
                },
                {
                    "content": "Test task 2", 
                    "status": "in_progress",
                    "activeForm": "Testing task 2",
                    "priority": "medium"
                }
            ]
            
            result = await planning_tool.execute(todos=test_todos)
            
            if result and result.output:
                print("✅ Planning tool executed successfully")
                print("📋 Planning tool output preview:")
                print(result.output[:200] + "..." if len(result.output) > 200 else result.output)
            else:
                print("⚠️  Planning tool executed but no output")
            
            return True
        else:
            print("❌ Planning tool not found in agent")
            return False
            
    except Exception as e:
        print(f"❌ Planning tool test failed: {e}")
        return False


async def test_filesystem_tool():
    """Test the filesystem tools."""
    print("\n📁 Testing Filesystem Tools...")
    print("=" * 60)
    
    try:
        agent = create_deep_agent(
            tools=[SimpleMockTool()],
            name="filesystem_test_agent"
        )
        
        # Look for filesystem tools
        fs_tools = {}
        if hasattr(agent, 'available_tools') and hasattr(agent.available_tools, 'tool_map'):
            for tool in agent.available_tools.tool_map.values():
                if hasattr(tool, 'name'):
                    if tool.name in ["ls", "read_file", "write_file", "edit_file"]:
                        fs_tools[tool.name] = tool
        
        print(f"✅ Found {len(fs_tools)} filesystem tools: {list(fs_tools.keys())}")
        
        if "write_file" in fs_tools and "read_file" in fs_tools and "ls" in fs_tools:
            # Test basic file operations
            write_tool = fs_tools["write_file"]
            read_tool = fs_tools["read_file"]
            ls_tool = fs_tools["ls"]
            
            # Test file creation
            write_result = await write_tool.execute(
                file_path="test.txt",
                content="Hello, Deep Agent filesystem!"
            )
            
            if write_result and not write_result.error:
                print("✅ File write test passed")
                
                # Test file listing
                ls_result = await ls_tool.execute()
                if ls_result and not ls_result.error:
                    print("✅ File listing test passed")
                    
                    # Test file reading
                    read_result = await read_tool.execute(file_path="test.txt")
                    if read_result and not read_result.error:
                        print("✅ File read test passed")
                        print("📄 File content preview:")
                        print(read_result.output[:100] + "..." if len(read_result.output) > 100 else read_result.output)
                        return True
                    else:
                        print(f"❌ File read failed: {read_result.error if read_result else 'No result'}")
                else:
                    print(f"❌ File listing failed: {ls_result.error if ls_result else 'No result'}")
            else:
                print(f"❌ File write failed: {write_result.error if write_result else 'No result'}")
        else:
            print("❌ Required filesystem tools not found")
        
        return False
        
    except Exception as e:
        print(f"❌ Filesystem test failed: {e}")
        return False


async def test_tool_integration():
    """Test tool integration and availability."""
    print("\n🔧 Testing Tool Integration...")
    print("=" * 60)
    
    try:
        agent = create_deep_agent(
            tools=[SimpleMockTool()],
            name="tool_integration_test"
        )
        
        total_tools = len(agent.available_tools.tool_map) if hasattr(agent, 'available_tools') else 0
        print(f"✅ Agent created with {total_tools} tools")
        
        # List all available tools
        print("🔧 Available tools:")
        if hasattr(agent, 'available_tools') and hasattr(agent.available_tools, 'tool_map'):
            for i, tool in enumerate(agent.available_tools.tool_map.values(), 1):
                tool_name = getattr(tool, 'name', 'Unknown')
                tool_desc = getattr(tool, 'description', 'No description')
                print(f"  {i}. {tool_name}: {tool_desc}")
        
        # Check for Deep Agent core tools
        expected_tools = ["write_todos", "ls", "read_file", "write_file", "edit_file", "task"]
        found_tools = []
        
        if hasattr(agent, 'available_tools') and hasattr(agent.available_tools, 'tool_map'):
            for tool in agent.available_tools.tool_map.values():
                if hasattr(tool, 'name') and tool.name in expected_tools:
                    found_tools.append(tool.name)
        
        print(f"\n✅ Found {len(found_tools)}/{len(expected_tools)} expected Deep Agent tools:")
        for tool_name in found_tools:
            print(f"  ✓ {tool_name}")
        
        missing_tools = set(expected_tools) - set(found_tools)
        if missing_tools:
            print(f"⚠️  Missing tools: {list(missing_tools)}")
        
        return len(found_tools) >= 4  # At least most tools should be available
        
    except Exception as e:
        print(f"❌ Tool integration test failed: {e}")
        return False


async def run_simple_tests():
    """Run all simple tests."""
    print("🚀 Deep Agent Simple Test Suite")
    print("Testing core functionality without external dependencies")
    print("=" * 80)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Planning Tool", test_planning_tool),
        ("Filesystem Tools", test_filesystem_tool),
        ("Tool Integration", test_tool_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n🎯 Running: {test_name}")
            success = await test_func()
            results[test_name] = success
            
            if success:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
                
        except Exception as e:
            print(f"❌ {test_name} encountered error: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Test Results Summary:")
    print("=" * 80)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {test_name.ljust(20)} : {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎊 All tests passed! Deep Agent implementation is working correctly.")
    elif passed >= total * 0.5:
        print("⚠️  Some tests failed, but core functionality appears to work.")
    else:
        print("❌ Multiple test failures. Deep Agent implementation may have issues.")
    
    return results


if __name__ == "__main__":
    try:
        results = asyncio.run(run_simple_tests())
        
        # Exit with appropriate code
        passed = sum(1 for success in results.values() if success)
        total = len(results)
        
        if passed == total:
            sys.exit(0)  # Success
        elif passed >= total * 0.5:
            sys.exit(1)  # Partial success
        else:
            sys.exit(2)  # Failure
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        sys.exit(3)