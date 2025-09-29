"""Service registry for managing agent services."""

import asyncio
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from myagent.logger import logger
from ..storage.models import AgentService, ServiceConfig, ServiceStatus
from ..storage.repository import ServiceRepository


class ServiceRegistry:
    """Registry for managing agent services."""
    
    def __init__(self, repository: ServiceRepository):
        self.repository = repository
        self._running_processes: Dict[str, subprocess.Popen] = {}
        self._port_allocator = PortAllocator()
    
    async def register_service(
        self,
        name: str,
        agent_factory_path: str,
        host: str = "localhost",
        port: Optional[int] = None,
        description: str = "",
        tags: Optional[Set[str]] = None,
        config: Optional[ServiceConfig] = None,
    ) -> Optional[AgentService]:
        """Register a new agent service."""
        
        # Check if service name already exists
        existing = self.repository.get_service_by_name(name)
        if existing:
            logger.error(f"Service with name '{name}' already exists")
            return None
        
        # Validate agent factory file
        agent_path = Path(agent_factory_path)
        if not agent_path.exists():
            logger.error(f"Agent factory file not found: {agent_factory_path}")
            return None
        
        # Allocate port if not specified
        if port is None:
            port = self._port_allocator.allocate_port()
            if port is None:
                logger.error("No available ports for service")
                return None
        elif not self._port_allocator.is_port_available(port):
            logger.error(f"Port {port} is not available")
            return None
        
        # Create default config if not provided
        if config is None:
            config = ServiceConfig(agent_factory_path=str(agent_path.absolute()))
        
        # Create service instance
        service = AgentService(
            name=name,
            description=description,
            host=host,
            port=port,
            endpoint=f"ws://{host}:{port}",
            tags=tags or set(),
            config=config,
        )
        
        # Save to repository
        if self.repository.save_service(service):
            self._port_allocator.reserve_port(port)
            logger.info(f"Service '{name}' registered successfully at {service.endpoint}")
            return service
        else:
            logger.error(f"Failed to save service '{name}' to repository")
            return None
    
    async def unregister_service(self, service_id: str) -> bool:
        """Unregister a service."""
        service = self.repository.get_service(service_id)
        if not service:
            logger.error(f"Service {service_id} not found")
            return False
        
        # Stop service if running
        if service.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
            await self.stop_service(service_id)
        
        # Release port
        self._port_allocator.release_port(service.port)
        
        # Delete from repository
        if self.repository.delete_service(service_id):
            logger.info(f"Service '{service.name}' unregistered successfully")
            return True
        else:
            logger.error(f"Failed to delete service '{service.name}' from repository")
            return False
    
    async def start_service(self, service_id: str) -> bool:
        """Start a service."""
        service = self.repository.get_service(service_id)
        if not service:
            logger.error(f"Service {service_id} not found")
            return False
        
        if service.status == ServiceStatus.RUNNING:
            logger.warning(f"Service '{service.name}' is already running")
            return True
        
        if service.status == ServiceStatus.STARTING:
            logger.warning(f"Service '{service.name}' is already starting")
            return True
        
        try:
            # Update status to starting
            service.status = ServiceStatus.STARTING
            service.error_message = None
            self.repository.save_service(service)
            
            # Prepare command
            agent_path = Path(service.config.agent_factory_path)
            if not agent_path.exists():
                raise FileNotFoundError(f"Agent factory file not found: {agent_path}")
            
            cmd = [
                sys.executable, "-m", "myagent.cli.server", "server",
                str(agent_path),
                "--host", service.host,
                "--port", str(service.port)
            ]
            
            # Prepare environment
            env = dict(service.config.environment)
            
            # Start process
            logger.info(f"Starting service '{service.name}' with command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            # Wait a bit to check if process started successfully
            await asyncio.sleep(2)
            
            if process.poll() is None:
                # Process is still running
                self._running_processes[service_id] = process
                service.status = ServiceStatus.RUNNING
                service.started_at = datetime.now()
                service.restart_count = 0
                logger.info(f"Service '{service.name}' started successfully")
            else:
                # Process exited
                stdout, stderr = process.communicate()
                error_msg = f"Process exited with code {process.returncode}. stderr: {stderr}"
                logger.error(f"Failed to start service '{service.name}': {error_msg}")
                service.status = ServiceStatus.ERROR
                service.error_message = error_msg
            
            self.repository.save_service(service)
            return service.status == ServiceStatus.RUNNING
            
        except Exception as e:
            logger.error(f"Error starting service '{service.name}': {e}")
            service.status = ServiceStatus.ERROR
            service.error_message = str(e)
            self.repository.save_service(service)
            return False
    
    async def stop_service(self, service_id: str) -> bool:
        """Stop a service."""
        service = self.repository.get_service(service_id)
        if not service:
            logger.error(f"Service {service_id} not found")
            return False
        
        if service.status == ServiceStatus.STOPPED:
            logger.warning(f"Service '{service.name}' is already stopped")
            return True
        
        try:
            # Update status to stopping
            service.status = ServiceStatus.STOPPING
            self.repository.save_service(service)
            
            # Kill process if exists
            process = self._running_processes.get(service_id)
            if process:
                logger.info(f"Terminating process for service '{service.name}'")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    await asyncio.wait_for(
                        asyncio.create_task(self._wait_for_process(process)),
                        timeout=10.0
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Force killing process for service '{service.name}'")
                    process.kill()
                    await asyncio.create_task(self._wait_for_process(process))
                
                del self._running_processes[service_id]
            
            # Update status to stopped
            service.status = ServiceStatus.STOPPED
            service.started_at = None
            service.error_message = None
            self.repository.save_service(service)
            
            logger.info(f"Service '{service.name}' stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping service '{service.name}': {e}")
            service.status = ServiceStatus.ERROR
            service.error_message = str(e)
            self.repository.save_service(service)
            return False
    
    async def restart_service(self, service_id: str) -> bool:
        """Restart a service."""
        service = self.repository.get_service(service_id)
        if not service:
            return False
        
        logger.info(f"Restarting service '{service.name}'")
        
        # Stop first
        if not await self.stop_service(service_id):
            return False
        
        # Wait a bit before starting
        await asyncio.sleep(1)
        
        # Start again
        success = await self.start_service(service_id)
        
        if success:
            # Increment restart count
            service = self.repository.get_service(service_id)
            if service:
                service.restart_count += 1
                self.repository.save_service(service)
        
        return success
    
    def get_service(self, service_id: str) -> Optional[AgentService]:
        """Get service by ID."""
        return self.repository.get_service(service_id)
    
    def get_service_by_name(self, name: str) -> Optional[AgentService]:
        """Get service by name."""
        return self.repository.get_service_by_name(name)
    
    def list_services(
        self,
        status: Optional[ServiceStatus] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[AgentService]:
        """List services with optional filters."""
        return self.repository.list_services(status, tags, limit, offset)
    
    def get_running_services(self) -> List[AgentService]:
        """Get all running services."""
        return self.repository.list_services(status=ServiceStatus.RUNNING)
    
    async def check_service_health(self, service_id: str) -> bool:
        """Basic health check for a service."""
        service = self.repository.get_service(service_id)
        if not service:
            return False
        
        if service.status != ServiceStatus.RUNNING:
            return False
        
        # Check if process is still running
        process = self._running_processes.get(service_id)
        if process and process.poll() is not None:
            # Process has exited
            logger.warning(f"Service '{service.name}' process has exited unexpectedly")
            service.status = ServiceStatus.ERROR
            service.error_message = "Process exited unexpectedly"
            self.repository.save_service(service)
            
            # Clean up
            del self._running_processes[service_id]
            return False
        
        return True
    
    async def _wait_for_process(self, process: subprocess.Popen):
        """Wait for process to exit asynchronously."""
        while process.poll() is None:
            await asyncio.sleep(0.1)


class PortAllocator:
    """Port allocation and management."""
    
    def __init__(self, start_port: int = 8081, end_port: int = 9000):
        self.start_port = start_port
        self.end_port = end_port
        self._reserved_ports: Set[int] = set()
    
    def allocate_port(self) -> Optional[int]:
        """Allocate an available port."""
        for port in range(self.start_port, self.end_port + 1):
            if self.is_port_available(port):
                return port
        return None
    
    def is_port_available(self, port: int) -> bool:
        """Check if port is available."""
        if port in self._reserved_ports:
            return False
        
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def reserve_port(self, port: int):
        """Reserve a port."""
        self._reserved_ports.add(port)
    
    def release_port(self, port: int):
        """Release a port."""
        self._reserved_ports.discard(port)