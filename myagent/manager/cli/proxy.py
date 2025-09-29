"""CLI for running the WebSocket proxy server."""

import asyncio
import signal
import sys

import click
from rich.console import Console

from myagent.logger import logger
from ..core.manager import AgentManager
from ..proxy.server import ProxyServer

console = Console()


@click.command()
@click.option('--host', default='localhost', help='Proxy server host')
@click.option('--port', type=int, default=9090, help='Proxy server port')
@click.option('--db-path', default='agent_manager.db', help='Database path')
@click.option('--health-interval', type=int, default=10, help='Health check interval')
def proxy(host, port, db_path, health_interval):
    """Run WebSocket proxy server."""
    
    async def _run_proxy():
        # Create manager and proxy server
        manager = AgentManager(db_path)
        proxy_server = ProxyServer(manager, host, port)
        
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
        
        try:
            # Start manager and proxy server
            await manager.start(health_check_interval=health_interval)
            await proxy_server.start()
            
            console.print("🚀 MyAgent Proxy Server started", style="green")
            console.print(f"   Proxy endpoint: ws://{host}:{port}")
            console.print(f"   Database: {db_path}")
            console.print(f"   Health check interval: {health_interval}s")
            console.print("   Press Ctrl+C to stop")
            
            # Wait for shutdown signal
            if sys.platform == 'win32':
                # On Windows, we can't use signal handlers, so just wait for KeyboardInterrupt
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    signal_handler()
            else:
                await shutdown_event.wait()
            
        except Exception as e:
            console.print(f"❌ Error running proxy server: {e}", style="red")
            raise
        finally:
            # Graceful shutdown
            console.print("🛑 Shutting down proxy server...", style="yellow")
            await proxy_server.stop()
            await manager.stop()
            console.print("✅ Proxy server stopped", style="green")
    
    try:
        asyncio.run(_run_proxy())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"❌ Fatal error: {e}", style="red")
        sys.exit(1)


if __name__ == '__main__':
    proxy()