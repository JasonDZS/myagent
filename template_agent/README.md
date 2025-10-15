Template Agent (Plan & Solve)

Purpose
- Generate a report in the style of a user-provided markdown template.
- Follows the plan → solve architecture: planner proposes sections; solvers write each section; aggregator assembles the final markdown report.

Key Files
- template_agent/agents.py: Plan and solver implementations + aggregator.
- template_agent/tools.py: Tools for planning, drafting, and rendering.
- template_agent/pipeline.py: Factory to create the pipeline.
- template_agent/server.py: WebSocket server exposing the pipeline.
- template_agent/workdir: Reference templates and datasets.

Run (WebSocket)
- python -m template_agent.server --host 127.0.0.1 --port 8081
- Client messages mirror slide_agent_ws (plan/solve events). Tasks are report sections instead of slides.

Quick Test (WS)
- Start server (example): python template_agent/server.py --host 0.0.0.0 --port 8087
- In another shell: python scripts/ws_test_template_agent.py --host 127.0.0.1 --port 8087 --template "template/常规团队例会模板.md"
  - Auto-confirms the plan by default; prints key events and report path.

Run (Local example)
- python examples/plan_solve_template_report.py

Environment Variables
- TEMPLATE_WS_CONCURRENCY: Max concurrent section solvers (default 5)
- TEMPLATE_WS_BROADCAST_TASKS: Whether to broadcast tasks in plan.completed (default true)
- TEMPLATE_WS_MAX_RETRY: Retry attempts for failures (default 1)
- TEMPLATE_WS_RETRY_DELAY: Retry delay seconds (default 3.0)
- TEMPLATE_WS_REQUIRE_CONFIRM: Require plan confirmation before solving (default true)
- TEMPLATE_WS_CONFIRM_TIMEOUT: Seconds to wait for confirmation (default 600)

Inputs
- Templates: Place under template_agent/workdir/template or provide a path relative to that root.
- Data files: Place under workspace/ or template_agent/workdir/datasets and reference their relative paths.

Outputs
- Aggregator writes markdown to workspace/reports/generated_report.md and returns both path and content in aggregate_output.
