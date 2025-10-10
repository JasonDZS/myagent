# Plan and Solve Flow Diagrams

这个文档使用 Mermaid 图表展示 Plan and Solve agent 的执行流程。

## 1. 整体状态流程图

```mermaid
stateDiagram-v2
    [*] --> IDLE
    note right of IDLE: Agent Created

    IDLE --> PLANNING
    note right of PLANNING: run(question)

    state PLANNING {
        [*] --> AnalyzeProblem
        AnalyzeProblem --> CreatePlan
        CreatePlan --> ValidatePlan
        ValidatePlan --> StorePlan
        StorePlan --> [*]

        note right of AnalyzeProblem: Receive Question
        note right of CreatePlan: Use write_todos tool
        note right of ValidatePlan: Optional validate_plan
        note right of StorePlan: Plan Ready
    }

    PLANNING --> SOLVING
    note right of SOLVING: Plan Created

    state SOLVING {
        [*] --> CheckNextTask
        CheckNextTask --> MarkInProgress
        MarkInProgress --> ExecuteTool
        ExecuteTool --> RecordResult
        RecordResult --> MarkCompleted
        MarkCompleted --> CheckNextTask
        CheckNextTask --> [*]

        note right of CheckNextTask: Get Next Pending Task
        note right of MarkInProgress: Update Status
        note right of ExecuteTool: Tool Execution
        note right of MarkCompleted: Store Output
    }

    SOLVING --> VERIFYING
    note right of VERIFYING: All Steps Complete

    state VERIFYING {
        [*] --> CheckResults
        CheckResults --> ValidateAnswer
        ValidateAnswer --> FormatResponse
        FormatResponse --> [*]

        note right of CheckResults: Review Outputs
        note right of ValidateAnswer: Verify Calculations
        note right of FormatResponse: Final Answer Ready
    }

    VERIFYING --> FINISHED
    FINISHED --> [*]
    note right of FINISHED: terminate tool
```

## 2. 任务状态转换图

```mermaid
stateDiagram-v2
    [*] --> PENDING
    note right of PENDING: Task Created in Plan

    PENDING --> IN_PROGRESS
    note left of IN_PROGRESS: Agent Starts Task

    IN_PROGRESS --> COMPLETED
    note right of COMPLETED: Task Finished Successfully

    IN_PROGRESS --> FAILED
    note right of FAILED: Task Execution Error

    FAILED --> IN_PROGRESS
    FAILED --> SKIPPED

    COMPLETED --> [*]
    SKIPPED --> [*]
```

## 3. 详细执行流程图

```mermaid
stateDiagram-v2
    [*] --> ReceiveQuestion
    ReceiveQuestion --> Step1_Plan

    state Step1_Plan {
        [*] --> Think_Plan
        Think_Plan --> Call_WriteTodos
        Call_WriteTodos --> ExecuteTool_WriteTodos
        ExecuteTool_WriteTodos --> StoreTodoList
        StoreTodoList --> [*]

        note right of Think_Plan: LLM Reasoning
        note right of Call_WriteTodos: Decide to Create Plan
        note right of StoreTodoList: Plan Stored
    }

    Step1_Plan --> Step2_Execute1

    state Step2_Execute1 {
        [*] --> Think_Execute
        Think_Execute --> UpdateStatus_Start
        UpdateStatus_Start --> SelectTool
        SelectTool --> CallTool
        CallTool --> UpdateStatus_Done
        UpdateStatus_Done --> [*]

        note right of Think_Execute: LLM Reviews Plan
        note right of UpdateStatus_Start: Mark in_progress
        note right of CallTool: Execute Tool
    }

    Step2_Execute1 --> Step3_Execute2

    state Step3_Execute2 {
        [*] --> Think_Execute2
        Think_Execute2 --> UpdateStatus_Start2
        UpdateStatus_Start2 --> SelectTool2
        SelectTool2 --> CallTool2
        CallTool2 --> UpdateStatus_Done2
        UpdateStatus_Done2 --> [*]

        note right of Think_Execute2: LLM Reviews Remaining
        note right of CallTool2: calculator
    }

    Step3_Execute2 --> StepN_ExecuteN

    state StepN_ExecuteN {
        [*] --> ExecuteRemaining
        ExecuteRemaining --> [*]
        note right of ExecuteRemaining: All Remaining Tasks
    }

    StepN_ExecuteN --> StepFinal_Verify

    state StepFinal_Verify {
        [*] --> CheckProgress
        CheckProgress --> ValidateResults
        ValidateResults --> FormatAnswer
        FormatAnswer --> CallTerminate
        CallTerminate --> [*]

        note right of CheckProgress: Review Todo List
        note right of CallTerminate: terminate tool
    }

    StepFinal_Verify --> [*]
```

## 4. 工具调用流程图

```mermaid
stateDiagram-v2
    [*] --> LLM_Think
    LLM_Think --> ToolSelection

    state ToolSelection {
        [*] --> IdentifyTool
        IdentifyTool --> ValidateParams
        ValidateParams --> [*]

        note right of IdentifyTool: Parse Tool Name
        note right of ValidateParams: Parse Arguments
    }

    ToolSelection --> CheckToolType

    state CheckToolType <<choice>>
    CheckToolType --> PlanningTool: write_todos
    CheckToolType --> DomainTool: calculator
    CheckToolType --> ValidationTool: validate_plan
    CheckToolType --> SpecialTool: terminate

    state PlanningTool {
        [*] --> ParseTodos
        ParseTodos --> ValidateFormat
        ValidateFormat --> UpdateState
        UpdateState --> FormatOutput
        FormatOutput --> [*]

        note right of ParseTodos: Parse Todo Items
        note right of UpdateState: Store Todo List
    }

    state DomainTool {
        [*] --> ParseInput
        ParseInput --> ExecuteLogic
        ExecuteLogic --> [*]

        note right of ExecuteLogic: Run Tool Logic
    }

    state ValidationTool {
        [*] --> AnalyzePlan
        AnalyzePlan --> GenerateFeedback
        GenerateFeedback --> [*]

        note right of AnalyzePlan: Review Plan Quality
    }

    state SpecialTool {
        [*] --> GenerateSummary
        GenerateSummary --> UpdateStateFinished
        UpdateStateFinished --> [*]

        note right of GenerateSummary: Create Final Summary
        note right of UpdateStateFinished: Set FINISHED
    }

    PlanningTool --> AddToMemory
    DomainTool --> AddToMemory
    ValidationTool --> AddToMemory
    SpecialTool --> AddToMemory

    AddToMemory --> NextStep
    NextStep --> [*]
```

## 5. Agent 与 LLM 交互流程

```mermaid
stateDiagram-v2
    [*] --> InitAgent
    InitAgent --> WaitInput
    WaitInput --> PrepareMessages

    state PrepareMessages {
        [*] --> AddUserMessage
        AddUserMessage --> AddSystemPrompt
        AddSystemPrompt --> AddNextStepPrompt
        AddNextStepPrompt --> [*]

        note right of AddUserMessage: Add to Memory
        note right of AddSystemPrompt: System Prompt
        note right of AddNextStepPrompt: Guide
    }

    PrepareMessages --> CallLLM

    state CallLLM {
        [*] --> FormatMessages
        FormatMessages --> SendRequest
        SendRequest --> ReceiveResponse
        ReceiveResponse --> ParseResponse
        ParseResponse --> [*]

        note right of FormatMessages: Format for API
        note right of SendRequest: Call LLM API
        note right of ParseResponse: Parse Tool Calls
    }

    CallLLM --> CheckResponse

    state CheckResponse <<choice>>
    CheckResponse --> HasToolCalls: has tools
    CheckResponse --> NoToolCalls: text only

    HasToolCalls --> ExecuteTools

    state ExecuteTools {
        [*] --> ToolLoop
        ToolLoop --> ExecuteTool
        ExecuteTool --> StoreResult
        StoreResult --> ToolLoop
        ToolLoop --> [*]

        note right of ExecuteTool: Run tool.execute
        note right of StoreResult: Add to memory
    }

    ExecuteTools --> PrepareMessages

    NoToolCalls --> CheckFinished

    state CheckFinished <<choice>>
    CheckFinished --> Complete: FINISHED
    CheckFinished --> PrepareMessages: continue

    Complete --> [*]
```

## 6. 内存管理状态图

```mermaid
stateDiagram-v2
    [*] --> EmptyMemory
    EmptyMemory --> AddUserMsg

    state AddUserMsg {
        [*] --> CreateMessage
        CreateMessage --> AppendMemory
        AppendMemory --> [*]

        note right of CreateMessage: role=user
        note right of AppendMemory: Add to messages
    }

    AddUserMsg --> AddAssistantMsg

    state AddAssistantMsg {
        [*] --> CreateAssistantMsg
        CreateAssistantMsg --> CheckToolCalls

        state CheckToolCalls <<choice>>
        CheckToolCalls --> WithTools: Yes
        CheckToolCalls --> WithoutTools: No

        WithTools --> StoreWithTools
        WithoutTools --> StoreContentOnly

        StoreWithTools --> [*]
        StoreContentOnly --> [*]

        note right of CreateAssistantMsg: role=assistant
        note right of StoreWithTools: content+tool_calls
    }

    AddAssistantMsg --> AddToolMsg

    state AddToolMsg {
        [*] --> LoopTools
        LoopTools --> CreateToolMsg
        CreateToolMsg --> SetToolCallId
        SetToolCallId --> AppendResult
        AppendResult --> LoopTools
        LoopTools --> [*]

        note right of CreateToolMsg: role=tool
        note right of SetToolCallId: Set tool_call_id
    }

    AddToolMsg --> AddAssistantMsg

    AddAssistantMsg --> FinalSummary

    state FinalSummary {
        [*] --> AddSummaryPrompt
        AddSummaryPrompt --> CallLLM
        CallLLM --> StoreSummary
        StoreSummary --> [*]

        note right of AddSummaryPrompt: Add summary request
        note right of CallLLM: Generate summary
    }

    FinalSummary --> [*]
```

## 7. 完整示例执行流程（圆形计算）

```mermaid
stateDiagram-v2
    [*] --> Start
    note right of Start: 问题：计算半径5米圆的面积和周长

    Start --> Step1

    state Step1 {
        [*] --> Think1
        Think1 --> Tool1
        Tool1 --> Result1
        Result1 --> [*]

        note right of Think1: LLM 需要创建计划
        note right of Tool1: write_todos
        note right of Result1: 4个任务已创建
    }

    Step1 --> Step2

    state Step2 {
        [*] --> Think2
        Think2 --> Update2a
        Update2a --> Tool2
        Tool2 --> Result2
        Result2 --> Update2b
        Update2b --> [*]

        note right of Think2: 开始第一个任务
        note right of Update2a: Task1 in_progress
        note right of Tool2: knowledge_lookup
        note right of Update2b: Task1 completed
    }

    Step2 --> Step3

    state Step3 {
        [*] --> Think3
        Think3 --> Update3a
        Update3a --> Tool3
        Tool3 --> Result3
        Result3 --> Update3b
        Update3b --> [*]

        note right of Think3: 计算面积
        note right of Tool3: calculator
        note right of Result3: 78.54
    }

    Step3 --> Step4

    state Step4 {
        [*] --> Think4
        Think4 --> Update4a
        Update4a --> Tool4
        Tool4 --> Result4
        Result4 --> Update4b
        Update4b --> [*]

        note right of Think4: 计算周长
        note right of Tool4: calculator
        note right of Result4: 31.42
    }

    Step4 --> Step5

    state Step5 {
        [*] --> Think5
        Think5 --> Update5a
        Update5a --> Format5
        Format5 --> Update5b
        Update5b --> Tool5
        Tool5 --> [*]

        note right of Think5: 准备最终答案
        note right of Format5: Format result
        note right of Tool5: terminate
    }

    Step5 --> End

    state End {
        [*] --> Summary
        Summary --> Final
        Final --> [*]

        note right of Summary: Generate Summary
        note right of Final: 最终答案
    }

    End --> [*]
```

## 8. Plan-Solver 双阶段架构

新版示例采用 `create_plan_solver` 将规划与求解拆分为两类 Agent，并引入可选聚合器。整体协作如下：

```mermaid
flowchart TD
    Question[用户问题] --> Planner[PlanAgent.run]
    Planner -->|调用规划工具| TaskList[任务列表]
    TaskList --> FanOut[生成求解任务]
    FanOut --> SolverA[SolverAgent #1]
    FanOut --> SolverB[SolverAgent #2]
    FanOut --> SolverN[SolverAgent #N]
    SolverA --> Drafts[提交草稿]
    SolverB --> Drafts
    SolverN --> Drafts
    Drafts --> Aggregator[聚合/产出]
    Aggregator --> Final[最终回答 & 产物]
```

- **PlanAgent** 负责读取需求、探索数据结构并产出结构化任务（例如每页 PPT 的目标与提示）。
- **SolverAgent** 针对单个任务生成成果，可根据任务特征调用不同工具。
- **Aggregator** 在所有 solver 完成后执行一次，可生成报告文件或合并文本。

## 9. `create_plan_solver` 执行时序

```mermaid
sequenceDiagram
    participant Orchestrator as Orchestrator<br/>PlanSolverPipeline
    participant Planner as PlanAgent
    participant Solvers as SolverAgent 实例
    participant Aggregator as Aggregator

    Orchestrator->>Planner: build_agent()
    Orchestrator->>Planner: run(question)
    Planner-->>Orchestrator: plan_output + tasks
    loop 每个任务（可并发）
        Orchestrator->>Solvers: build_agent(task)
        Orchestrator->>Solvers: run(task_request)
        Solvers-->>Orchestrator: solver_output + draft
    end
    Orchestrator->>Aggregator: aggregate(context, solver_results)
    Aggregator-->>Orchestrator: final_artifact
    Orchestrator-->>User: 结果汇总与文件提示
```

> `create_plan_solver` 支持通过 `concurrency` 参数控制并发度，也允许自定义 PlanAgent/SolverAgent 子类以适配不同领域任务。

## 图表说明

### 图表1：整体状态流程
- 展示了 Agent 从创建到完成的三个主要阶段
- PLANNING → SOLVING → VERIFYING

### 图表2：任务状态转换
- 展示了单个任务的状态变化
- PENDING → IN_PROGRESS → COMPLETED

### 图表3：详细执行流程
- 展示了每个步骤的详细操作
- 包括 LLM 推理、工具调用、状态更新

### 图表4：工具调用流程
- 展示了不同工具的执行逻辑
- Planning、Domain、Validation、Special 工具

### 图表5：Agent-LLM 交互
- 展示了 Agent 如何与 LLM 交互
- 消息准备、API 调用、响应处理

### 图表6：内存管理
- 展示了 Memory 中消息的添加和管理
- User、Assistant、Tool 消息的存储

### 图表7：完整示例
- 真实示例的完整执行流程
- 从问题输入到最终答案的全过程

## 使用说明

这些图表可以在支持 Mermaid 的 Markdown 渲染器中查看，例如：
- GitHub
- GitLab
- VS Code (with Mermaid extension)
- Obsidian
- Typora

或者使用在线 Mermaid 编辑器：
- https://mermaid.live/
