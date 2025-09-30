# Deep Agents 研究智能体示例

## 概述

基于 Deep Agents 架构的研究智能体演示，集成了网络搜索、学术搜索、数据分析和网页内容抓取功能。

## 主要功能

### 🔍 网络搜索
- **SERPER API 集成** - 获取最新行业信息和技术报告
- **多语言支持** - 中文、英文搜索
- **搜索类型** - 网页、新闻、学术、图片搜索

### 📚 学术搜索
- **arXiv 集成** - 搜索最新学术论文和预印本
- **PubMed 集成** - 生物医学文献搜索
- **分类筛选** - 支持按学科和时间筛选

### 📊 数据分析
- **pandas/numpy** - 真实数据统计分析
- **趋势检测** - 时间序列和趋势分析
- **相关性分析** - 数据关联性分析
- **分布分析** - 数据分布特征分析

### 🌐 网页内容抓取
- **BeautifulSoup 解析** - 智能网页内容提取
- **结构化分析** - 页面元数据和结构分析
- **链接提取** - 内部和外部链接分析

### 🏗️ Deep Agents 架构
- **任务规划** - 自动任务分解和进度跟踪
- **虚拟文件系统** - 报告生成和文档管理
- **子智能体** - 专业化任务委托

## 快速开始

### 1. 环境配置

确保已安装依赖：
```bash
uv sync
```

配置 API 密钥（`.env` 文件）：
```env
SERPER_API_KEY=your_serper_api_key
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=deepseek-chat
```

### 2. 运行演示

**完整研究演示**：
```bash
uv run python examples/research_agent_demo.py --topic "LLM发展历程"
```

**工具功能测试**：
```bash
uv run python examples/research_agent_demo.py --test-tools
```

**自定义研究主题**：
```bash
uv run python examples/research_agent_demo.py --topic "人工智能在医疗领域的应用"
```

## 使用场景

### 📈 技术研究
- 技术发展趋势分析
- 行业报告生成
- 竞品分析

### 🎓 学术研究
- 文献综述
- 研究现状分析
- 学术趋势跟踪

### 📊 市场分析
- 市场规模预测
- 行业发展分析
- 投资机会评估

### 📝 内容创作
- 深度报告写作
- 技术博客素材收集
- 行业洞察总结

## 输出结果

智能体执行完成后会生成：

1. **结构化研究报告** - Markdown 格式的完整报告
2. **数据分析图表** - 趋势分析和统计结果
3. **信息来源清单** - 可验证的数据来源
4. **执行日志** - 详细的执行步骤和进度

## 技术架构

```
研究智能体
├── 网络搜索工具 (SERPER API)
├── 学术搜索工具 (arXiv, PubMed)
├── 数据分析工具 (pandas, numpy)
├── 网页抓取工具 (BeautifulSoup)
└── Deep Agents 框架
    ├── 任务规划 (write_todos)
    ├── 虚拟文件系统 (ls, read_file, write_file)
    └── 子智能体委托 (task)
```

## 扩展开发

### 添加新工具
1. 继承 `BaseTool` 类
2. 实现 `execute` 方法
3. 在 `create_research_agent()` 中注册

### 自定义研究流程
1. 修改 `research_task` 模板
2. 调整任务分解逻辑
3. 定制输出格式

## 故障排除

### API 配置问题
- 检查 `.env` 文件中的 API 密钥
- 确认 SERPER API 余额充足
- 验证 OpenAI API 可用性

### 网络连接问题
- 确认网络连接正常
- 检查防火墙设置
- 尝试使用代理

### 依赖问题
```bash
uv add beautifulsoup4 lxml pandas numpy aiohttp
```

## 许可证

本项目基于 MIT 许可证开源。