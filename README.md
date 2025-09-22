# myagent

`myagent` 提供了一个轻量级的工具增强 LLM agent 框架。下面的示例展示了如何结合 `create_react_agent` 与 DuckDuckGo 网络搜索工具，实现一个能够联网检索的智能体。

## 快速开始

1. 安装依赖并创建虚拟环境：

   ```bash
   uv sync
   ```

2. 复制示例环境文件并根据需要修改：

   ```bash
   cp .env.example .env
   # 编辑 .env，填入实际的 OPENAI_API_KEY 等参数
   ```

   （或直接导出临时环境变量，例如：）

   ```bash
   export OPENAI_API_KEY="your-key"
   export OPENAI_API_BASE="https://api.openai.com/v1"  # 可选
   ```

3. 运行示例：

   ```bash
   uv run python examples/web_search.py
   ```

   示例通过 [`duckduckgo-search`](https://pypi.org/project/duckduckgo-search/) 抓取 DuckDuckGo 搜索结果，再由 agent 组织输出。支持在 `.env` 或命令行中配置代理、Region 等选项，应对不同的网络环境。

## 示例工具说明

`examples/web_search.py` 中定义的 `DuckDuckGoSearchTool` 继承自 `BaseTool`，使用 `AsyncDDGS` 异步抓取搜索摘要并格式化为对话消息。通过 `create_react_agent` 将该工具注入智能体后，LLM 可以根据需要触发网络搜索，实现 LangChain 风格的 ReAct 能力。示例还展示了如何通过工具参数自定义最大返回条数、地区等行为。
