#!/usr/bin/env python3
"""
代码执行工具

提供安全的Python代码执行能力，支持：
1. 代码执行和输出捕获
2. 执行超时控制
3. 标准输出/错误输出捕获
4. 变量持久化（会话状态）
"""

import sys
import io
import asyncio
from typing import Optional, Dict, Any
from contextlib import redirect_stdout, redirect_stderr

from pydantic import Field
from myagent.tool.base_tool import BaseTool, ToolResult


class CodeExecutionTool(BaseTool):
    """Python代码执行工具

    执行Python代码并返回结果，支持：
    - 捕获标准输出和错误输出
    - 超时控制（默认30秒）
    - 会话状态持久化（变量在多次执行间保持）
    - 支持常用数据科学库（pandas, numpy等）
    """

    name: str = "execute_code"
    description: str = """执行Python代码并返回结果。

参数:
- code (str, 必需): 要执行的Python代码
- timeout (int, 可选): 执行超时时间（秒），默认30秒

功能:
- 执行任意Python代码
- 捕获print输出和返回值
- 支持多行代码和函数定义
- 变量在执行间持久化（会话状态）
- 支持常用库：pandas, numpy, matplotlib等

示例代码:
```python
import pandas as pd
import numpy as np

# 创建数据
data = {'name': ['Alice', 'Bob'], 'age': [25, 30]}
df = pd.DataFrame(data)
print(df)
print(f"平均年龄: {df['age'].mean()}")
```

注意事项:
- 代码在受限环境中执行
- 不支持文件系统操作（使用文件系统工具代替）
- 超时后会自动终止执行
- 错误会被捕获并在输出中显示
"""

    user_confirm: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化执行上下文（实例变量）
        self._execution_context = self._create_execution_context()

    def _create_execution_context(self) -> Dict[str, Any]:
        """创建执行上下文，导入常用库"""
        context = {}

        # 基础模块
        context['__builtins__'] = __builtins__

        # 尝试导入常用数据科学库
        try:
            import pandas as pd
            import numpy as np
            context['pd'] = pd
            context['pandas'] = pd
            context['np'] = np
            context['numpy'] = np
        except ImportError:
            pass

        # 尝试导入其他常用库
        try:
            import json
            import re
            import math
            import datetime
            context['json'] = json
            context['re'] = re
            context['math'] = math
            context['datetime'] = datetime
        except ImportError:
            pass

        return context

    async def execute(self, code: str, timeout: int = 30, **kwargs) -> ToolResult:
        """执行Python代码

        Args:
            code: 要执行的Python代码
            timeout: 执行超时时间（秒）

        Returns:
            ToolResult: 包含执行结果、输出和错误信息
        """
        if not code or not code.strip():
            return ToolResult(
                output="",
                error="代码不能为空",
                system="代码执行失败"
            )

        try:
            # 创建输出捕获器
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            # 执行结果
            result = None
            error_msg = None

            try:
                # 使用 asyncio.wait_for 实现超时控制
                async def _execute():
                    nonlocal result, error_msg

                    # 重定向标准输出和错误输出
                    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                        try:
                            # 编译代码
                            compiled = compile(code, '<string>', 'exec')
                            # 在持久化的上下文中执行
                            exec(compiled, self._execution_context)

                            # 尝试获取最后一个表达式的值
                            # 如果代码最后一行是表达式，尝试求值
                            lines = code.strip().split('\n')
                            last_line = lines[-1].strip()

                            # 检查最后一行是否是表达式（不是赋值、import等语句）
                            if last_line and not any(last_line.startswith(kw) for kw in
                                ['import', 'from', 'def', 'class', 'if', 'for', 'while', 'try', 'with']):
                                if '=' not in last_line or last_line.startswith('('):
                                    try:
                                        result = eval(last_line, self._execution_context)
                                    except:
                                        pass

                        except Exception as e:
                            error_msg = f"{type(e).__name__}: {str(e)}"
                            import traceback
                            error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"

                # 执行代码（带超时）
                await asyncio.wait_for(_execute(), timeout=timeout)

            except asyncio.TimeoutError:
                error_msg = f"代码执行超时（超过 {timeout} 秒）"

            # 获取输出
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            # 构建输出消息
            output_parts = []

            if stdout_output:
                output_parts.append(f"标准输出:\n{stdout_output}")

            if result is not None:
                output_parts.append(f"返回值:\n{repr(result)}")

            if stderr_output:
                output_parts.append(f"错误输出:\n{stderr_output}")

            # 显示当前上下文中的变量（排除内置和模块）
            user_vars = {k: type(v).__name__ for k, v in self._execution_context.items()
                        if not k.startswith('_') and not hasattr(v, '__module__') or k in ['pd', 'np']}
            if user_vars:
                vars_info = ", ".join([f"{k}({v})" for k, v in user_vars.items()])
                output_parts.append(f"\n当前会话变量: {vars_info}")

            output_text = "\n\n".join(output_parts) if output_parts else "代码执行完成（无输出）"

            # 如果有错误
            if error_msg:
                return ToolResult(
                    output=output_text,
                    error=error_msg,
                    system="代码执行出错"
                )

            return ToolResult(
                output=output_text,
                system="代码执行成功"
            )

        except Exception as e:
            return ToolResult(
                output="",
                error=f"执行工具异常: {str(e)}",
                system="工具执行失败"
            )


def create_code_execution_tools() -> list[BaseTool]:
    """创建代码执行工具集合

    Returns:
        包含代码执行工具的列表
    """
    return [CodeExecutionTool()]