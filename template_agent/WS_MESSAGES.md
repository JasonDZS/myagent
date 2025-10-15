Template Agent WS Protocol (Plan & Solve)

Overview
- Mirrors slide_agent_ws flow. The planner emits a section plan; solvers produce section drafts; the aggregator compiles a markdown report.

Start Session
- Send: { "event": "user.create_session" }
- Server: { "event": "agent.session_created", "session_id": "<sid>" }

Ask
- Send: { "event": "user.message", "session_id": "<sid>", "content": { "question": "请使用 template/常规团队例会模板.md 生成报告，输入数据来自 workspace/ 或 datasets/" } }

Events (typical)
- plan.start → { question }
- agent.tool_call / agent.tool_result (template listing/reading)
- plan.completed → { tasks: [SectionTask...], plan_summary }
- agent.user_confirm (if enabled) → client replies via user.response { confirmed: true | false, tasks?: [...] }
- solver.start / agent.tool_call (read_local_file) / solver.completed
- aggregate.start / aggregate.completed → { output: { sections, report: { path?, content } } }
- pipeline.completed, agent.final_answer

Task Schema (SectionTask)
- id: integer (1..N)
- title: string
- objective: string
- hints?: string[]
- required_inputs?: string[] (relative paths under workspace/ or template_agent/workdir)
- notes?: string

Solver Result Schema
- output.section: { id, title, content, tables? }

Aggregate Result
- output: { sections: [...], report: { path?: string, content: string } }

Notes
- Use read_local_file to load files from template_agent/workdir or workspace/.
- To provide uploads, write them into workspace/ on the server or expose via your own storage and reference with relative paths.

