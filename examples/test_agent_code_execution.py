#!/usr/bin/env python3
"""测试智能体中的代码执行功能"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from myagent.middleware.deep_agent import create_deep_agent
from myagent.tool.code_execution import create_code_execution_tools


async def test_agent_with_code_execution():
    """测试智能体执行代码的能力"""

    print("🤖 测试智能体代码执行能力")
    print("=" * 80)

    # 创建包含代码执行工具的智能体
    tools = create_code_execution_tools()

    agent = create_deep_agent(
        tools=tools,
        name="code_executor",
        description="具有Python代码执行能力的智能体"
    )

    agent.max_steps = 5

    # 测试任务：使用代码执行工具进行数据分析
    task = """
请使用 execute_code 工具完成以下任务：

1. 创建一个包含以下数据的 pandas DataFrame：
   - 产品名称：['笔记本电脑', '手机', '平板', '耳机', '键盘']
   - 销量：[150, 300, 200, 450, 180]
   - 单价：[5999, 3999, 2999, 299, 199]

2. 计算：
   - 每个产品的总销售额（销量 × 单价）
   - 平均销量
   - 总销售额
   - 销量最高的产品

3. 显示完整的数据分析结果

请直接使用 execute_code 工具执行Python代码来完成这个任务。
"""

    print("📋 任务:")
    print(task)
    print("\n" + "=" * 80)
    print("🚀 开始执行...\n")

    try:
        result = await agent.run(task)

        print("\n" + "=" * 80)
        print("✅ 任务完成!")
        print("=" * 80)
        print("\n📊 执行结果:")
        print(result)

        print(f"\n📈 执行统计:")
        print(f"  • 步骤数: {agent.current_step}/{agent.max_steps}")
        print(f"  • 消息数: {len(agent.memory.messages)}")

        return True

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("🔬 智能体代码执行集成测试")
    print("=" * 80)
    print()

    success = await test_agent_with_code_execution()

    print("\n" + "=" * 80)
    if success:
        print("🎉 测试成功! 代码执行工具已成功集成到智能体中")
    else:
        print("❌ 测试失败，请检查配置")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())