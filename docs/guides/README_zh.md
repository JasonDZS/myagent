# MyAgent 使用指南

欢迎使用 MyAgent！本目录包含完整的中文使用指南，帮助您快速上手并掌握高级功能。

## 📚 指南目录

### 🚀 入门指南

#### [研究智能体快速入门](research-agent-guide_zh.md)
**推荐新手从这里开始！**

完整的研究智能体使用指南，包括：
- 环境配置和 API 密钥设置
- 简单研究示例（5 分钟上手）
- 完整研究智能体（16 个工具）
- 所有研究工具详解
- 工作空间结构说明
- 最佳实践和常见问题

**适合：** 想要快速构建研究系统的开发者

---

#### [Deep Agent 使用指南](deep-agent-guide_zh.md)
Deep Agent 中间件层完整指南，包括：
- Deep Agent vs 普通 Agent
- 任务规划能力（TODO 管理）
- 文件系统能力（持久化存储）
- 子智能体能力（任务委托）
- 实际应用场景
- 工作空间管理
- 高级功能和配置

**适合：** 需要企业级智能体能力的开发者

---

### 📖 英文原版指南

#### [Quick Start Guide](quick-start.md)
5 分钟快速入门指南（英文）
- 基础安装和配置
- 第一个智能体示例
- 核心概念讲解

#### [Installation Guide](installation.md)
详细安装说明（英文）

#### [Basic Concepts](basic-concepts.md)
基础概念介绍（英文）

---

## 🎯 根据需求选择指南

### 我想要...

#### 构建研究系统
→ 阅读 [研究智能体快速入门](research-agent-guide_zh.md)

**包含功能：**
- ✅ 网络搜索（SERPER API）
- ✅ 学术搜索（arXiv, PubMed）
- ✅ 数据分析（pandas, numpy）
- ✅ 网页抓取（BeautifulSoup）
- ✅ 代码执行 + 自动图表保存
- ✅ 文件持久化存储

---

#### 管理复杂项目
→ 阅读 [Deep Agent 使用指南](deep-agent-guide_zh.md)

**包含功能：**
- ✅ 任务规划和追踪
- ✅ 文件系统管理
- ✅ 子智能体协作
- ✅ 多步骤工作流

---

#### 快速了解基础
→ 阅读 [Quick Start Guide](quick-start.md)（英文）

**包含内容：**
- 基础安装
- 简单示例
- 核心概念

---

## 📊 功能对比

### 普通 Agent vs Deep Agent vs 研究 Agent

| 功能 | 普通 Agent | Deep Agent | 研究 Agent |
|------|-----------|-----------|-----------|
| **基础工具** | ✅ | ✅ | ✅ |
| **自定义工具** | ✅ | ✅ | ✅ |
| **任务规划** | ❌ | ✅ | ✅ |
| **文件系统** | ❌ | ✅ | ✅ |
| **子智能体** | ❌ | ✅ | ✅ |
| **网络搜索** | ❌ | ❌ | ✅ |
| **学术搜索** | ❌ | ❌ | ✅ |
| **数据分析** | ❌ | ❌ | ✅ |
| **代码执行** | ❌ | ❌ | ✅ |
| **图表自动保存** | ❌ | ❌ | ✅ |

### 工具数量统计

| 类型 | 普通 Agent | Deep Agent | 研究 Agent |
|------|-----------|-----------|-----------|
| 系统工具 | 1 | 1 | 1 |
| 规划工具 | 0 | 3 | 3 |
| 文件系统 | 0 | 4 | 4 |
| 子智能体 | 0 | 1 | 1 |
| 研究工具 | 0 | 0 | 7 |
| **总计** | **1** | **9** | **16** |

---

## 🔧 核心工具速查

### Deep Agent 工具（9个）

#### 规划工具
```python
write_todos   # 创建任务清单
read_todos    # 读取任务列表
complete_todo # 标记任务完成
```

#### 文件系统工具
```python
ls            # 列出文件
read_file     # 读取文件
write_file    # 写入文件（持久化）
edit_file     # 编辑文件
```

#### 子智能体工具
```python
create_subagent  # 创建子智能体
```

### 研究工具（7个）

#### 搜索工具
```python
web_search      # 网络搜索（SERPER）
scholar_search  # 学术搜索
arxiv_search    # arXiv 论文
pubmed_search   # PubMed 文献
```

#### 分析工具
```python
analyze_data    # 数据分析
fetch_content   # 网页抓取
execute_code    # 代码执行 + 图表自动保存
```

---

## 💡 快速示例

### 1. 创建普通智能体

```python
from myagent import create_toolcall_agent
from myagent.tool import BaseTool, ToolResult

class MyTool(BaseTool):
    name = "my_tool"
    description = "我的工具"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(output="完成")

agent = create_toolcall_agent(
    tools=[MyTool()],
    name="basic_agent"
)

result = await agent.run("执行任务")
```

### 2. 创建 Deep Agent

```python
from myagent.middleware.deep_agent import create_deep_agent

agent = create_deep_agent(
    tools=[MyTool()],  # 可选
    name="deep_agent"
)

# 自动包含 9 个 Deep Agent 工具
result = await agent.run("""
创建项目计划并保存到 plan.md
""")
```

### 3. 创建研究智能体

```python
from myagent.middleware.deep_agent import create_deep_agent
from myagent.tool.web_search import create_search_tools
from myagent.tool.academic_search import create_academic_tools
from myagent.tool.code_execution import create_code_execution_tools

tools = []
tools.extend(create_search_tools())
tools.extend(create_academic_tools())
tools.extend(create_code_execution_tools())

agent = create_deep_agent(
    tools=tools,
    name="researcher"
)

# 包含所有 16 个工具
result = await agent.run("""
研究"人工智能伦理"并生成报告
""")
```

---

## 📁 文件组织

### workspace 目录结构

```
workspace/
├── *.md                    # 文档文件
├── data/                   # 数据目录
│   ├── web_search_results.md
│   ├── academic_papers.md
│   └── analysis_results.md
├── code/                   # 代码目录
│   ├── analysis_scripts.py
│   └── results.txt
├── images/                 # 图片目录
│   └── plot_*.png          # 自动保存的图表
├── docs/                   # 文档目录
└── reports/                # 报告目录
    └── final_report.md
```

---

## 🎓 学习路径

### 初学者路径

1. **第一天**：阅读 [研究智能体快速入门](research-agent-guide_zh.md)
   - 完成环境配置
   - 运行简单研究示例
   - 理解基本概念

2. **第二天**：探索工具
   - 尝试不同的搜索工具
   - 测试代码执行功能
   - 练习文件系统操作

3. **第三天**：构建项目
   - 创建自定义研究任务
   - 使用 Deep Agent 能力
   - 生成完整报告

### 进阶路径

1. **深入 Deep Agent**：阅读 [Deep Agent 使用指南](deep-agent-guide_zh.md)
   - 掌握任务规划
   - 理解子智能体机制
   - 构建复杂工作流

2. **工具开发**：参考 [工具 API 文档](../api/tools_zh.md)
   - 创建自定义工具
   - 集成外部 API
   - 优化工具性能

3. **系统架构**：学习 [系统架构文档](../architecture/system_architecture.md)
   - 理解内部机制
   - 优化系统配置
   - 扩展框架能力

---

## 🔗 相关资源

### 文档

- **[工具 API 参考](../api/tools_zh.md)** - 所有工具的详细文档
- **[研究工作流程](../RESEARCH_AGENT_WORKFLOW.md)** - 完整流程说明
- **[系统架构](../architecture/system_architecture.md)** - 架构设计文档

### 示例代码

- **[研究智能体示例](../../examples/research_agent_demo.py)** - 完整实现
- **[WebSocket 示例](../../examples/ws_weather_agent.py)** - 实时交互
- **[网络搜索示例](../../examples/web_search.py)** - 搜索工具使用

### 社区

- **GitHub Issues** - 报告问题和建议
- **示例项目** - examples/ 目录

---

## ❓ 常见问题

### Q: 我应该从哪里开始？

**A:** 如果您想构建研究系统，从 [研究智能体快速入门](research-agent-guide_zh.md) 开始。如果您想了解 Deep Agent 能力，阅读 [Deep Agent 使用指南](deep-agent-guide_zh.md)。

### Q: 需要哪些 API 密钥？

**A:**
- **必需**: OpenAI API Key（所有智能体）
- **可选**: SERPER API Key（网络搜索功能）

### Q: 如何查看生成的文件？

**A:** 所有文件保存在项目根目录的 `workspace/` 文件夹中。

### Q: 图表会自动保存吗？

**A:** 是的！使用 `execute_code` 工具时，所有 matplotlib 图表会自动保存到 `workspace/images/` 目录。

### Q: 支持中文吗？

**A:** 完全支持！所有工具和智能体都支持中文输入和输出。

---

## 🚀 开始使用

1. 选择适合您的指南
2. 完成环境配置
3. 运行第一个示例
4. 探索高级功能
5. 构建您的应用

**祝您使用愉快！**

如有问题，请查阅相关文档或在 GitHub 提出 Issue。
