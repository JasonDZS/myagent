"""WebSocket server for MyAgent framework."""

import asyncio
import contextlib
import json
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed
from websockets.exceptions import WebSocketException
from websockets.server import WebSocketServerProtocol

from myagent.agent.base import BaseAgent
from myagent.logger import logger
from .events import AgentEvents
from .events import SystemEvents
from .events import UserEvents
from .events import create_event
from .session import AgentSession
from .state_manager import StateManager
from .utils import close_websocket_safely
from .utils import is_websocket_closed
from .utils import send_websocket_message


class AgentWebSocketServer:
    """MyAgent WebSocket server"""

    def __init__(
        self,
        agent_factory_func: Callable[[], BaseAgent],
        host: str = "localhost",
        port: int = 8080,
        state_secret_key: str = None,
    ):
        self.agent_factory_func = agent_factory_func
        self.host = host
        self.port = port
        self.sessions: dict[str, AgentSession] = {}
        self.connections: dict[str, WebSocketServerProtocol] = {}
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Initialize state manager for client-side state storage
        if state_secret_key is None:
            import secrets
            state_secret_key = secrets.token_hex(32)
            logger.warning("Generated random state secret key. For production, provide a fixed key.")
        self.state_manager = StateManager(state_secret_key)

    async def handle_connection(
        self, websocket: WebSocketServerProtocol, path: str | None = None
    ):
        """Handle new WebSocket connection"""
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket

        logger.info(f"New WebSocket connection: {connection_id}")

        try:
            # Send connection confirmation
            await self._send_event(
                websocket,
                create_event(
                    SystemEvents.CONNECTED,
                    content="Connected to MyAgent WebSocket Server",
                    metadata={"connection_id": connection_id},
                ),
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
                    )
                except Exception as e:
                    logger.error(f"Error handling message from {connection_id}: {e}")
                    await self._send_event(
                        websocket,
                        create_event(
                            SystemEvents.ERROR, content=f"Message handling error: {e!s}"
                        ),
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
            message_task = asyncio.create_task(
                self._handle_user_message(websocket, session_id, message)
            )

        elif event_type == UserEvents.RESPONSE and session_id:
            logger.info(f"Handling RESPONSE event for session {session_id}")
            await self._handle_user_response(websocket, session_id, message)

        elif event_type == UserEvents.CANCEL and session_id:
            logger.info(f"Handling CANCEL event for session {session_id}")
            await self._cancel_session(session_id)

        elif event_type == UserEvents.CANCEL_TASK and session_id:
            logger.info(f"Handling CANCEL_TASK event for session {session_id}")
            await self._handle_cancel_task(websocket, session_id, message)

        elif event_type == UserEvents.RESTART_TASK and session_id:
            logger.info(f"Handling RESTART_TASK event for session {session_id}")
            await self._handle_restart_task(websocket, session_id, message)

        elif event_type == UserEvents.CANCEL_PLAN and session_id:
            logger.info(f"Handling CANCEL_PLAN event for session {session_id}")
            await self._handle_cancel_plan(websocket, session_id, message)

        elif event_type == UserEvents.REPLAN and session_id:
            logger.info(f"Handling REPLAN event for session {session_id}")
            await self._handle_replan(websocket, session_id, message)

        elif event_type == UserEvents.RECONNECT_WITH_STATE:
            logger.info("Handling RECONNECT_WITH_STATE event")
            await self._handle_reconnect_with_state(websocket, connection_id, message)

        elif event_type == UserEvents.REQUEST_STATE and session_id:
            logger.info(f"Handling REQUEST_STATE event for session {session_id}")
            await self._handle_request_state(websocket, session_id, message)

        else:
            logger.warning(
                f"Unknown event type or missing session_id: event={event_type}, session_id={session_id}"
            )
            logger.warning(
                f"Available event types: CREATE_SESSION={UserEvents.CREATE_SESSION}, MESSAGE={UserEvents.MESSAGE}, "
                f"RESPONSE={UserEvents.RESPONSE}, CANCEL={UserEvents.CANCEL}, "
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
            # Use factory function to create Agent
            agent = self.agent_factory_func()

            # Create session
            session = AgentSession(
                session_id=session_id,
                connection_id=connection_id,
                agent=agent,
                websocket=websocket,
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
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        """Handle user message, execute Agent"""
        session = self.sessions.get(session_id)
        if not session:
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Session not found",
                ),
            )
            return

        if not session.is_active():
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Session is closed",
                ),
            )
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
            )
            return

        logger.info(
            f"Processing user message for session {session_id}: {user_input[:50]}..."
        )

        # Execute Agent asynchronously and stream results (in separate task, don't block message handling)
        try:
            await session.execute_streaming(user_input)
        except Exception as e:
            logger.error(f"Error executing agent for session {session_id}: {e}")
            try:
                await self._send_event(
                    websocket,
                    create_event(
                        AgentEvents.ERROR,
                        session_id=session_id,
                        content=f"Agent execution error: {e!s}",
                    ),
                )
            except Exception as send_error:
                logger.error(f"Failed to send error event: {send_error}")

    async def _handle_user_response(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        """Handle user response (for tool confirmation etc.)"""
        session = self.sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found for user response")
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Session not found",
                ),
            )
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
            )
            return

        response_data = message.get("content", {})

        try:
            await session.handle_user_response(step_id, response_data)
        except Exception as e:
            logger.error(
                f"Error processing user response for session {session_id}: {e}"
            )
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content=f"Error processing user response: {e!s}",
                ),
            )

    async def _handle_cancel_task(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        session = self.sessions.get(session_id)
        if not session:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Session not found"),
            )
            return
        content = message.get("content") or {}
        task_id = content.get("task_id") if isinstance(content, dict) else None
        if task_id is None:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Missing task_id for cancel_task"),
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
                )
            except Exception as e:
                await self._send_event(
                    websocket,
                    create_event(
                        AgentEvents.ERROR,
                        session_id=session_id,
                        content=f"Failed to cancel task {task_id}: {e!s}",
                    ),
                )
        else:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Agent does not support cancel_solver_task"),
            )

    async def _handle_restart_task(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        session = self.sessions.get(session_id)
        if not session:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Session not found"),
            )
            return
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
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        session = self.sessions.get(session_id)
        if not session:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Session not found"),
            )
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
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        session = self.sessions.get(session_id)
        if not session:
            await self._send_event(
                websocket,
                create_event(AgentEvents.ERROR, session_id=session_id, content="Session not found"),
            )
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

    async def _cancel_session(self, session_id: str) -> None:
        """Cancel session execution"""
        session = self.sessions.get(session_id)
        if session:
            await session.cancel()
            logger.info(f"Cancelled session {session_id}")

    async def _cleanup_connection(self, connection_id: str) -> None:
        """Clean up connection and related sessions"""
        # Remove connection
        self.connections.pop(connection_id, None)

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
        self, websocket: WebSocketServerProtocol, event: dict[str, Any]
    ) -> None:
        """Send event to client"""
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
            logger.error(f"Server error: {e}")
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

                # Send heartbeat to active connections
                for connection_id, websocket in list(self.connections.items()):
                    if not is_websocket_closed(websocket):
                        heartbeat_event = create_event(
                            SystemEvents.HEARTBEAT,
                            metadata={
                                "active_sessions": len(self.sessions),
                                "uptime": 0,  # Simplified version, can add startup time tracking later
                            },
                        )
                        success = await send_websocket_message(
                            websocket, heartbeat_event
                        )
                        if not success:
                            logger.debug(f"Heartbeat failed for {connection_id}")
                            # Connection may be disconnected, will be removed in next cleanup

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get server status"""
        active_sessions = sum(1 for s in self.sessions.values() if s.is_active())

        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "total_connections": len(self.connections),
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "server_time": datetime.now().isoformat(),
        }

    async def _handle_reconnect_with_state(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        message: dict[str, Any],
    ) -> None:
        """Handle reconnection with client-provided state."""
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
            )

        except Exception as e:
            logger.error(f"Failed to handle reconnect with state: {e}")
            await self._send_event(
                websocket,
                create_event(
                    SystemEvents.ERROR,
                    content=f"Reconnection failed: {str(e)}",
                ),
            )

    async def _handle_request_state(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        message: dict[str, Any],
    ) -> None:
        """Handle request to export current session state."""
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
            )

            logger.info(f"Exported state for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to export session state: {e}")
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content=f"Failed to export state: {str(e)}",
                ),
            )

    async def shutdown(self) -> None:
        """Gracefully shutdown server"""
        logger.info("Shutting down server...")

        # Set shutdown flag
        self.running = False

        # Close all sessions
        for session in list(self.sessions.values()):
            await session.close()

        # Close all connections
        for websocket in list(self.connections.values()):
            await close_websocket_safely(websocket)

        # Trigger shutdown event to stop server main loop
        self.shutdown_event.set()
        logger.info("Server shutdown complete")
