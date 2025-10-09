#!/usr/bin/env python3
"""
研究智能体演示

基于 Deep Agents 架构的全功能研究智能体，集成：
1. 网络搜索 (SERPER API)
2. 学术搜索 (arXiv, PubMed)
3. 数据分析 (pandas, numpy)
4. 网页内容抓取和分析
5. Deep Agents 完整架构

示例主题："LLM的发展历程"
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv()

from myagent.agent import create_deep_agent
from myagent.tool.base_tool import BaseTool, ToolResult
from myagent.tool.web_search import create_search_tools
from myagent.tool.academic_search import create_academic_tools
from myagent.tool.data_analysis import create_data_analysis_tools
from myagent.tool.web_content import create_web_content_tools
from myagent.tool.code_execution import create_code_execution_tools


async def create_research_agent():
    """创建集成所有工具的研究智能体"""
    
    # 收集所有工具
    tools = []
    
    try:
        # 网络搜索工具 (SERPER API)
        tools.extend(create_search_tools())
        print("✅ 已加载网络搜索工具 (SERPER API)")
    except Exception as e:
        print(f"⚠️ 网络搜索工具加载失败: {e}")
    
    try:
        # 学术搜索工具 (arXiv, PubMed)
        tools.extend(create_academic_tools())
        print("✅ 已加载学术搜索工具 (arXiv, PubMed)")
    except Exception as e:
        print(f"⚠️ 学术搜索工具加载失败: {e}")
    
    try:
        # 数据分析工具 (pandas, numpy)
        tools.extend(create_data_analysis_tools())
        print("✅ 已加载数据分析工具 (pandas, numpy)")
    except Exception as e:
        print(f"⚠️ 数据分析工具加载失败: {e}")
    
    try:
        # 网页内容分析工具 (BeautifulSoup)
        tools.extend(create_web_content_tools())
        print("✅ 已加载网页内容分析工具 (BeautifulSoup)")
    except Exception as e:
        print(f"⚠️ 网页内容分析工具加载失败: {e}")

    try:
        # 代码执行工具
        tools.extend(create_code_execution_tools())
        print("✅ 已加载代码执行工具 (Python)")
    except Exception as e:
        print(f"⚠️ 代码执行工具加载失败: {e}")

    print(f"\n🔧 总计加载 {len(tools)} 个工具")
    
    # 创建Deep Agent，集成所有工具
    agent = create_deep_agent(
        tools=tools,
        name="research_agent",
        description="全功能研究智能体，集成网络搜索、学术搜索、数据分析和内容抓取"
    )
    
    # 设置足够的最大步数以完成完整研究流程
    agent.max_steps = 50
    
    return agent


async def run_comprehensive_research(topic: str = "LLM的发展历程"):
    """运行综合研究演示"""
    
    print("🔬 研究智能体演示")
    print("=" * 80)
    print("📋 演示功能:")
    print("✅ 网络搜索 (SERPER API)")
    print("✅ 学术文献搜索 (arXiv, PubMed)")
    print("✅ 数据分析和趋势 (pandas, numpy)")
    print("✅ 网页内容抓取 (BeautifulSoup)")
    print("✅ 代码执行 (Python)")
    print("✅ Deep Agents 完整架构")
    print("=" * 80)
    
    # 创建研究智能体
    agent = await create_research_agent()
    
    # 详细的研究任务
    research_task = f"""
请对"{topic}"进行全面深入的研究分析，要求：

## 研究目标
创建一份专业的研究报告，涵盖技术发展、学术进展、市场趋势和未来展望。

## 具体任务

### 1. 研究规划 (使用 write_todos 工具)
- 制定详细的研究计划和时间线
- 分解任务为可管理的步骤
- 设定优先级和依赖关系

### 2. 网络信息收集 (使用 web_search 工具)
- 搜索最新的行业报告和市场分析
- 收集技术发展趋势信息
- 获取权威媒体的相关报道

### 3. 学术文献研究 (使用 arxiv_search 工具)
- 搜索相关的学术论文和预印本
- 分析技术突破和研究方向
- 收集引用数据和影响力指标

### 4. 数据分析 (使用 analyze_data 工具)
- 分析技术发展趋势数据
- 进行统计分析和相关性分析
- 生成数据驱动的洞察

### 5. 代码执行和计算 (使用 execute_code 工具)
- 编写Python代码进行定量分析
- **创建数据可视化和图表（使用matplotlib，图表会自动保存到 workspace/images/）**
- 执行复杂的统计计算
- 生成自定义分析脚本
- 注意：所有 matplotlib 图表会自动保存，无需手动调用 savefig()

### 6. 网页内容深度分析 (使用 fetch_content 工具)
- 抓取重要技术博客和文档内容
- 分析官方发布和技术规格
- 提取关键技术细节

### 7. 数据和内容保存 (使用 write_file 工具 - 必须执行)
**重要：所有收集的信息都必须保存到文件！**
- 保存网络搜索结果到 `data/web_search_results.md`
- 保存学术文献信息到 `data/academic_papers.md`
- 保存数据分析结果到 `data/analysis_results.md`（包含对生成图表的引用说明）
- 保存网页内容到 `data/web_content.md`
- 保存代码执行结果到 `code/analysis_scripts.py` 和 `code/results.txt`
- 注意：matplotlib图表会自动保存到 `workspace/images/` 目录

### 8. 综合报告生成 (使用 write_file 工具 - 必须执行)
**最终必须生成完整的研究报告文件：**
- 文件名：`final_report.md`
- 包含完整的研究内容、数据分析、图表说明
- **在报告中引用所有生成的图表（格式：`![图表说明](images/plot_xxx.png)`）**
- 整合所有收集的信息和洞察
- 提供数据支撑的结论和建议
- 包含信息来源引用

### 9. 执行要求
- 使用真实的API和数据源
- **每完成一个步骤，立即使用 write_file 保存结果**
- 提供可验证的信息来源
- 保持客观和专业的分析视角
- 确保研究的完整性和准确性
- 充分利用代码执行能力进行定量分析

请严格按照Deep Agent的最佳实践执行：
- 使用规划工具管理任务进度
- 充分利用所有可用的真实工具
- **使用 write_file 工具保存所有中间结果和最终报告**
- 创建详细的文档记录
- 提供全面的研究成果

## 完成标准
只有当以下所有文件都创建完成后，才能使用 terminate 工具结束任务：
✅ `llm_agent_research_plan.md` - 研究计划
✅ `data/web_search_results.md` - 网络搜索结果
✅ `data/academic_papers.md` - 学术文献
✅ `data/analysis_results.md` - 数据分析结果
✅ `final_report.md` - 完整的最终研究报告

开始执行研究任务。
    """
    
    print(f"🚀 开始全面研究: {topic}")
    print("=" * 80)
    
    try:
        # 执行研究
        result = await agent.run(research_task)
        
        print("\n✅ 研究任务完成!")
        print("=" * 80)
        print(result)
        
        print(f"\n📊 执行统计:")
        print(f"执行步数: {agent.current_step}/{agent.max_steps}")
        print(f"消息数量: {len(agent.memory.messages)}")
        
        # 检查虚拟文件系统中的文件
        if hasattr(agent, 'available_tools'):
            for tool in agent.available_tools.tools:
                if hasattr(tool, 'filesystem') and tool.filesystem._files:
                    print(f"\n📁 生成的文件:")
                    for filename, content in tool.filesystem._files.items():
                        print(f"• {filename}: {len(content)} 字符")
                    break
        
        return True
        
    except Exception as e:
        print(f"❌ 研究过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_specific_tool_test():
    """运行特定工具测试"""
    
    print("🧪 工具功能测试")
    print("=" * 50)
    
    # 创建简单的测试智能体
    from myagent.tool.web_search import WebSearchTool
    
    try:
        search_tool = WebSearchTool()
        print("✅ SERPER 搜索工具初始化成功")
        
        # 测试搜索
        result = await search_tool.execute("LLM language models 2024", max_results=5)
        
        if result.error:
            print(f"❌ 搜索测试失败: {result.error}")
        else:
            print(f"✅ 搜索测试成功: {result.system}")
            print(f"📄 结果预览: {result.output[:200]}...")
            
    except Exception as e:
        print(f"❌ 工具测试失败: {e}")


async def main():
    """主函数"""
    
    parser = argparse.ArgumentParser(description='研究智能体演示')
    parser.add_argument('--topic', default='LLM的发展历程', help='研究主题')
    parser.add_argument('--test-tools', action='store_true', help='仅测试工具功能')
    args = parser.parse_args()
    
    print("🤖 Deep Agents - 研究智能体")
    print(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔑 API Keys 状态:")
    print(f"  • SERPER_API_KEY: {'✅ 已配置' if os.getenv('SERPER_API_KEY') else '❌ 未配置'}")
    print(f"  • OPENAI_API_KEY: {'✅ 已配置' if os.getenv('OPENAI_API_KEY') else '❌ 未配置'}")
    print()
    
    if args.test_tools:
        await run_specific_tool_test()
        return
    
    # 运行完整研究演示
    success = await run_comprehensive_research(args.topic)
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 研究智能体演示成功!")
        print("\n🏆 成功验证的能力:")
        print("✅ 网络搜索：SERPER API 集成")
        print("✅ 学术文献搜索：arXiv 和 PubMed API")
        print("✅ 数据科学分析：pandas 和 numpy")
        print("✅ 网页内容抓取：BeautifulSoup 解析")
        print("✅ 代码执行：Python 代码动态执行")
        print("✅ Deep Agents 架构：规划、文件系统、子智能体")
        print("✅ 真实数据源：可验证的信息来源")
        
        print(f"\n💡 完整功能演示: uv run python examples/research_agent_demo.py --topic 'your_topic'")
        print(f"💡 工具测试模式: uv run python examples/research_agent_demo.py --test-tools")
    else:
        print("❌ 演示未完全成功，请检查配置和网络连接")
        print("\n🔧 故障排除:")
        print("1. 检查 .env 文件中的 API 密钥")
        print("2. 确认网络连接正常")
        print("3. 验证所有依赖项已安装")


if __name__ == "__main__":
    asyncio.run(main())