"""CLI for running the HTTP API server."""

import asyncio
import signal
import sys

import click
from rich.console import Console

from myagent.logger import logger
from ..core.manager import AgentManager
from ..api.server import APIServer

console = Console()


@click.command()
@click.option('--host', default='0.0.0.0', help='API server host')
@click.option('--port', type=int, default=8080, help='API server port')
@click.option('--db-path', default='agent_manager.db', help='Database path')
@click.option('--health-interval', type=int, default=10, help='Health check interval')
@click.option('--proxy-port', type=int, default=None, help='Also start proxy server on this port')
def api(host, port, db_path, health_interval, proxy_port):
    """Run HTTP API server."""
    
    async def _run_api():
        # Create manager and API server
        manager = AgentManager(db_path)
        api_server = APIServer(manager)
        
        # Setup signal handling for graceful shutdown
        shutdown_event = asyncio.Event()
        
        def signal_handler():
            console.print("\n🛑 Received shutdown signal...", style="yellow")
            shutdown_event.set()
        
        # Register signal handlers
        if sys.platform != 'win32':
            loop = asyncio.get_event_loop()
            loop.add_signal_handler(signal.SIGINT, signal_handler)
            loop.add_signal_handler(signal.SIGTERM, signal_handler)
        
        # Optionally start proxy server
        proxy_server = None
        if proxy_port:
            from ..proxy.server import ProxyServer
            proxy_server = ProxyServer(manager, "localhost", proxy_port)
        
        try:
            # Start manager
            await manager.start(health_check_interval=health_interval)
            
            # Start proxy server if requested
            if proxy_server:
                await proxy_server.start()
                console.print(f"🔌 Proxy server started on ws://localhost:{proxy_port}")
            
            console.print("🚀 MyAgent API Server started", style="green")
            console.print(f"   API endpoint: http://{host}:{port}")
            console.print(f"   Documentation: http://{host}:{port}/docs")
            console.print(f"   Database: {db_path}")
            console.print(f"   Health check interval: {health_interval}s")
            if proxy_server:
                console.print(f"   WebSocket proxy: ws://localhost:{proxy_port}")
            console.print("   Press Ctrl+C to stop")
            
            # Start API server in background
            api_task = asyncio.create_task(api_server.start(host, port))
            
            # Wait for shutdown signal
            if sys.platform == 'win32':
                # On Windows, we can't use signal handlers, so just wait for KeyboardInterrupt
                try:
                    await api_task
                except KeyboardInterrupt:
                    signal_handler()
            else:
                # Wait for either the API server to finish or shutdown signal
                done, pending = await asyncio.wait(
                    [api_task, asyncio.create_task(shutdown_event.wait())],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel any pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
        except Exception as e:
            console.print(f"❌ Error running API server: {e}", style="red")
            raise
        finally:
            # Graceful shutdown
            console.print("🛑 Shutting down API server...", style="yellow")
            if proxy_server:
                await proxy_server.stop()
            await manager.stop()
            console.print("✅ API server stopped", style="green")
    
    try:
        asyncio.run(_run_api())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"❌ Fatal error: {e}", style="red")
        sys.exit(1)


if __name__ == '__main__':
    api()