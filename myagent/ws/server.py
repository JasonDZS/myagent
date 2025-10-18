"""WebSocket server for MyAgent framework."""

import asyncio
import contextlib
import json
import uuid
from collections.abc import Callable
from collections import deque
from datetime import datetime
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed
from websockets.exceptions import WebSocketException
from websockets.server import WebSocketServerProtocol

from myagent.agent.base import BaseAgent
from myagent.logger import logger
from .events import AgentEvents, SystemEvents, UserEvents, create_event
from .session import AgentSession
from .state_manager import StateManager
from .utils import close_websocket_safely, is_websocket_closed, send_websocket_message
from .outbound import OutboundChannel


class AgentWebSocketServer:
    """MyAgent WebSocket server.

    Design goals:
    - Single-writer outbound per connection (prevents concurrent sends)
    - Clear session/connection validation helpers
    - Bounded buffers for replay across reconnects
    - Defensive error handling and concise logs
    """

    def __init__(
        self,
        agent_factory_func: Callable[[], BaseAgent],
        host: str = "localhost",
        port: int = 8080,
        state_secret_key: str | None = None,
    ):
        self.agent_factory_func = agent_factory_func
        self.host = host
        self.port = port
        self.sessions: dict[str, AgentSession] = {}
        self.connections: dict[str, WebSocketServerProtocol] = {}
        self.outbounds: dict[str, OutboundChannel] = {}
        self.sequences: dict[str, int] = {}
        self.last_ack: dict[str, int] = {}
        self.buffers: dict[str, deque[tuple[int, dict[str, Any]]]] = {}
        # Per-session event history for replay across reconnects
        self.session_buffers: dict[str, deque[dict[str, Any]]] = {}
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Initialize state manager for client-side state storage
        if state_secret_key is None:
            import secrets
            state_secret_key = secrets.token_hex(32)
            logger.warning("Generated random state secret key. For production, provide a fixed key.")
        self.state_manager = StateManager(state_secret_key)
        # Optional: per-session init hook (e.g., configure env from client payload)
        self.session_init_handler: Callable[[dict[str, Any] | None], None] | None = None

    def set_session_init_handler(
        self, handler: Callable[[dict[str, Any] | None], None]
    ) -> None:
        """Register a handler invoked during session creation.

        The handler receives the message content (dict or None) from the
        user's create_session event to support per-session configuration.
        """
        self.session_init_handler = handler

    async def handle_connection(
        self, websocket: WebSocketServerProtocol, path: str | None = None
    ):
        """Handle new WebSocket connection"""
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket

        logger.info(f"New WebSocket connection: {connection_id}")

        # Create per-connection outbound channel (single-writer)
        outbound = OutboundChannel(websocket, name=f"conn-{connection_id}")
        outbound.start()
        self.outbounds[connection_id] = outbound
        # Initialize sequence tracking and buffers
        self.sequences[connection_id] = 0
        self.last_ack[connection_id] = 0
        self.buffers[connection_id] = deque(maxlen=1000)

        try:
            # Send connection confirmation
            await self._send_event(
                websocket,
                create_event(
                    SystemEvents.CONNECTED,
                    content="Connected to MyAgent WebSocket Server",
                    metadata={"connection_id": connection_id},
                ),
                connection_id=connection_id,
            )

            # Message handling loop
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(websocket, connection_id, data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error from {connection_id}: {e}")
                    await self._send_event(
                        websocket,
                        create_event(
                            SystemEvents.ERROR, content=f"Invalid JSON: {e!s}"
                        ),
                        connection_id=connection_id,
                    )
                except Exception as e:
                    logger.exception(
                        f"Error handling message from {connection_id}: {e}"
                    )
                    await self._send_event(
                        websocket,
                        create_event(
                            SystemEvents.ERROR, content=f"Message handling error: {e!s}"
                        ),
                        connection_id=connection_id,
                    )

        except ConnectionClosed:
            logger.info(f"WebSocket connection closed: {connection_id}")
        except WebSocketException as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
        finally:
            await self._cleanup_connection(connection_id)

    async def _handle_message(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        message: dict[str, Any],
    ):
        """Handle received message"""
        event_type = message.get("event")
        session_id = message.get("session_id")

        logger.debug(f"Processing message: event={event_type}, session_id={session_id}")
        if event_type == UserEvents.RESPONSE:
            logger.info(
                f"User response received: session={session_id}, step_id={message.get('step_id')}"
            )

        if event_type == UserEvents.CREATE_SESSION:
            logger.info("Handling CREATE_SESSION event")
            await self._create_session(websocket, connection_id, message)

        elif event_type == UserEvents.MESSAGE and session_id:
            logger.info(f"Handling MESSAGE event for session {session_id}")
            # Execute asynchronously, don't block message handling loop
            asyncio.create_task(
                self._handle_user_message(
                    websocket, connection_id, session_id, message
                )
            )
        
        elif event_type == UserEvents.SOLVE_TASKS and session_id:
            logger.info(f"Handling SOLVE_TASKS event for session {session_id}")
            # Execute asynchronously, don't block message handling loop
            asyncio.create_task(
                self._handle_user_solve_tasks(websocket, connection_id, session_id, message)
            )

        elif event_type == UserEvents.RESPONSE and session_id:
            logger.info(f"Handling RESPONSE event for session {session_id}")
            await self._handle_user_response(websocket, connection_id, session_id, message)

        elif event_type == UserEvents.CANCEL and session_id:
            logger.info(f"Handling CANCEL event for session {session_id}")
            await self._cancel_session(connection_id, session_id)

        elif event_type == UserEvents.CANCEL_TASK and session_id:
            logger.info(f"Handling CANCEL_TASK event for session {session_id}")
            await self._handle_cancel_task(websocket, connection_id, session_id, message)

        elif event_type == UserEvents.RESTART_TASK and session_id:
            logger.info(f"Handling RESTART_TASK event for session {session_id}")
            await self._handle_restart_task(websocket, connection_id, session_id, message)

        elif event_type == UserEvents.CANCEL_PLAN and session_id:
            logger.info(f"Handling CANCEL_PLAN event for session {session_id}")
            await self._handle_cancel_plan(websocket, connection_id, session_id, message)

        elif event_type == UserEvents.REPLAN and session_id:
            logger.info(f"Handling REPLAN event for session {session_id}")
            await self._handle_replan(websocket, connection_id, session_id, message)

        elif event_type == UserEvents.RECONNECT_WITH_STATE:
            # RECONNECT_WITH_STATE: Stateful recovery with client-provided state export
            # Use Case: Extended disconnect (60s-24h) where event buffer may be cleared
            # Workflow: Verify state signature → Create new session → Restore state → Replay events
            # See: docs/ws-protocol/stable/RECONNECT_CLARIFICATION.md for detailed flow
            logger.info("Handling RECONNECT_WITH_STATE event")
            await self._handle_reconnect_with_state(websocket, connection_id, message)

        elif event_type == UserEvents.REQUEST_STATE and session_id:
            # REQUEST_STATE: Explicit state export request (not reconnection)
            # Use Case: Client intentionally wants to save session state
            # Workflow: Verify session → Create snapshot → Sign/encrypt → Send signed_state
            # Client can later use signed_state with RECONNECT_WITH_STATE after disconnect
            # See: docs/ws-protocol/stable/RECONNECT_CLARIFICATION.md for detailed flow
            logger.info(f"Handling REQUEST_STATE event for session {session_id}")
            await self._handle_request_state(websocket, connection_id, session_id, message)

        elif event_type == UserEvents.ACK:
            # Update last acknowledged sequence for this connection
            acked = self._parse_last_seq(message.get("content"))
            prev = self.last_ack.get(connection_id, 0)
            if acked > prev:
                self.last_ack[connection_id] = acked
                # prune buffer
                buf = self.buffers.get(connection_id)
                if buf is not None:
                    while buf and buf[0][0] <= acked:
                        buf.popleft()
                logger.debug(f"ACK from {connection_id}: last_seq={acked}")
            else:
                logger.debug(f"ACK (stale) from {connection_id}: last_seq={acked}, prev={prev}")

        else:
            logger.warning(
                f"Unknown event type or missing session_id: event={event_type}, session_id={session_id}"
            )
            logger.warning(
                f"Available: CREATE_SESSION={UserEvents.CREATE_SESSION}, MESSAGE={UserEvents.MESSAGE}, "
                f"SOLVE_TASKS={UserEvents.SOLVE_TASKS}, RESPONSE={UserEvents.RESPONSE}, CANCEL={UserEvents.CANCEL}, "
                f"RECONNECT_WITH_STATE={UserEvents.RECONNECT_WITH_STATE}, REQUEST_STATE={UserEvents.REQUEST_STATE}"
            )
            await self._send_event(
                websocket,
                create_event(
                    SystemEvents.ERROR,
                    content=f"Unknown event type or missing session_id: {event_type}",
                ),
            )

    async def _create_session(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        message: dict[str, Any],
    ) -> None:
        """Create new Agent session"""
        session_id = str(uuid.uuid4())

        try:
            # Invoke optional session init handler with user-provided content
            try:
                if callable(self.session_init_handler):
                    content = None
                    if isinstance(message, dict):
                        c = message.get("content")
                        content = c if isinstance(c, dict) else None
                    self.session_init_handler(content)
            except Exception as hook_err:  # pragma: no cover - defensive
                logger.debug(f"session_init_handler error: {hook_err}")

            # Use factory function to create Agent
            agent = self.agent_factory_func()

            # Create session
            session = AgentSession(
                session_id=session_id,
                connection_id=connection_id,
                agent=agent,
                websocket=websocket,
                send_event_func=lambda ev: self._send_event(websocket, ev, connection_id=connection_id),
            )

            self.sessions[session_id] = session

            # Calculate current active session count
            active_sessions = sum(1 for s in self.sessions.values() if s.is_active())
            total_sessions = len(self.sessions)

            logger.info(
                f"Created session {session_id} for connection {connection_id} | Active sessions: {active_sessions}/{total_sessions}"
            )

            # Send session creation confirmation
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.SESSION_CREATED,
                    session_id=session_id,
                    content="Session created successfully",
                    metadata={
                        "agent_name": getattr(agent, "name", "unknown"),
                        "connection_id": connection_id,
                    },
                ),
                connection_id=connection_id,
            )

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            await self._send_event(
                websocket,
                create_event(
                    SystemEvents.ERROR, content=f"Failed to create session: {e!s}"
                ),
            )

    async def _handle_user_message(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        """Handle user message, execute Agent"""
        session = await self._require_session(
            websocket, connection_id, session_id, require_active=True
        )
        if not session:
            return

        user_input = message.get("content", "")
        if not user_input.strip():
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Message content cannot be empty",
                ),
                connection_id=connection_id,
            )
            return

        logger.info(
            f"Processing user message for session {session_id}: {user_input[:50]}..."
        )

        # Execute Agent asynchronously and stream results (in separate task, don't block message handling)
        try:
            await session.execute_streaming(user_input)
        except Exception as e:
            logger.exception(
                f"Error executing agent for session {session_id}: {e}"
            )
            try:
                await self._send_event(
                    websocket,
                    create_event(
                        AgentEvents.ERROR,
                        session_id=session_id,
                        content=f"Agent execution error: {e!s}",
                    ),
                    connection_id=connection_id,
                )
            except Exception as send_error:
                logger.error(f"Failed to send error event: {send_error}")

    async def _handle_user_solve_tasks(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        """Handle client-provided tasks to run solver directly (bypassing planner)."""
        session = await self._require_session(
            websocket, connection_id, session_id, require_active=True
        )
        if not session:
            return

        content = message.get("content") or {}
        tasks = None
        question = None
        plan_summary = None
        if isinstance(content, dict):
            tasks = content.get("tasks", None)
            question = content.get("question", None)
            plan_summary = content.get("plan_summary", None)
        else:
            tasks = content

        if tasks is None:
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Missing tasks in user.solve_tasks content",
                ),
                connection_id=connection_id,
            )
            return

        try:
            await session.execute_solve_tasks(
                tasks, question=question, plan_summary=plan_summary
            )
        except Exception as e:
            logger.exception(
                f"Error executing solve_tasks for session {session_id}: {e}"
            )
            try:
                await self._send_event(
                    websocket,
                    create_event(
                        AgentEvents.ERROR,
                        session_id=session_id,
                        content=f"solve_tasks execution error: {e!s}",
                    ),
                    connection_id=connection_id,
                )
            except Exception as send_error:
                logger.error(f"Failed to send error event: {send_error}")

    async def _handle_user_response(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        """Handle user response (for tool confirmation etc.)"""
        session = await self._require_session(
            websocket, connection_id, session_id, require_active=False
        )
        if not session:
            return

        step_id = message.get("step_id")
        if not step_id:
            logger.error(f"Missing step_id in user response for session {session_id}")
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Missing step_id in user response",
                ),
                connection_id=connection_id,
            )
            return

        response_data = message.get("content", {})

        try:
            await session.handle_user_response(step_id, response_data)
        except Exception as e:
            logger.exception(
                f"Error processing user response for session {session_id}: {e}"
            )
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content=f"Error processing user response: {e!s}",
                ),
                connection_id=connection_id,
            )

    async def _handle_cancel_task(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        session = await self._require_session(
            websocket, connection_id, session_id, require_active=False
        )
        if not session:
            return
        content = message.get("content") or {}
        task_id = content.get("task_id") if isinstance(content, dict) else None
        if task_id is None:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Missing task_id for cancel_task"),
                connection_id=connection_id,
            )
            return
        agent = session.agent
        if hasattr(agent, "cancel_solver_task"):
            try:
                ok = await agent.cancel_solver_task(task_id)  # type: ignore[attr-defined]
                await self._send_event(
                    websocket,
                    create_event(
                        SystemEvents.NOTICE,
                        session_id=session_id,
                        content=(
                            f"Cancel task request for {task_id} accepted" if ok else f"No running task {task_id} to cancel"
                        ),
                        metadata={"task_id": task_id, "action": "cancel_task", "ok": ok},
                    ),
                    connection_id=connection_id,
                )
            except Exception as e:
                await self._send_event(
                    websocket,
                    create_event(
                        AgentEvents.ERROR,
                        session_id=session_id,
                        content=f"Failed to cancel task {task_id}: {e!s}",
                    ),
                    connection_id=connection_id,
                )
        else:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Agent does not support cancel_solver_task"),
                connection_id=connection_id,
            )

    async def _handle_restart_task(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        session = await self._require_session(
            websocket, connection_id, session_id, require_active=False
        )
        if not session:
            return

        # Session validated by _require_session
        content = message.get("content") or {}
        task_id = content.get("task_id") if isinstance(content, dict) else None
        if task_id is None:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Missing task_id for restart_task"),
            )
            return
        agent = session.agent
        if hasattr(agent, "restart_solver_task"):
            try:
                ok = await agent.restart_solver_task(task_id)  # type: ignore[attr-defined]
                await self._send_event(
                    websocket,
                    create_event(
                        SystemEvents.NOTICE,
                        session_id=session_id,
                        content=f"Restart task request for {task_id} submitted",
                        metadata={"task_id": task_id, "action": "restart_task", "ok": ok},
                    ),
                )
            except Exception as e:
                await self._send_event(
                    websocket,
                    create_event(
                        AgentEvents.ERROR,
                        session_id=session_id,
                        content=f"Failed to restart task {task_id}: {e!s}",
                    ),
                )
        else:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Agent does not support restart_solver_task"),
            )

    async def _handle_cancel_plan(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        session = await self._require_session(
            websocket, connection_id, session_id, require_active=False
        )
        if not session:
            return
        agent = session.agent
        if hasattr(agent, "cancel_plan"):
            ok = await agent.cancel_plan()  # type: ignore[attr-defined]
            await self._send_event(
                websocket,
                create_event(
                    SystemEvents.NOTICE,
                    session_id=session_id,
                    content=("Plan cancellation requested" if ok else "No planning in progress"),
                    metadata={"action": "cancel_plan", "ok": ok},
                ),
            )
        else:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Agent does not support cancel_plan"),
            )

    async def _handle_replan(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        session = await self._require_session(
            websocket, connection_id, session_id, require_active=False
        )
        if not session:
            return
        agent = session.agent
        content = message.get("content") or {}
        new_question = content.get("question") if isinstance(content, dict) else None
        # If session is running, request in-run replan; otherwise start a new run
        if session.state == "running":
            if hasattr(agent, "replan"):
                ok = await agent.replan(new_question)  # type: ignore[attr-defined]
                await self._send_event(
                    websocket,
                    create_event(
                        SystemEvents.NOTICE,
                        session_id=session_id,
                        content=("Replan requested" if ok else "Replan request rejected"),
                        metadata={"action": "replan", "ok": ok, "mode": "in_run"},
                    ),
                )
            else:
                await self._send_event(
                    websocket,
                    create_event(AgentEvents.ERROR, session_id=session_id, content="Agent does not support replan"),
                )
            return

        # Session idle: start a new planning run
        question = None
        if isinstance(new_question, str) and new_question.strip():
            question = new_question.strip()
        else:
            # Try to recover last question from agent memory
            try:
                last_user_msg = (
                    agent._get_last_user_message()  # type: ignore[attr-defined]
                    if hasattr(agent, "_get_last_user_message")
                    else None
                )
                if last_user_msg and getattr(last_user_msg, "content", None):
                    question = str(last_user_msg.content)
            except Exception:
                question = None

        if not question:
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Replan requires a question when session is idle",
                ),
            )
            return

        # Launch execute_streaming without blocking the handler
        asyncio.create_task(session.execute_streaming(question))
        await self._send_event(
            websocket,
            create_event(
                SystemEvents.NOTICE,
                session_id=session_id,
                content="Replan started",
                metadata={"action": "replan", "mode": "restart", "question": question[:120]},
            ),
        )

    async def _cancel_session(self, connection_id: str, session_id: str) -> None:
        """Cancel session execution"""
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"Cancel requested for non-existent session {session_id}")
            return
        # Enforce session-connection binding
        if session.connection_id != connection_id:
            logger.warning(
                f"Session ownership mismatch for CANCEL: session={session_id} belongs to {session.connection_id}, got {connection_id}"
            )
            return
        await session.cancel()
        logger.info(f"Cancelled session {session_id}")

    async def _cleanup_connection(self, connection_id: str) -> None:
        """Clean up connection and related sessions"""
        # Remove connection
        self.connections.pop(connection_id, None)

        # Stop outbound writer and remove channel
        outbound = self.outbounds.pop(connection_id, None)
        if outbound is not None:
            with contextlib.suppress(Exception):
                await outbound.close()
        # Clear sequence state
        self.sequences.pop(connection_id, None)
        self.last_ack.pop(connection_id, None)
        self.buffers.pop(connection_id, None)

        # Find and close related sessions
        sessions_to_remove = []
        for session_id, session in self.sessions.items():
            if session.connection_id == connection_id:
                await session.close()
                sessions_to_remove.append(session_id)

        # Remove closed sessions
        for session_id in sessions_to_remove:
            self.sessions.pop(session_id, None)
            logger.info(f"Cleaned up session {session_id}")

        # Show session statistics after cleanup
        if sessions_to_remove:
            active_sessions = sum(1 for s in self.sessions.values() if s.is_active())
            total_sessions = len(self.sessions)
            logger.info(
                f"Cleaned up connection {connection_id} | Active sessions: {active_sessions}/{total_sessions}"
            )
        else:
            logger.info(f"Cleaned up connection {connection_id}")

    async def _send_event(
        self,
        websocket: WebSocketServerProtocol,
        event: dict[str, Any],
        *,
        connection_id: str | None = None,
    ) -> None:
        """Send event to client via per-connection outbound queue.

        Falls back to direct send if channel is not available.
        """
        cid = connection_id
        if cid is None:
            # Best-effort reverse lookup
            for k, v in self.connections.items():
                if v is websocket:
                    cid = k
                    break

        if cid is not None and cid in self.outbounds:
            # Assign new sequence and event_id (override if present), retain originals in metadata
            try:
                seq = self.sequences.get(cid, 0) + 1
                self.sequences[cid] = seq
                prev_seq = event.get("seq")
                prev_eid = event.get("event_id")
                event["seq"] = seq
                event["event_id"] = f"{cid}-{seq}"
                md = dict(event.get("metadata") or {})
                md["connection_id"] = cid
                if prev_seq is not None and "orig_seq" not in md:
                    md["orig_seq"] = prev_seq
                if prev_eid is not None and "orig_event_id" not in md:
                    md["orig_event_id"] = prev_eid
                event["metadata"] = md
                # Append to per-connection buffer
                buf = self.buffers.get(cid)
                if buf is not None:
                    buf.append((seq, dict(event)))
                # Append to per-session buffer for replay
                sid = event.get("session_id")
                if isinstance(sid, str) and sid:
                    sbuf = self.session_buffers.get(sid)
                    if sbuf is None:
                        sbuf = self.session_buffers[sid] = deque(maxlen=1000)
                    sbuf.append(dict(event))
            except Exception as e:
                logger.debug(f"Failed to stamp/enqueue seq/event_id: {e}")
            try:
                await self.outbounds[cid].enqueue(event)
                return
            except Exception as e:
                logger.debug(f"Outbound enqueue failed for {cid}: {e}")

        # Fallback to direct send (should be rare)
        success = await send_websocket_message(websocket, event)
        if not success:
            logger.debug(f"Failed to send event: {event.get('event', 'unknown')}")

    async def start_server(self) -> None:
        """Start WebSocket server"""
        if self.running:
            logger.warning("Server is already running")
            return

        self.running = True
        logger.info(
            f"🚀 MyAgent WebSocket server started at ws://{self.host}:{self.port} | Active sessions: 0/0"
        )

        try:
            async with websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                ping_interval=30,  # Heartbeat interval
                ping_timeout=10,  # Heartbeat timeout
                max_size=1024 * 1024,  # 1MB max message size
                max_queue=32,  # Max queue length
            ):
                # Start heartbeat task
                heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                try:
                    # Wait for shutdown event instead of running forever
                    await self.shutdown_event.wait()
                finally:
                    heartbeat_task.cancel()
                    # Wait for heartbeat task to stop completely
                    with contextlib.suppress(asyncio.CancelledError):
                        await heartbeat_task

        except Exception as e:
            logger.exception(f"Server error: {e}")
            raise
        finally:
            self.running = False
            logger.info("Server stopped")

    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop, periodically clean invalid connections"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Clean invalid sessions
                invalid_sessions = []
                for session_id, session in self.sessions.items():
                    if not session.is_active():
                        invalid_sessions.append(session_id)

                for session_id in invalid_sessions:
                    session = self.sessions.pop(session_id, None)
                    if session:
                        await session.close()
                        logger.info(f"Cleaned up inactive session: {session_id}")

                # Show session statistics after heartbeat cleanup
                if invalid_sessions:
                    active_sessions = sum(
                        1 for s in self.sessions.values() if s.is_active()
                    )
                    total_sessions = len(self.sessions)
                    logger.info(
                        f"Heartbeat cleanup completed | Active sessions: {active_sessions}/{total_sessions}"
                    )

                # Send heartbeat to active connections (via outbound channel)
                for connection_id, websocket in list(self.connections.items()):
                    if not is_websocket_closed(websocket):
                        heartbeat_event = create_event(
                            SystemEvents.HEARTBEAT,
                            metadata={
                                "active_sessions": len(self.sessions),
                                "uptime": 0,
                            },
                        )
                        await self._send_event(
                            websocket,
                            heartbeat_event,
                            connection_id=connection_id,
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get server status"""
        active_sessions = sum(1 for s in self.sessions.values() if s.is_active())

        outbound_sizes = {cid: ch.queue.qsize() for cid, ch in self.outbounds.items()}
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "total_connections": len(self.connections),
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "server_time": datetime.now().isoformat(),
            "outbound_queues": outbound_sizes,
            "last_seq": self.sequences.copy(),
            "last_ack": self.last_ack.copy(),
        }

    async def _handle_reconnect_with_state(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        message: dict[str, Any],
    ) -> None:
        """
        Handle reconnection with client-provided state export.

        This is for extended offline periods (60s - 24h) where the event buffer
        on the server may have been cleared. The client provides a cryptographically
        signed state snapshot that was previously exported via REQUEST_STATE or
        STATE_EXPORTED event.

        Workflow:
        1. Extract signed_state from message
        2. Verify signature for authenticity (not tampered)
        3. Validate state is not expired
        4. Create NEW session with new ID (security: don't reuse old ID)
        5. Restore session state from snapshot
        6. Replay any buffered events since last_seq
        7. Send STATE_RESTORED confirmation

        Key Difference from RECONNECT:
        - RECONNECT: Resumes existing session (simple re-connection)
        - RECONNECT_WITH_STATE: Creates new session from client state (recovery)

        See: docs/ws-protocol/stable/RECONNECT_CLARIFICATION.md
        """
        try:
            signed_state = message.get("signed_state")
            if not signed_state:
                await self._send_event(
                    websocket,
                    create_event(
                        SystemEvents.ERROR,
                        content="Missing signed_state in reconnect request",
                    ),
                )
                return

            # Verify the signed state
            is_valid, state_data, error_msg = self.state_manager.verify_state(signed_state)
            if not is_valid:
                logger.warning(f"Invalid state in reconnect request: {error_msg}")
                await self._send_event(
                    websocket,
                    create_event(
                        SystemEvents.ERROR,
                        content=f"Invalid state: {error_msg}",
                    ),
                )
                return

            # Check if session is already active
            original_session_id = state_data.get("session_id")
            if original_session_id and original_session_id in self.sessions:
                await self._send_event(
                    websocket,
                    create_event(
                        AgentEvents.ERROR,
                        content="Session already active on another connection",
                    ),
                )
                return

            # Create new session with new ID
            new_session_id = str(uuid.uuid4())
            
            # Create agent using factory
            agent = self.agent_factory_func()

            # Create session
            session = AgentSession(
                session_id=new_session_id,
                connection_id=connection_id,
                agent=agent,
                websocket=websocket,
                send_event_func=lambda ev: self._send_event(websocket, ev, connection_id=connection_id),
            )

            # Restore state to session
            restore_success = self.state_manager.restore_session_from_state(session, state_data)
            if not restore_success:
                await self._send_event(
                    websocket,
                    create_event(
                        SystemEvents.ERROR,
                        content="Failed to restore session state",
                    ),
                    connection_id=connection_id,
                )
                return

            # Add session to active sessions
            self.sessions[new_session_id] = session

            # Calculate session statistics
            active_sessions = sum(1 for s in self.sessions.values() if s.is_active())
            total_sessions = len(self.sessions)

            logger.info(
                f"Restored session {new_session_id} from client state (original: {original_session_id}) "
                f"for connection {connection_id} | Active sessions: {active_sessions}/{total_sessions}"
            )

            # Send restoration confirmation
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.STATE_RESTORED,
                    session_id=new_session_id,
                    content="Session state restored successfully",
                    metadata={
                        "original_session_id": original_session_id,
                        "restored_step": state_data.get("current_step", 0),
                        "message_count": len(json.loads(state_data.get("memory_snapshot", "[]"))),
                        "agent_name": getattr(agent, "name", "unknown"),
                        "connection_id": connection_id,
                        "warnings": [] if restore_success else ["Some state restoration issues occurred"]
                    },
                ),
                connection_id=connection_id,
            )

            # Attempt differential replay after state restoration
            try:
                content = message.get("content") or {}
                last_seq = None
                last_event_id = None
                if isinstance(content, dict):
                    if "last_event_id" in content:
                        lei = content.get("last_event_id")
                        if isinstance(lei, str) and lei:
                            last_event_id = lei
                    if "last_seq" in content:
                        try:
                            last_seq = int(content.get("last_seq") or 0)
                        except Exception:
                            last_seq = None
                # Fallback to top-level fields
                if last_event_id is None:
                    lei = message.get("last_event_id")
                    if isinstance(lei, str) and lei:
                        last_event_id = lei
                if last_seq is None and message.get("last_seq") is not None:
                    try:
                        last_seq = int(message.get("last_seq"))
                    except Exception:
                        last_seq = None

                await self._replay_events_on_reconnect(
                    websocket,
                    connection_id,
                    new_session_id,
                    original_session_id,
                    last_seq=last_seq,
                    last_event_id=last_event_id,
                )
            except Exception as e:
                logger.debug(f"Replay on reconnect skipped: {e}")

        except Exception as e:
            logger.exception(f"Failed to handle reconnect with state: {e}")
            await self._send_event(
                websocket,
                create_event(
                    SystemEvents.ERROR,
                    content=f"Reconnection failed: {str(e)}",
                ),
                connection_id=connection_id,
            )

    async def _handle_request_state(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        """
        Handle explicit request to export current session state.

        This is NOT a reconnection operation. This is a client-initiated request
        to get a state snapshot for persistence (e.g., before intentionally closing
        the app). The client can later use this snapshot with RECONNECT_WITH_STATE
        to resume.

        Workflow:
        1. Verify session exists and is active
        2. Verify connection ownership (session belongs to this connection)
        3. Create state snapshot of current session
        4. Sign/encrypt the snapshot for integrity
        5. Send STATE_EXPORTED event with signed_state in metadata
        6. Client saves signed_state locally
        7. Connection remains unchanged (NOT a reconnection)

        Typical Usage Pattern:
        1. User clicks "Save Session" button
        2. Client sends REQUEST_STATE
        3. Server sends STATE_EXPORTED with signed_state
        4. Client saves signed_state to localStorage/preferences
        5. User can now close app safely
        6. Later: User reopens app
        7. Client sends RECONNECT_WITH_STATE with saved signed_state
        8. Server verifies and restores session

        Key Differences from RECONNECT_WITH_STATE:
        - REQUEST_STATE: Export request (connection active, planned operation)
        - RECONNECT_WITH_STATE: Recovery after disconnect (connection was lost)

        See: docs/ws-protocol/stable/RECONNECT_CLARIFICATION.md
        """
        try:
            session = self.sessions.get(session_id)
            if not session:
                await self._send_event(
                    websocket,
                    create_event(
                        AgentEvents.ERROR,
                        session_id=session_id,
                        content="Session not found",
                    ),
                    connection_id=connection_id,
                )
                return

            # Enforce session-connection binding
            if session.connection_id != connection_id:
                logger.warning(
                    f"Session ownership mismatch for REQUEST_STATE: session={session_id} belongs to {session.connection_id}, got {connection_id}"
                )
                await self._send_event(
                    websocket,
                    create_event(
                        AgentEvents.ERROR,
                        session_id=session_id,
                        content="Session does not belong to this connection",
                    ),
                    connection_id=connection_id,
                )
                return

            if not session.is_active():
                await self._send_event(
                    websocket,
                    create_event(
                        AgentEvents.ERROR,
                        session_id=session_id,
                        content="Session is not active",
                    ),
                    connection_id=connection_id,
                )
                return

            # Create state snapshot
            state_data = self.state_manager.create_state_snapshot(session)
            
            # Sign the state
            signed_state = self.state_manager.sign_state(state_data)

            # Send signed state to client
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.STATE_EXPORTED,
                    session_id=session_id,
                    content="Session state exported successfully",
                    metadata={
                        "signed_state": signed_state,
                        "state_size": len(json.dumps(signed_state)),
                        "message_count": len(json.loads(state_data.get("memory_snapshot", "[]"))),
                        "current_step": state_data.get("current_step", 0),
                    },
                ),
                connection_id=connection_id,
            )

            logger.info(f"Exported state for session {session_id}")

        except Exception as e:
            logger.exception(f"Failed to export session state: {e}")
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content=f"Failed to export state: {str(e)}",
                ),
                connection_id=connection_id,
            )

    async def shutdown(self) -> None:
        """Gracefully shutdown server"""
        logger.info("Shutting down server...")

        # Set shutdown flag
        self.running = False

        # Close all sessions
        for session in list(self.sessions.values()):
            await session.close()

        # Close all sessions' connections
        for websocket in list(self.connections.values()):
            await close_websocket_safely(websocket)

        # Stop all outbound writers
        for outbound in list(self.outbounds.values()):
            with contextlib.suppress(Exception):
                await outbound.close()
        self.outbounds.clear()

        # Trigger shutdown event to stop server main loop
        self.shutdown_event.set()
        logger.info("Server shutdown complete")

    async def _replay_events_on_reconnect(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        new_session_id: str,
        original_session_id: str | None,
        *,
        last_seq: int | None = None,
        last_event_id: str | None = None,
        max_replay: int = 200,
    ) -> None:
        """Replay buffered events after client reconnects with state.

        If last_event_id is provided (format: "<prev_connection_id>-<seq>"),
        only events from that connection and with seq greater than the provided
        value will be replayed. Otherwise, falls back to filtering by seq only.
        Replay events are retargeted to the new session_id and re-stamped with
        fresh seq/event_id for the new connection.
        """
        if not original_session_id:
            return
        buf = self.session_buffers.get(original_session_id)
        if not buf:
            await self._send_event(
                websocket,
                create_event(
                    SystemEvents.NOTICE,
                    session_id=new_session_id,
                    content="No buffered events available for replay",
                    metadata={"action": "replay", "count": 0},
                ),
                connection_id=connection_id,
            )
            return

        prev_cid = None
        prev_seq = None
        if isinstance(last_event_id, str) and "-" in last_event_id:
            try:
                prev_cid, prev_seq_str = last_event_id.rsplit("-", 1)
                prev_seq = int(prev_seq_str)
            except Exception:
                prev_cid, prev_seq = None, None

        candidates: list[dict[str, Any]] = []
        for ev in buf:
            try:
                if prev_cid is not None and prev_seq is not None:
                    if not str(ev.get("event_id", "")).startswith(f"{prev_cid}-"):
                        continue
                    if int(ev.get("seq") or 0) <= prev_seq:
                        continue
                elif last_seq is not None:
                    if int(ev.get("seq") or 0) <= last_seq:
                        continue
                c = dict(ev)
                c["session_id"] = new_session_id
                candidates.append(c)
            except Exception:
                continue

        if len(candidates) > max_replay:
            candidates = candidates[-max_replay:]

        for ev in candidates:
            await self._send_event(
                websocket,
                ev,
                connection_id=connection_id,
            )

        await self._send_event(
            websocket,
            create_event(
                SystemEvents.NOTICE,
                session_id=new_session_id,
                content="Replay completed",
                metadata={
                    "action": "replay",
                    "replayed": len(candidates),
                    "last_event_id": last_event_id,
                    "last_seq": last_seq,
                },
            ),
            connection_id=connection_id,
        )

    # ----------------------------
    # Helpers
    # ----------------------------
    async def _require_session(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        session_id: str,
        *,
        require_active: bool,
    ) -> AgentSession | None:
        """Ensure a session exists, belongs to the connection, and meets activity requirements.

        Sends a concise error event and returns None if validation fails.
        """
        session = self.sessions.get(session_id)
        if not session:
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Session not found",
                ),
                connection_id=connection_id,
            )
            return None

        if session.connection_id != connection_id:
            logger.warning(
                "Session ownership mismatch: session=%s belongs to %s, got %s",
                session_id,
                session.connection_id,
                connection_id,
            )
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Session does not belong to this connection",
                ),
                connection_id=connection_id,
            )
            return None

        if require_active and not session.is_active():
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Session is closed",
                ),
                connection_id=connection_id,
            )
            return None

        return session

    @staticmethod
    def _parse_last_seq(content: Any) -> int:
        """Parse last_seq from ACK content supporting dict or raw int."""
        if isinstance(content, dict):
            try:
                return int(content.get("last_seq", 0) or 0)
            except Exception:
                return 0
        try:
            return int(content or 0)
        except Exception:
            return 0
