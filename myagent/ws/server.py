"""WebSocket server for MyAgent framework."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Optional, Callable, Any
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from ..agent.base import BaseAgent
from ..logger import logger
from .session import AgentSession
from .events import create_event, UserEvents, AgentEvents, SystemEvents


class AgentWebSocketServer:
    """MyAgent WebSocket 服务器"""
    
    def __init__(self, agent_factory_func: Callable[[], BaseAgent], 
                 host: str = "localhost", port: int = 8080):
        self.agent_factory_func = agent_factory_func
        self.host = host
        self.port = port
        self.sessions: Dict[str, AgentSession] = {}
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.running = False
        
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: Optional[str] = None):
        """处理新的 WebSocket 连接"""
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket
        
        logger.info(f"New WebSocket connection: {connection_id}")
        
        try:
            # 发送连接确认
            await self._send_event(websocket, create_event(
                SystemEvents.CONNECTED,
                content="Connected to MyAgent WebSocket Server",
                metadata={"connection_id": connection_id}
            ))
            
            # 处理消息循环
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(websocket, connection_id, data)
                except json.JSONDecodeError as e:
                    await self._send_event(websocket, create_event(
                        SystemEvents.ERROR,
                        content=f"Invalid JSON: {str(e)}"
                    ))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await self._send_event(websocket, create_event(
                        SystemEvents.ERROR,
                        content=f"Message handling error: {str(e)}"
                    ))
                    
        except ConnectionClosed:
            logger.info(f"WebSocket connection closed: {connection_id}")
        except WebSocketException as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
        finally:
            await self._cleanup_connection(connection_id)
    
    async def _handle_message(self, websocket: WebSocketServerProtocol, 
                            connection_id: str, message: Dict[str, Any]):
        """处理接收到的消息"""
        event_type = message.get("event")
        session_id = message.get("session_id")
        
        logger.debug(f"Received message: {event_type} from {connection_id}")
        
        if event_type == UserEvents.CREATE_SESSION:
            await self._create_session(websocket, connection_id, message)
            
        elif event_type == UserEvents.MESSAGE and session_id:
            await self._handle_user_message(websocket, session_id, message)
            
        elif event_type == UserEvents.CANCEL and session_id:
            await self._cancel_session(session_id)
            
        else:
            await self._send_event(websocket, create_event(
                SystemEvents.ERROR,
                content=f"Unknown event type or missing session_id: {event_type}"
            ))
    
    async def _create_session(self, websocket: WebSocketServerProtocol, 
                            connection_id: str, message: Dict[str, Any]) -> None:
        """创建新的 Agent 会话"""
        session_id = str(uuid.uuid4())
        
        try:
            # 使用工厂函数创建 Agent
            agent = self.agent_factory_func()
            
            # 创建会话
            session = AgentSession(
                session_id=session_id,
                connection_id=connection_id,
                agent=agent,
                websocket=websocket
            )
            
            self.sessions[session_id] = session
            
            logger.info(f"Created session {session_id} for connection {connection_id}")
            
            # 发送会话创建确认
            await self._send_event(websocket, create_event(
                AgentEvents.SESSION_CREATED,
                session_id=session_id,
                content="会话创建成功",
                metadata={
                    "agent_name": getattr(agent, 'name', 'unknown'),
                    "connection_id": connection_id
                }
            ))
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            await self._send_event(websocket, create_event(
                SystemEvents.ERROR,
                content=f"Failed to create session: {str(e)}"
            ))
    
    async def _handle_user_message(self, websocket: WebSocketServerProtocol,
                                 session_id: str, message: Dict[str, Any]) -> None:
        """处理用户消息，执行 Agent"""
        session = self.sessions.get(session_id)
        if not session:
            await self._send_event(websocket, create_event(
                AgentEvents.ERROR,
                session_id=session_id,
                content="会话不存在"
            ))
            return
            
        if not session.is_active():
            await self._send_event(websocket, create_event(
                AgentEvents.ERROR,
                session_id=session_id,
                content="会话已关闭"
            ))
            return
            
        user_input = message.get("content", "")
        if not user_input.strip():
            await self._send_event(websocket, create_event(
                AgentEvents.ERROR,
                session_id=session_id,
                content="消息内容不能为空"
            ))
            return
            
        logger.info(f"Processing user message for session {session_id}: {user_input[:50]}...")
        
        # 异步执行 Agent 并流式推送结果
        try:
            await session.execute_streaming(user_input)
        except Exception as e:
            logger.error(f"Error executing agent for session {session_id}: {e}")
            await self._send_event(websocket, create_event(
                AgentEvents.ERROR,
                session_id=session_id,
                content=f"Agent 执行出错: {str(e)}"
            ))
    
    async def _cancel_session(self, session_id: str) -> None:
        """取消会话执行"""
        session = self.sessions.get(session_id)
        if session:
            await session.cancel()
            logger.info(f"Cancelled session {session_id}")
    
    async def _cleanup_connection(self, connection_id: str) -> None:
        """清理连接和相关会话"""
        # 移除连接
        self.connections.pop(connection_id, None)
        
        # 找到并关闭相关会话
        sessions_to_remove = []
        for session_id, session in self.sessions.items():
            if session.connection_id == connection_id:
                await session.close()
                sessions_to_remove.append(session_id)
        
        # 移除已关闭的会话
        for session_id in sessions_to_remove:
            self.sessions.pop(session_id, None)
            logger.info(f"Cleaned up session {session_id}")
        
        logger.info(f"Cleaned up connection {connection_id}")
    
    async def _send_event(self, websocket: WebSocketServerProtocol, 
                         event: Dict[str, Any]) -> None:
        """发送事件到客户端"""
        try:
            # 检查连接状态的兼容性方法
            if hasattr(websocket, 'closed'):
                is_closed = websocket.closed
            else:
                # 对于较新版本的 websockets 库
                is_closed = getattr(websocket, 'close_code', None) is not None
            
            if not is_closed:
                await websocket.send(json.dumps(event))
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
    
    async def start_server(self) -> None:
        """启动 WebSocket 服务器"""
        if self.running:
            logger.warning("Server is already running")
            return
            
        self.running = True
        logger.info(f"🚀 MyAgent WebSocket 服务启动在 ws://{self.host}:{self.port}")
        
        try:
            async with websockets.serve(
                self.handle_connection, 
                self.host, 
                self.port,
                ping_interval=30,  # 心跳间隔
                ping_timeout=10,   # 心跳超时
                max_size=1024*1024,  # 1MB 最大消息大小
                max_queue=32       # 最大队列长度
            ):
                # 启动心跳任务
                heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                try:
                    await asyncio.Future()  # 永远运行
                finally:
                    heartbeat_task.cancel()
                    
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            self.running = False
            logger.info("Server stopped")
    
    async def _heartbeat_loop(self) -> None:
        """心跳循环，定期清理无效连接"""
        while self.running:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                # 清理无效会话
                invalid_sessions = []
                for session_id, session in self.sessions.items():
                    if not session.is_active():
                        invalid_sessions.append(session_id)
                
                for session_id in invalid_sessions:
                    session = self.sessions.pop(session_id, None)
                    if session:
                        await session.close()
                        logger.info(f"Cleaned up inactive session: {session_id}")
                
                # 发送心跳给活跃连接
                for connection_id, websocket in list(self.connections.items()):
                    # 检查连接状态的兼容性方法
                    if hasattr(websocket, 'closed'):
                        is_closed = websocket.closed
                    else:
                        is_closed = getattr(websocket, 'close_code', None) is not None
                        
                    if not is_closed:
                        try:
                            await self._send_event(websocket, create_event(
                                SystemEvents.HEARTBEAT,
                                metadata={
                                    "active_sessions": len(self.sessions),
                                    "uptime": 0  # 简化版本，后续可以添加启动时间记录
                                }
                            ))
                        except Exception as e:
                            logger.debug(f"Heartbeat failed for {connection_id}: {e}")
                            # 连接可能已断开，将在下次清理时移除
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        active_sessions = sum(1 for s in self.sessions.values() if s.is_active())
        
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "total_connections": len(self.connections),
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "server_time": datetime.now().isoformat()
        }
    
    async def shutdown(self) -> None:
        """优雅关闭服务器"""
        logger.info("Shutting down server...")
        
        # 关闭所有会话
        for session in list(self.sessions.values()):
            await session.close()
        
        # 关闭所有连接
        for websocket in list(self.connections.values()):
            try:
                # 检查连接状态的兼容性方法
                if hasattr(websocket, 'closed'):
                    is_closed = websocket.closed
                else:
                    is_closed = getattr(websocket, 'close_code', None) is not None
                
                if not is_closed:
                    await websocket.close()
            except Exception as e:
                logger.debug(f"Error closing websocket: {e}")
        
        self.running = False
        logger.info("Server shutdown complete")