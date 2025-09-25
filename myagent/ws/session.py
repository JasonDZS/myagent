"""WebSocket session management for MyAgent."""

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Awaitable
from websockets.server import WebSocketServerProtocol

from ..agent.base import BaseAgent
from ..schema import AgentState
from ..logger import logger
from .events import create_event, AgentEvents, SystemEvents


class AgentSession:
    """管理单个 Agent 实例的 WebSocket 会话"""
    
    def __init__(self, session_id: str, connection_id: str, 
                 agent: BaseAgent, websocket: WebSocketServerProtocol):
        self.session_id = session_id
        self.connection_id = connection_id
        self.agent = agent
        self.websocket = websocket
        self.state = "idle"
        self.created_at = datetime.now()
        self.current_task: Optional[asyncio.Task] = None
        self.step_counter = 0
        
        # 设置 agent 回调来监控执行状态
        self._setup_agent_callbacks()
        
    def _setup_agent_callbacks(self):
        """设置 Agent 执行回调"""
        original_step = getattr(self.agent, 'step', None)
        
        if original_step:
            async def wrapped_step(*args, **kwargs):
                # Set current step counter for agent to use
                setattr(self.agent, '_current_step', self.step_counter)
                
                try:
                    result = await original_step(*args, **kwargs)
                    self.step_counter += 1
                    return result
                except Exception as e:
                    # Log error but don't send event here to avoid async issues in sync context
                    logger.error(f"Agent step execution error in session {self.session_id}: {str(e)}")
                    raise
                    
            self.agent.step = wrapped_step
        
    async def execute_streaming(self, user_input: str) -> None:
        """流式执行 Agent 并实时推送状态"""
        if self.state == "running":
            await self._send_event(create_event(
                AgentEvents.ERROR,
                session_id=self.session_id,
                content="Agent 正在运行中，请稍后再试"
            ))
            return
            
        self.state = "running"
        self.step_counter = 0
        
        try:
            # 创建执行任务 (Agent will send its own thinking events with actual content)
            self.current_task = asyncio.create_task(
                self._run_agent_with_streaming(user_input)
            )
            
            await self.current_task
            
        except asyncio.CancelledError:
            await self._send_event(create_event(
                AgentEvents.INTERRUPTED,
                session_id=self.session_id,
                content="执行被取消"
            ))
        except Exception as e:
            logger.error(f"Session {self.session_id} execution error: {e}")
            await self._send_event(create_event(
                AgentEvents.ERROR,
                session_id=self.session_id,
                content=f"执行出错: {str(e)}"
            ))
        finally:
            self.state = "idle"
            self.current_task = None
    
    async def _run_agent_with_streaming(self, user_input: str) -> None:
        """运行 Agent 并流式推送状态"""
        try:
            # Reset agent state if it's finished or in error to allow reuse
            from ..schema import AgentState
            if self.agent.state in [AgentState.FINISHED, AgentState.ERROR]:
                logger.info(f"Resetting agent state from {self.agent.state} to IDLE for session {self.session_id}")
                self.agent.state = AgentState.IDLE
                self.agent.current_step = 0
                
                # Clean incomplete tool_calls messages to fix multi-turn conversation issues
                messages_before = len(self.agent.memory.messages)
                self.agent.memory.clean_incomplete_tool_calls()
                messages_after = len(self.agent.memory.messages)
                logger.info(f"Cleaned incomplete tool_calls from agent memory for session {self.session_id}: {messages_before} -> {messages_after} messages")
            
            # 监控 Agent 工具调用
            self._wrap_tool_calls()
            
            # Set WebSocket session in trace manager for streaming support
            try:
                from ..trace import get_trace_manager
                trace_manager = get_trace_manager()
                trace_manager.ws_session = self
                logger.info(f"Set WebSocket session in trace manager for streaming")
            except Exception as e:
                logger.debug(f"Could not set WebSocket session in trace manager: {e}")
            
            # 执行 Agent
            if hasattr(self.agent, 'arun'):
                result = await self.agent.arun(user_input)
            elif hasattr(self.agent, 'run'):
                # 检查 run 方法是否是协程函数
                run_method = self.agent.run(user_input)
                if asyncio.iscoroutine(run_method):
                    result = await run_method
                else:
                    # 如果不是协程，直接使用结果
                    result = run_method
            else:
                raise AttributeError("Agent has no run or arun method")
                
            # 发送最终结果 - 使用 agent.final_response 而不是 run() 的返回值
            final_content = getattr(self.agent, 'final_response', None) or str(result) if result else "执行完成"
            await self._send_event(create_event(
                AgentEvents.FINAL_ANSWER,
                session_id=self.session_id,
                content=final_content
            ))
            
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            raise
        finally:
            # Clean up WebSocket session from trace manager
            try:
                from ..trace import get_trace_manager
                trace_manager = get_trace_manager()
                if trace_manager.ws_session == self:
                    trace_manager.ws_session = None
                    logger.debug(f"Cleaned up WebSocket session from trace manager")
            except Exception as e:
                logger.debug(f"Could not clean up WebSocket session from trace manager: {e}")
            
    def _wrap_tool_calls(self):
        """包装工具调用以提供实时反馈"""
        if not hasattr(self.agent, 'available_tools'):
            logger.debug("Agent has no available_tools attribute")
            return
            
        tools = self.agent.available_tools
        
        # Setup confirmation handlers for tools that require user confirmation
        self._setup_confirmation_handlers(tools)
        
        # Check if it's a ToolCollection and wrap its execute method
        if hasattr(tools, 'execute') and hasattr(tools, 'tool_map'):
            original_execute = getattr(tools, 'execute')
            logger.info(f"Wrapping ToolCollection.execute with {len(tools.tool_map)} tools: {list(tools.tool_map.keys())}")
            
            async def wrapped_collection_execute(*, name: str, tool_input: dict = None):
                step_id = f"step_{self.step_counter}_{name}"
                self.step_counter += 1
                
                # 发送工具调用开始事件
                await self._send_event(create_event(
                    AgentEvents.TOOL_CALL,
                    session_id=self.session_id,
                    step_id=step_id,
                    content=f"调用工具: {name}",
                    metadata={
                        "tool": name,
                        "args": tool_input or {},
                        "status": "running"
                    }
                ))
                
                try:
                    result = await original_execute(name=name, tool_input=tool_input)
                    
                    # 发送工具结果事件
                    # Determine if the tool execution was successful
                    is_success = True
                    if hasattr(result, 'error') and result.error is not None:
                        is_success = False
                    elif result.__class__.__name__ == 'ToolFailure':
                        is_success = False
                        
                    await self._send_event(create_event(
                        AgentEvents.TOOL_RESULT,
                        session_id=self.session_id,
                        step_id=step_id,
                        content=str(result.output) if hasattr(result, 'output') else str(result),
                        metadata={
                            "tool": name,
                            "status": "success" if is_success else "failed",
                            "error": str(result.error) if hasattr(result, 'error') and result.error else None
                        }
                    ))
                    
                    return result
                    
                except Exception as e:
                    # 发送工具错误事件
                    await self._send_event(create_event(
                        AgentEvents.TOOL_RESULT,
                        session_id=self.session_id,
                        step_id=step_id,
                        content=f"工具执行失败: {str(e)}",
                        metadata={
                            "tool": name,
                            "status": "failed",
                            "error": str(e)
                        }
                    ))
                    raise
                    
            # Replace the ToolCollection's execute method
            setattr(tools, 'execute', wrapped_collection_execute)
            logger.info("Successfully wrapped ToolCollection.execute method")
        else:
            logger.warning(f"Unknown tools structure: {type(tools)}, cannot wrap")
    
    def _setup_confirmation_handlers(self, tools):
        """Setup confirmation handlers for tools that require user confirmation."""
        if hasattr(tools, 'tool_map'):
            # ToolCollection
            for tool_name, tool in tools.tool_map.items():
                if hasattr(tool, 'user_confirm') and tool.user_confirm:
                    tool.set_confirmation_handler(self._handle_tool_confirmation)
                    logger.info(f"Setup confirmation handler for tool: {tool_name}")
        elif hasattr(tools, '__iter__'):
            # List of tools
            for tool in tools:
                if hasattr(tool, 'user_confirm') and tool.user_confirm:
                    tool.set_confirmation_handler(self._handle_tool_confirmation)
                    logger.info(f"Setup confirmation handler for tool: {tool.name}")
        else:
            logger.debug(f"Tools structure {type(tools)} not recognized for confirmation setup")
    
    async def _handle_tool_confirmation(self, tool, kwargs):
        """Handle user confirmation for a tool execution."""
        # Use a unique UUID-based step_id to avoid conflicts with regular tool step_ids
        import uuid
        step_id = f"confirm_{uuid.uuid4().hex[:8]}_{tool.name}"
        
        logger.info(f"Requesting user confirmation for tool '{tool.name}' with step_id: {step_id}")
        
        # Send user confirmation request
        await self._send_event(create_event(
            AgentEvents.USER_CONFIRM,
            session_id=self.session_id,
            step_id=step_id,
            content=f"确认执行工具: {tool.name}",
            metadata={
                "tool_name": tool.name,
                "tool_description": tool.description,
                "tool_args": kwargs,
                "requires_confirmation": True
            }
        ))
        
        # Wait for user response
        try:
            confirmation_result = await self._wait_for_user_response(step_id)
            confirmed = confirmation_result.get("confirmed", False)
            logger.info(f"User {'confirmed' if confirmed else 'denied'} tool execution for '{tool.name}'")
            return confirmed
        except Exception as e:
            logger.error(f"Error waiting for user response for step_id {step_id}: {e}")
            return False
    
    async def _wait_for_user_response(self, step_id: str, timeout: int = 300):
        """Wait for user response with timeout."""
        if not hasattr(self, '_pending_confirmations'):
            self._pending_confirmations = {}
        
        future = asyncio.Future()
        self._pending_confirmations[step_id] = future
        
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"User confirmation timeout for step {step_id} after {timeout}s")
            return {"confirmed": False, "reason": "timeout"}
        except Exception as e:
            logger.error(f"Exception while waiting for user response for step_id {step_id}: {e}")
            return {"confirmed": False, "reason": f"error: {str(e)}"}
        finally:
            self._pending_confirmations.pop(step_id, None)
    
    async def handle_user_response(self, step_id: str, response_data: dict):
        """Handle user response for confirmations."""
        if not hasattr(self, '_pending_confirmations'):
            self._pending_confirmations = {}
        
        future = self._pending_confirmations.get(step_id)
        if future:
            if not future.done():
                future.set_result(response_data)
                logger.debug(f"User response processed for step {step_id}")
            else:
                logger.warning(f"Future for step_id {step_id} is already done")
        else:
            logger.warning(f"No pending confirmation found for step {step_id}")
            logger.warning(f"Available pending confirmations: {list(self._pending_confirmations.keys())}")
    
    async def cancel(self) -> None:
        """取消当前执行"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            
        self.state = "idle"
        
        await self._send_event(create_event(
            AgentEvents.INTERRUPTED,
            session_id=self.session_id,
            content="执行已取消"
        ))
    
    async def _send_event(self, event: Dict[str, Any]) -> None:
        """发送事件到客户端"""
        try:
            # 检查连接状态的兼容性方法
            if hasattr(self.websocket, 'closed'):
                is_closed = self.websocket.closed
            else:
                is_closed = getattr(self.websocket, 'close_code', None) is not None
            
            if not is_closed:
                await self.websocket.send(json.dumps(event))
        except Exception as e:
            logger.error(f"Failed to send event to session {self.session_id}: {e}")
    
    def is_active(self) -> bool:
        """检查会话是否仍然活跃"""
        # 如果有待处理的确认请求，认为会话仍然活跃
        if hasattr(self, '_pending_confirmations') and self._pending_confirmations:
            return True
            
        if hasattr(self.websocket, 'closed'):
            is_closed = self.websocket.closed
        else:
            is_closed = getattr(self.websocket, 'close_code', None) is not None
        return not is_closed and self.state != "closed"
    
    async def close(self) -> None:
        """关闭会话"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            
        self.state = "closed"
        
        await self._send_event(create_event(
            AgentEvents.SESSION_END,
            session_id=self.session_id,
            content="会话已关闭"
        ))