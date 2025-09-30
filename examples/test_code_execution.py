#!/usr/bin/env python3
"""测试代码执行工具"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from myagent.tool.code_execution import CodeExecutionTool


async def test_basic_execution():
    """测试基础代码执行"""
    print("测试1: 基础代码执行")
    print("=" * 50)

    tool = CodeExecutionTool()

    code = """
print("Hello from code execution!")
result = 2 + 2
print(f"2 + 2 = {result}")
result
"""

    result = await tool.execute(code)
    print(f"状态: {result.system}")
    print(f"输出:\n{result.output}")
    if result.error:
        print(f"错误: {result.error}")
    print()


async def test_data_science():
    """测试数据科学代码"""
    print("测试2: 数据科学代码")
    print("=" * 50)

    tool = CodeExecutionTool()

    code = """
import pandas as pd
import numpy as np

# 创建示例数据
data = {
    'name': ['Alice', 'Bob', 'Charlie', 'David'],
    'age': [25, 30, 35, 28],
    'score': [85, 90, 78, 92]
}

df = pd.DataFrame(data)
print("数据框:")
print(df)
print(f"\\n平均年龄: {df['age'].mean()}")
print(f"平均分数: {df['score'].mean()}")
print(f"最高分数: {df['score'].max()}")

# 统计分析
correlation = df['age'].corr(df['score'])
print(f"\\n年龄与分数相关性: {correlation:.3f}")
"""

    result = await tool.execute(code)
    print(f"状态: {result.system}")
    print(f"输出:\n{result.output}")
    if result.error:
        print(f"错误: {result.error}")
    print()


async def test_session_persistence():
    """测试会话持久化"""
    print("测试3: 会话状态持久化")
    print("=" * 50)

    tool = CodeExecutionTool()

    # 第一次执行：定义变量
    code1 = """
x = 100
y = 200
print(f"定义了变量: x={x}, y={y}")
"""

    result1 = await tool.execute(code1)
    print("第一次执行:")
    print(f"状态: {result1.system}")
    print(f"输出:\n{result1.output}\n")

    # 第二次执行：使用之前定义的变量
    code2 = """
z = x + y
print(f"使用之前的变量: x={x}, y={y}")
print(f"计算结果: z = x + y = {z}")
"""

    result2 = await tool.execute(code2)
    print("第二次执行:")
    print(f"状态: {result2.system}")
    print(f"输出:\n{result2.output}\n")


async def test_error_handling():
    """测试错误处理"""
    print("测试4: 错误处理")
    print("=" * 50)

    tool = CodeExecutionTool()

    code = """
# 这会产生一个错误
result = 1 / 0
"""

    result = await tool.execute(code)
    print(f"状态: {result.system}")
    print(f"输出: {result.output}")
    if result.error:
        print(f"错误信息:\n{result.error}")
    print()


async def main():
    """运行所有测试"""
    print("🧪 代码执行工具测试")
    print("=" * 50)
    print()

    await test_basic_execution()
    await test_data_science()
    await test_session_persistence()
    await test_error_handling()

    print("=" * 50)
    print("✅ 所有测试完成")


if __name__ == "__main__":
    asyncio.run(main())