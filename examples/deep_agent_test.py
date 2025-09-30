#!/usr/bin/env python3
"""
Deep Agent Test Example

Tests the Deep Agent implementation with a comprehensive workflow
that demonstrates all capabilities: planning, filesystem, sub-agents, and integration.
"""

import asyncio
import argparse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Deep Agent and related components
from myagent.middleware.deep_agent import create_deep_agent
from myagent.tool.base_tool import BaseTool, ToolResult
from myagent.trace import get_trace_manager, TraceExporter, TraceQueryEngine

# Mock tools for testing
class MockWebSearchTool(BaseTool):
    """Mock web search tool for testing."""
    
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
        # Mock search results based on query
        mock_results = {
            "AI safety": [
                "AI Safety Research Institute publishes new guidelines for LLM alignment",
                "Constitutional AI: Training language models to be helpful, harmless, and honest",
                "Red teaming and adversarial testing in AI safety evaluation"
            ],
            "quantum computing": [
                "IBM unveils new 1000-qubit quantum processor with error correction",
                "Google's quantum supremacy achievement in cryptographic applications", 
                "Microsoft Azure Quantum cloud services now generally available"
            ],
            "machine learning": [
                "Transformer architecture improvements show 40% efficiency gains",
                "AutoML platforms democratize machine learning for small businesses",
                "Federated learning enables privacy-preserving distributed training"
            ]
        }
        
        # Find relevant results
        results = []
        for topic, topic_results in mock_results.items():
            if topic.lower() in query.lower():
                results.extend(topic_results[:max_results])
                break
        
        if not results:
            results = [
                f"General result 1 for '{query}': Latest developments in the field",
                f"General result 2 for '{query}': Research papers and industry reports",
                f"General result 3 for '{query}': Expert opinions and analysis"
            ]
        
        output = f"🔍 **Web Search Results for '{query}':**\n\n"
        output += "\n".join([f"{i+1}. {result}" for i, result in enumerate(results[:max_results])])
        
        return ToolResult(output=output)


class MockDataAnalysisTool(BaseTool):
    """Mock data analysis tool for testing."""
    
    name: str = "analyze_data"
    description: str = "Analyze data and generate insights"
    parameters: dict = {
        "type": "object",
        "properties": {
            "data_source": {
                "type": "string",
                "description": "Source or type of data to analyze"
            },
            "analysis_type": {
                "type": "string",
                "description": "Type of analysis to perform",
                "enum": ["statistical", "trend", "comparative", "predictive"]
            }
        },
        "required": ["data_source", "analysis_type"]
    }

    async def execute(self, data_source: str, analysis_type: str, **kwargs) -> ToolResult:
        """Simulate data analysis."""
        mock_analysis = {
            "statistical": f"Statistical analysis of {data_source}: Mean=42.5, Std=8.3, Median=41.2",
            "trend": f"Trend analysis of {data_source}: 15% upward trend over last quarter",
            "comparative": f"Comparative analysis of {data_source}: 23% above industry average",
            "predictive": f"Predictive analysis of {data_source}: 78% confidence in continued growth"
        }
        
        result = mock_analysis.get(analysis_type, f"General analysis of {data_source}")
        
        return ToolResult(
            output=f"📊 **Data Analysis Results:**\n\n{result}",
            system=f"Analysis completed for {data_source}"
        )


async def test_planning_workflow():
    """Test the planning capabilities of Deep Agent."""
    print("\n🎯 Testing Planning Workflow...")
    print("=" * 60)
    
    agent = create_deep_agent(
        tools=[MockWebSearchTool(), MockDataAnalysisTool()],
        llm_config={
            "model": "gpt-4",
            "temperature": 0.7
        },
        name="planning_test_agent",
        description="Agent for testing planning capabilities"
    )
    
    planning_request = """
    I need you to create a comprehensive research plan for analyzing the impact of AI on healthcare. 
    This should be a complex multi-step project that includes:
    
    1. Literature review and current state analysis
    2. Market research on AI healthcare companies
    3. Technical analysis of AI applications in healthcare
    4. Risk assessment and regulatory considerations
    5. Future trend predictions and recommendations
    
    Please create a detailed plan using your planning tools and then begin execution.
    """
    
    try:
        result = await agent.run(planning_request)
        print("✅ Planning workflow completed!")
        print(result)
        return True
        
    except Exception as e:
        print(f"❌ Planning workflow failed: {e}")
        return False


async def test_filesystem_workflow():
    """Test the virtual filesystem capabilities."""
    print("\n📁 Testing Filesystem Workflow...")
    print("=" * 60)
    
    agent = create_deep_agent(
        tools=[MockWebSearchTool()],
        name="filesystem_test_agent",
        description="Agent for testing filesystem capabilities"
    )
    
    filesystem_request = """
    Create a complete project documentation structure for a new AI research project. 
    
    Please create the following files:
    1. project_overview.md - with project description and objectives
    2. research_plan.md - with detailed research methodology 
    3. bibliography.md - with relevant sources and references
    4. progress_notes.md - with initial setup notes
    
    Then demonstrate file management by:
    - Reading each file to verify content
    - Editing the progress_notes.md to add a status update
    - Creating a summary report that references all files
    """
    
    try:
        result = await agent.run(filesystem_request)
        print("✅ Filesystem workflow completed!")
        print(result)
        return True
        
    except Exception as e:
        print(f"❌ Filesystem workflow failed: {e}")
        return False


async def test_subagent_workflow():
    """Test the sub-agent delegation capabilities."""
    print("\n🤖 Testing Sub-Agent Workflow...")
    print("=" * 60)
    
    agent = create_deep_agent(
        tools=[MockWebSearchTool(), MockDataAnalysisTool()],
        name="subagent_test_agent", 
        description="Agent for testing sub-agent capabilities"
    )
    
    subagent_request = """
    I need you to coordinate a comprehensive analysis using specialized sub-agents:
    
    1. Use the research-agent to investigate "AI safety in large language models"
    2. Use the code-reviewer to analyze best practices for AI system architecture
    3. Use the general-purpose agent to synthesize findings and create recommendations
    
    Coordinate these tasks and compile a final integrated report.
    """
    
    try:
        result = await agent.run(subagent_request)
        print("✅ Sub-agent workflow completed!")
        print(result)
        return True
        
    except Exception as e:
        print(f"❌ Sub-agent workflow failed: {e}")
        return False


async def test_integrated_workflow():
    """Test all Deep Agent capabilities working together."""
    print("\n🔮 Testing Integrated Workflow...")
    print("=" * 60)
    
    agent = create_deep_agent(
        tools=[MockWebSearchTool(), MockDataAnalysisTool()],
        name="integrated_test_agent",
        description="Agent for testing integrated Deep Agent capabilities"
    )
    
    integrated_request = """
    I'm developing a new AI startup focused on healthcare automation. I need comprehensive preparation including:
    
    1. Market research and competitive analysis
    2. Technical architecture planning
    3. Risk assessment and compliance considerations
    4. Business strategy and go-to-market plan
    5. Documentation and presentations for investors
    
    Please use your full capabilities - planning, research, file management, and sub-agent delegation - 
    to create a complete startup preparation package. Document everything properly and provide a 
    comprehensive final report.
    """
    
    try:
        result = await agent.run(integrated_request)
        print("✅ Integrated workflow completed!")
        print(result)
        
        # Show comprehensive results
        print("\n📊 Workflow Summary:")
        print(f"Steps executed: {agent.current_step}")
        print(f"Messages in memory: {len(agent.memory.messages)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integrated workflow failed: {e}")
        return False


async def save_test_traces(test_name: str):
    """Save trace data for analysis."""
    print(f"\n💾 Saving trace data for {test_name}...")
    
    try:
        trace_manager = get_trace_manager()
        query_engine = TraceQueryEngine(trace_manager.storage)
        exporter = TraceExporter(query_engine)
        
        # Create traces directory
        traces_dir = "./workdir/traces"
        if not os.path.isdir(traces_dir):
            os.makedirs(traces_dir)
        
        # Export traces to JSON
        json_data = await exporter.export_traces_to_json()
        filename = f"deep_agent_{test_name}_traces.json"
        
        with open(f"{traces_dir}/{filename}", "w", encoding="utf-8") as f:
            f.write(json_data)
        
        # Get statistics
        stats = await query_engine.get_trace_statistics()
        
        print(f"✅ Saved trace data to {filename}")
        print("📊 Trace Statistics:")
        print(f"  - Total traces: {stats.get('total_traces', 0)}")
        print(f"  - Average duration: {stats.get('avg_duration_ms', 0):.2f}ms")
        print(f"  - Error rate: {stats.get('error_rate', 0):.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to save traces: {e}")
        return False


async def run_test_suite():
    """Run the complete Deep Agent test suite."""
    print("🚀 Deep Agent Test Suite")
    print("Testing all capabilities of the Deep Agent implementation")
    print("=" * 80)
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found in environment")
        print("Please set your OpenAI API key in .env file or environment")
        print("Tests will continue but may fail without proper LLM access")
    
    # Test cases
    test_cases = [
        ("planning", test_planning_workflow),
        ("filesystem", test_filesystem_workflow),
        ("subagent", test_subagent_workflow),
        ("integrated", test_integrated_workflow)
    ]
    
    results = {}
    
    for test_name, test_func in test_cases:
        try:
            print(f"\n🎯 Running Test: {test_name.upper()}")
            success = await test_func()
            results[test_name] = success
            
            # Save traces for this test
            await save_test_traces(test_name)
            
            if success:
                print(f"✅ Test {test_name} PASSED")
            else:
                print(f"❌ Test {test_name} FAILED")
            
            # Brief pause between tests
            await asyncio.sleep(2)
            
        except KeyboardInterrupt:
            print(f"\n⏹️  Test suite interrupted during {test_name}")
            break
        except Exception as e:
            print(f"❌ Test {test_name} encountered unexpected error: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 80)
    print("🎉 Deep Agent Test Suite Results:")
    print("=" * 80)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {test_name.ljust(15)} : {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎊 All tests completed successfully!")
        print("\nDeep Agent capabilities verified:")
        print("✅ Task planning and management")
        print("✅ Virtual file system operations")
        print("✅ Sub-agent delegation and coordination")
        print("✅ Integrated multi-capability workflows")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Check logs for details.")
    
    return results


async def main():
    """Main entry point for Deep Agent testing."""
    parser = argparse.ArgumentParser(
        description="Deep Agent Test Suite - Comprehensive testing of Deep Agent capabilities"
    )
    parser.add_argument(
        "--test",
        choices=["planning", "filesystem", "subagent", "integrated", "all"],
        default="all",
        help="Specific test to run (default: all)"
    )
    parser.add_argument(
        "--save-traces",
        action="store_true",
        help="Save execution traces for analysis"
    )
    
    args = parser.parse_args()
    
    if args.test == "all":
        results = await run_test_suite()
    else:
        # Run specific test
        test_functions = {
            "planning": test_planning_workflow,
            "filesystem": test_filesystem_workflow,
            "subagent": test_subagent_workflow,
            "integrated": test_integrated_workflow
        }
        
        print(f"🎯 Running specific test: {args.test.upper()}")
        success = await test_functions[args.test]()
        
        if args.save_traces:
            await save_test_traces(args.test)
        
        results = {args.test: success}
    
    return results


if __name__ == "__main__":
    asyncio.run(main())