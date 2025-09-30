#!/usr/bin/env python3
"""
Deep Agent Example

Demonstrates how to use the Deep Agent implementation based on myagent framework.
Shows planning, file system, and sub-agent capabilities in action.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Deep Agent components
from myagent.middleware.deep_agent import create_deep_agent
from myagent.tool.base_tool import BaseTool, ToolResult

# Example: Custom tool for demonstration
class WebSearchTool(BaseTool):
    """Example web search tool for demonstration."""
    
    name: str = "web_search"
    description: str = "Search the web for information on a given topic"
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results",
                "default": 5
            }
        },
        "required": ["query"]
    }

    async def execute(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """Simulate web search results."""
        # In a real implementation, this would use an actual search API
        results = [
            f"Search result {i+1} for '{query}': Mock result content..."
            for i in range(min(max_results, 3))
        ]
        
        output = f"🔍 **Web Search Results for '{query}':**\n\n"
        output += "\n".join([f"{i+1}. {result}" for i, result in enumerate(results)])
        
        return ToolResult(output=output)


async def research_workflow_example():
    """Example of a complex research workflow using Deep Agent capabilities."""
    
    print("🤖 Creating Deep Agent with research capabilities...")
    
    # Create Deep Agent with additional tools
    agent = create_deep_agent(
        tools=[WebSearchTool()],
        llm_config={
            "model": "gpt-4",
            "temperature": 0.7
        },
        name="research_agent",
        description="Research specialist with Deep Agent capabilities"
    )
    
    # Complex research task
    research_request = """
    I need you to conduct comprehensive research on "AI Safety in Large Language Models" and create a detailed report. 
    
    Your task should include:
    1. Research current developments and key concerns
    2. Analyze different approaches to AI safety
    3. Create a structured report with findings
    4. Provide recommendations for best practices
    
    Please organize your work systematically and save your findings to files for reference.
    """
    
    print("\n📋 Starting research workflow...")
    print("=" * 60)
    
    try:
        # Execute the research workflow
        result = await agent.run(research_request)
        
        print("\n✅ Research workflow completed!")
        print("=" * 60)
        print(result)
        
        # Show final memory state
        print("\n📊 Final Agent State:")
        print(f"Total messages: {len(agent.memory.messages)}")
        print(f"Final response: {agent.final_response[:200]}..." if agent.final_response else "No final response")
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")


async def planning_example():
    """Example of task planning capabilities."""
    
    print("\n🎯 Demonstrating Planning Capabilities...")
    print("=" * 60)
    
    agent = create_deep_agent(
        name="planning_agent",
        description="Agent focused on task planning and management"
    )
    
    planning_request = """
    Help me plan a software development project for a new web application. 
    Break down the project into manageable tasks and create a comprehensive plan.
    
    The app should be a task management system with user authentication, 
    task creation/editing, and collaborative features.
    """
    
    try:
        result = await agent.run(planning_request)
        print(result)
        
    except Exception as e:
        print(f"❌ Error during planning: {e}")


async def file_system_example():
    """Example of virtual file system capabilities."""
    
    print("\n📁 Demonstrating File System Capabilities...")
    print("=" * 60)
    
    agent = create_deep_agent(
        name="file_agent", 
        description="Agent with file management capabilities"
    )
    
    file_request = """
    Create a project documentation structure with the following files:
    1. A README.md with project overview
    2. A CHANGELOG.md with version history
    3. A TODO.md with remaining tasks
    
    Then demonstrate reading and editing capabilities by updating the TODO.md file.
    """
    
    try:
        result = await agent.run(file_request)
        print(result)
        
    except Exception as e:
        print(f"❌ Error during file operations: {e}")


async def subagent_example():
    """Example of sub-agent delegation."""
    
    print("\n🤖 Demonstrating Sub-Agent Capabilities...")
    print("=" * 60)
    
    agent = create_deep_agent(
        tools=[WebSearchTool()],
        name="coordinator_agent",
        description="Coordinator agent that delegates to sub-agents"
    )
    
    delegation_request = """
    I need you to coordinate a comprehensive analysis of three different topics:
    
    1. Research the latest trends in artificial intelligence (use research-agent)
    2. Analyze code quality best practices for Python projects (use code-reviewer) 
    3. Create a general comparison framework for the findings (use general-purpose)
    
    Coordinate these tasks and compile a final summary report.
    """
    
    try:
        result = await agent.run(delegation_request)
        print(result)
        
    except Exception as e:
        print(f"❌ Error during sub-agent coordination: {e}")


async def integrated_workflow_example():
    """Example showing all Deep Agent capabilities working together."""
    
    print("\n🔮 Demonstrating Integrated Deep Agent Workflow...")
    print("=" * 60)
    
    agent = create_deep_agent(
        tools=[WebSearchTool()],
        name="deep_agent_full",
        description="Full Deep Agent with all capabilities"
    )
    
    complex_request = """
    I'm launching a new AI startup and need comprehensive preparation. Please help me with:
    
    1. Market research on the AI industry landscape
    2. Competitive analysis of similar companies
    3. Technical architecture planning for our platform
    4. Business plan documentation
    5. Risk assessment and mitigation strategies
    
    Use your full capabilities - planning, research, file management, and delegation - 
    to create a complete startup preparation package with all documentation.
    """
    
    try:
        result = await agent.run(complex_request)
        print(result)
        
        # Show the comprehensive results
        print("\n📊 Workflow Summary:")
        print(f"Steps executed: {agent.current_step}")
        print(f"Messages in memory: {len(agent.memory.messages)}")
        
    except Exception as e:
        print(f"❌ Error during integrated workflow: {e}")


async def main():
    """Run all Deep Agent examples."""
    
    print("🚀 Deep Agent Examples - MyAgent Implementation")
    print("Based on DeepAgents architecture adapted for myagent framework")
    print("=" * 80)
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found in environment")
        print("Please set your OpenAI API key in .env file or environment")
        return
    
    examples = [
        ("Basic Planning", planning_example),
        ("File System Operations", file_system_example), 
        ("Sub-Agent Delegation", subagent_example),
        ("Research Workflow", research_workflow_example),
        ("Integrated Workflow", integrated_workflow_example)
    ]
    
    for name, example_func in examples:
        try:
            print(f"\n🎯 Running Example: {name}")
            await example_func()
            print(f"✅ Completed: {name}")
            
            # Wait between examples
            await asyncio.sleep(1)
            
        except KeyboardInterrupt:
            print("\n⏹️  Examples interrupted by user")
            break
        except Exception as e:
            print(f"❌ Example '{name}' failed: {e}")
            continue
    
    print("\n🎉 All Deep Agent examples completed!")
    print("\nKey capabilities demonstrated:")
    print("✅ Task planning and management with write_todos")
    print("✅ Virtual file system with persistent storage")
    print("✅ Sub-agent delegation for specialized tasks")
    print("✅ Integrated workflows combining all capabilities")
    print("✅ Complex multi-step task execution")


if __name__ == "__main__":
    asyncio.run(main())