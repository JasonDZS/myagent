"""WebSocket proxy server for routing connections to agent services."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.server import WebSocketServerProtocol

from myagent.logger import logger
from myagent.ws.utils import is_websocket_closed
from ..core.manager import AgentManager
from ..storage.models import ConnectionStatus


class ProxyServer:
    """WebSocket proxy server that routes connections to agent services."""
    
    def __init__(
        self,
        manager: AgentManager,
        host: str = "localhost",
        port: int = 9090,
    ):
        self.manager = manager
        self.host = host
        self.port = port
        self.running = False
        self.server = None
        self._active_proxies: Dict[str, 'ConnectionProxy'] = {}
    
    async def start(self):
        """Start the proxy server."""
        if self.running:
            logger.warning("Proxy server is already running")
            return
        
        logger.info(f"Starting proxy server on {self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10,
        )
        
        self.running = True
        logger.info(f"Proxy server started on ws://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the proxy server."""
        if not self.running:
            return
        
        logger.info("Stopping proxy server...")
        self.running = False
        
        # Close all active proxies
        for proxy in list(self._active_proxies.values()):
            await proxy.close()
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("Proxy server stopped")
    
    async def handle_connection(self, websocket: WebSocketServerProtocol):
        """Handle new client connection."""
        # Extract path from websocket object for compatibility
        path = getattr(websocket, 'path', '/')
        connection_id = str(uuid.uuid4())
        client_info = self._extract_client_info(websocket, path)
        
        logger.info(f"New proxy connection: {connection_id} from {client_info['client_ip']}")
        
        try:
            # Route connection to appropriate service
            service = await self.manager.route_connection(
                client_ip=client_info['client_ip'],
                client_port=client_info['client_port'],
                user_agent=client_info.get('user_agent'),
                headers=client_info.get('headers', {}),
                query_params=client_info.get('query_params', {}),
            )
            
            if not service:
                await self._send_error(websocket, "No available services")
                return
            
            # Create proxy connection
            proxy = ConnectionProxy(
                connection_id=connection_id,
                client_websocket=websocket,
                service=service,
                manager=self.manager,
                client_info=client_info,
            )
            
            self._active_proxies[connection_id] = proxy
            
            # Start proxying
            await proxy.start()
            
        except Exception as e:
            logger.error(f"Error handling connection {connection_id}: {e}")
            await self._send_error(websocket, f"Connection error: {e}")
        finally:
            # Clean up
            if connection_id in self._active_proxies:
                del self._active_proxies[connection_id]
    
    def _extract_client_info(self, websocket: WebSocketServerProtocol, path: str) -> Dict[str, Any]:
        """Extract client information from WebSocket connection."""
        # Get client address
        client_ip, client_port = "unknown", 0
        if hasattr(websocket, 'remote_address') and websocket.remote_address:
            try:
                # Handle different remote_address formats
                addr = websocket.remote_address
                if isinstance(addr, (list, tuple)) and len(addr) >= 2:
                    client_ip, client_port = addr[0], addr[1]
                elif hasattr(addr, '__iter__'):
                    addr_list = list(addr)
                    if len(addr_list) >= 2:
                        client_ip, client_port = addr_list[0], addr_list[1]
            except (ValueError, TypeError, IndexError):
                # Fallback for any unpacking issues
                client_ip, client_port = "unknown", 0
        
        # Parse path and query parameters
        parsed_path = urlparse(path)
        query_params = {}
        if parsed_path.query:
            query_params = {k: v[0] if v else '' for k, v in parse_qs(parsed_path.query).items()}
        
        # Extract headers
        headers = {}
        if hasattr(websocket, 'request_headers'):
            headers = dict(websocket.request_headers)
        
        return {
            'client_ip': client_ip,
            'client_port': client_port,
            'path': parsed_path.path,
            'query_params': query_params,
            'headers': headers,
            'user_agent': headers.get('user-agent'),
        }
    
    async def _send_error(self, websocket: WebSocketServerProtocol, message: str):
        """Send error message to client."""
        try:
            error_msg = {
                'type': 'error',
                'message': message,
                'timestamp': datetime.now().isoformat(),
            }
            await websocket.send(json.dumps(error_msg))
        except Exception:
            pass  # Best effort


class ConnectionProxy:
    """Proxy for a single client-service connection."""
    
    def __init__(
        self,
        connection_id: str,
        client_websocket: WebSocketServerProtocol,
        service,  # AgentService
        manager: AgentManager,
        client_info: Dict[str, Any],
    ):
        self.connection_id = connection_id
        self.client_websocket = client_websocket
        self.service = service
        self.manager = manager
        self.client_info = client_info
        self.service_websocket: Optional[WebSocketServerProtocol] = None
        self.connection_info = None
        self.running = False
    
    async def start(self):
        """Start proxying between client and service."""
        try:
            # Connect to target service
            await self._connect_to_service()
            
            # Register connection
            self.connection_info = self.manager.register_connection(
                connection_id=self.connection_id,
                service=self.service,
                client_ip=self.client_info['client_ip'],
                client_port=self.client_info['client_port'],
                routing_strategy="proxy",
                user_agent=self.client_info.get('user_agent'),
            )
            
            self.running = True
            
            # Send connection success message
            await self._send_to_client({
                'type': 'system',
                'event': 'connected',
                'service': {
                    'name': self.service.name,
                    'endpoint': self.service.endpoint,
                },
                'connection_id': self.connection_id,
            })
            
            # Start bidirectional proxying
            await asyncio.gather(
                self._proxy_client_to_service(),
                self._proxy_service_to_client(),
                return_exceptions=True,
            )
            
        except Exception as e:
            logger.error(f"Proxy connection {self.connection_id} failed: {e}")
            await self._send_to_client({
                'type': 'error',
                'message': f"Proxy connection failed: {e}",
            })
        finally:
            await self.close()
    
    async def _connect_to_service(self):
        """Connect to the target service."""
        try:
            self.service_websocket = await websockets.connect(
                self.service.endpoint,
                ping_interval=20,
                ping_timeout=10,
            )
            logger.debug(f"Connected to service {self.service.name} for client {self.connection_id}")
        except Exception as e:
            raise Exception(f"Failed to connect to service {self.service.name}: {e}")
    
    async def _proxy_client_to_service(self):
        """Proxy messages from client to service."""
        try:
            async for message in self.client_websocket:
                if self.service_websocket and not is_websocket_closed(self.service_websocket):
                    await self.service_websocket.send(message)
                    
                    # Update connection activity
                    if self.connection_info:
                        self.connection_info.last_activity = datetime.now()
                        self.connection_info.message_count += 1
                        self.manager.router.update_connection_status(
                            self.connection_id, ConnectionStatus.ACTIVE
                        )
        except ConnectionClosed:
            logger.debug(f"Client {self.connection_id} disconnected")
        except Exception as e:
            logger.error(f"Error proxying client to service for {self.connection_id}: {e}")
    
    async def _proxy_service_to_client(self):
        """Proxy messages from service to client."""
        try:
            if not self.service_websocket:
                return
                
            async for message in self.service_websocket:
                if not is_websocket_closed(self.client_websocket):
                    await self.client_websocket.send(message)
                    
                    # Update connection activity
                    if self.connection_info:
                        self.connection_info.last_activity = datetime.now()
        except ConnectionClosed:
            logger.debug(f"Service {self.service.name} disconnected for client {self.connection_id}")
        except Exception as e:
            logger.error(f"Error proxying service to client for {self.connection_id}: {e}")
    
    async def _send_to_client(self, data: Dict[str, Any]):
        """Send data to client."""
        try:
            if not is_websocket_closed(self.client_websocket):
                message = json.dumps(data)
                await self.client_websocket.send(message)
        except Exception:
            pass  # Best effort
    
    async def close(self):
        """Close proxy connection."""
        if not self.running:
            return
            
        self.running = False
        
        # Unregister connection
        if self.connection_info:
            self.manager.unregister_connection(self.connection_id)
        
        # Close connections
        if self.service_websocket and not is_websocket_closed(self.service_websocket):
            await self.service_websocket.close()
        
        logger.debug(f"Proxy connection {self.connection_id} closed")