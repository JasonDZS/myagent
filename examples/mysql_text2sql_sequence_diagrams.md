# MySQL Text-to-SQL Agent Execution Sequence Diagrams

本文档展示了 MySQL Text-to-SQL Agent 执行用户问题的完整流程序列图。

## 1. 完整执行流程

```mermaid
sequenceDiagram
    participant User
    participant Main
    participant Agent as ReActAgent
    participant TraceManager
    participant SchemaTool as MySQLSchemaTool
    participant QueryTool as MySQLQueryTool
    participant ValidateTool as MySQLValidateSQLTool
    participant MySQL as MySQL Database

    User->>Main: 用户问题 (e.g., "显示用户表的10条用户数据")
    Main->>TraceManager: 创建 TraceMetadata
    Main->>Agent: create_react_agent(tools, system_prompt)
    
    Main->>Agent: run(question)
    Agent->>TraceManager: 开始执行追踪
    
    Note over Agent: Step 1: 思考阶段
    Agent->>Agent: think() - 分析问题需求
    
    Note over Agent: Step 2: 行动阶段 - 获取表结构
    Agent->>SchemaTool: mysql_schema()
    SchemaTool->>MySQL: SHOW TABLES
    MySQL-->>SchemaTool: 返回表列表
    SchemaTool-->>Agent: 表结构信息
    
    Note over Agent: Step 3: 继续获取特定表结构
    Agent->>SchemaTool: mysql_schema(table="users")
    SchemaTool->>MySQL: SELECT column info FROM information_schema
    MySQL-->>SchemaTool: 列详细信息
    SchemaTool-->>Agent: 用户表列信息
    
    Note over Agent: Step 4: 探索性查询
    Agent->>QueryTool: mysql_query("SELECT COUNT(*) FROM users")
    QueryTool->>MySQL: 执行只读查询
    MySQL-->>QueryTool: 查询结果
    QueryTool-->>Agent: 格式化的结果表格
    
    Note over Agent: Step 5: 验证最终SQL
    Agent->>ValidateTool: mysql_validate_sql("SELECT * FROM users LIMIT 10")
    ValidateTool->>MySQL: EXPLAIN SELECT查询
    MySQL-->>ValidateTool: 执行计划
    ValidateTool-->>Agent: 验证成功 + 执行计划
    
    Agent->>TraceManager: 记录执行完成
    Agent-->>Main: 返回最终响应
    
    Main->>Main: 显示执行历史和最终SQL
    Main->>TraceManager: save_traces_to_json()
    TraceManager-->>Main: 导出追踪数据
```

## 2. Agent内部ReAct循环详细流程

```mermaid
sequenceDiagram
    participant Agent as ReActAgent
    participant Memory
    participant LLM
    participant Tools as Tool System
    participant Trace as TraceManager

    loop 每个执行步骤 (max_steps=15)
        Agent->>Trace: 开始步骤追踪
        
        Note over Agent: Think Phase
        Agent->>Agent: think() - 决策是否需要行动
        Agent->>Memory: 获取对话历史
        Agent->>LLM: 发送思考提示
        LLM-->>Agent: 返回思考结果
        
        alt 需要使用工具
            Note over Agent: Act Phase
            Agent->>Agent: act() - 选择并执行工具
            Agent->>LLM: 发送工具调用请求
            LLM-->>Agent: 返回工具调用指令
            
            Agent->>Tools: 执行指定工具
            Tools->>Trace: 工具执行追踪
            Tools-->>Agent: 工具执行结果
            
            Agent->>Memory: 更新对话记录
        else 完成任务
            Agent->>Agent: 设置状态为FINISHED
            break
        end
        
        Agent->>Trace: 记录步骤完成
        
        alt 达到最大步数
            Agent->>Agent: 强制终止
            break
        end
    end
```

## 3. MySQL工具详细交互流程

```mermaid
sequenceDiagram
    participant Agent
    participant SchemaTool as MySQLSchemaTool
    participant QueryTool as MySQLQueryTool
    participant ValidateTool as MySQLValidateSQLTool
    participant Config as MySQLConfig
    participant DB as MySQL Database

    Note over Agent: 第一阶段：了解数据库结构
    Agent->>SchemaTool: mysql_schema()
    SchemaTool->>Config: _load_mysql_config()
    Config-->>SchemaTool: 数据库连接配置
    SchemaTool->>DB: SHOW TABLES
    DB-->>SchemaTool: 表名列表
    SchemaTool-->>Agent: "Available tables:\n- users\n- orders\n..."

    Agent->>SchemaTool: mysql_schema(table="users")
    SchemaTool->>DB: SELECT FROM information_schema.columns
    DB-->>SchemaTool: 列详细信息
    SchemaTool-->>Agent: "Columns for users:\n- id (int NOT NULL PRI)\n- name (varchar(100) NOT NULL)..."

    Note over Agent: 第二阶段：探索性查询
    Agent->>QueryTool: mysql_query(sql, max_rows=20)
    QueryTool->>QueryTool: _ensure_read_only(sql) - 安全检查
    QueryTool->>DB: 执行SELECT查询
    DB-->>QueryTool: 查询结果行
    QueryTool->>QueryTool: _format_table() - 格式化输出
    QueryTool-->>Agent: 表格化查询结果

    Note over Agent: 第三阶段：最终SQL验证
    Agent->>ValidateTool: mysql_validate_sql(final_sql)
    ValidateTool->>ValidateTool: 安全检查 (只允许SELECT/WITH)
    ValidateTool->>DB: EXPLAIN SELECT查询
    DB-->>ValidateTool: 查询执行计划
    ValidateTool->>ValidateTool: 保存final_sql
    ValidateTool-->>Agent: "EXPLAIN succeeded. Execution plan:\n..."
```

## 4. 追踪系统记录流程

```mermaid
sequenceDiagram
    participant Agent
    participant TraceManager
    participant Storage as TraceStorage
    participant Exporter as TraceExporter
    participant File as JSON/MD Files

    Note over Agent: 执行开始
    Agent->>TraceManager: trace(name, request, metadata)
    TraceManager->>Storage: 创建追踪记录
    
    loop 每个步骤/工具调用
        Agent->>TraceManager: run(name, run_type, inputs)
        TraceManager->>Storage: 记录运行详情
        Note over Storage: 存储输入、输出、时间戳、错误等
        TraceManager-->>Agent: 返回运行上下文
    end
    
    Note over Agent: 执行完成
    Agent->>TraceManager: 完成追踪
    TraceManager->>Storage: 更新最终状态
    
    Note over Agent: 导出追踪数据
    Agent->>Exporter: export_traces_to_json()
    Exporter->>Storage: 查询所有追踪数据
    Storage-->>Exporter: 返回追踪记录
    Exporter->>File: 写入JSON文件
    
    Agent->>Exporter: export_trace_summary()
    Exporter->>Storage: 生成统计信息
    Exporter->>File: 写入Markdown摘要
```

## 5. 错误处理和安全机制

```mermaid
sequenceDiagram
    participant Agent
    participant Tool as MySQL Tool
    participant Safety as Security Check
    participant DB as MySQL Database

    Agent->>Tool: 执行SQL请求
    Tool->>Safety: _ensure_read_only(sql)
    
    alt SQL包含危险操作
        Safety-->>Tool: 返回错误信息
        Tool-->>Agent: ToolResult(error="Disallowed keyword detected")
    else 多语句查询
        Safety-->>Tool: 返回错误信息  
        Tool-->>Agent: ToolResult(error="Multiple statements not allowed")
    else 锁定子句
        Safety-->>Tool: 返回错误信息
        Tool-->>Agent: ToolResult(error="Row locking not permitted")
    else SQL安全
        Safety-->>Tool: 通过安全检查
        Tool->>DB: 执行查询
        
        alt 数据库错误
            DB-->>Tool: 抛出异常
            Tool-->>Agent: ToolResult(error="Query failed: ...")
        else 查询成功
            DB-->>Tool: 返回结果
            Tool->>Tool: 格式化结果 + 截断保护
            Tool-->>Agent: ToolResult(output=formatted_result)
        end
    end
```

## 主要特性说明

### 安全机制
- **只读限制**: 只允许 SELECT、SHOW、DESCRIBE、EXPLAIN、WITH 语句
- **关键词检测**: 阻止 INSERT、UPDATE、DELETE 等修改操作
- **多语句防护**: 不允许包含分号的多语句查询
- **锁定防护**: 禁止 FOR UPDATE/SHARE 子句

### 输出保护
- **行数限制**: 查询结果默认最多返回20行，最大200行
- **字符长度限制**: 输出超过2000字符时自动截断
- **EXPLAIN截断**: 执行计划输出超过1200字符时截断

### 追踪能力
- **完整记录**: 记录每个步骤、工具调用、思考过程
- **性能统计**: 计算执行时间、错误率等指标
- **多格式导出**: 支持JSON和Markdown格式的追踪数据导出

### ReAct模式
- **思考阶段**: Agent分析当前状态，决定下一步行动
- **行动阶段**: 根据需要调用相应的MySQL工具
- **循环执行**: 重复思考-行动循环直到任务完成或达到步数限制