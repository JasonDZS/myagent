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
                # 在每个步骤前发送 thinking 事件
                await self._send_event(create_event(
                    AgentEvents.THINKING,
                    session_id=self.session_id,
                    content="正在处理...",
                    metadata={"step": self.step_counter}
                ))
                
                try:
                    result = await original_step(*args, **kwargs)
                    self.step_counter += 1
                    return result
                except Exception as e:
                    await self._send_event(create_event(
                        AgentEvents.ERROR,
                        session_id=self.session_id,
                        content=f"执行出错: {str(e)}"
                    ))
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
            # 发送开始执行事件
            await self._send_event(create_event(
                AgentEvents.THINKING,
                session_id=self.session_id,
                content="开始处理您的请求...",
                metadata={"step": 0}
            ))
            
            # 创建执行任务
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
                
            # 发送最终结果
            await self._send_event(create_event(
                AgentEvents.FINAL_ANSWER,
                session_id=self.session_id,
                content=str(result) if result else "执行完成"
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
            return
            
        tools = self.agent.available_tools
        tool_dict = {}
        
        if hasattr(tools, 'tools'):
            # ToolCollection
            if isinstance(tools.tools, dict):
                tool_dict = tools.tools
            elif hasattr(tools.tools, 'items'):
                tool_dict = dict(tools.tools.items())
        elif hasattr(tools, '__iter__'):
            # List of tools
            try:
                tool_dict = {tool.name: tool for tool in tools if hasattr(tool, 'name')}
            except (TypeError, AttributeError):
                return
        else:
            return
            
        for tool_name, tool in tool_dict.items():
            original_execute = tool.execute
            
            async def wrapped_execute(*args, tool=tool, name=tool_name, **kwargs):
                step_id = f"step_{self.step_counter}_{name}"
                
                # 发送工具调用开始事件
                await self._send_event(create_event(
                    AgentEvents.TOOL_CALL,
                    session_id=self.session_id,
                    step_id=step_id,
                    content=f"调用工具: {name}",
                    metadata={
                        "tool": name,
                        "args": kwargs,
                        "status": "running"
                    }
                ))
                
                try:
                    result = await original_execute(*args, **kwargs)
                    
                    # 发送工具结果事件
                    await self._send_event(create_event(
                        AgentEvents.TOOL_RESULT,
                        session_id=self.session_id,
                        step_id=step_id,
                        content=str(result.output) if hasattr(result, 'output') else str(result),
                        metadata={
                            "tool": name,
                            "status": "success"
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
                    
            tool.execute = wrapped_execute
    
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