"""CLI for MyAgent management system."""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional, Set

import click
from rich.console import Console
from rich.table import Table
from rich.json import JSON
from rich.panel import Panel

from myagent.logger import logger
from ..core.manager import AgentManager
from ..storage.models import ServiceConfig, ServiceStatus


console = Console()


@click.group()
@click.option('--db-path', default='agent_manager.db', help='Database path')
@click.pass_context
def cli(ctx, db_path):
    """MyAgent Management CLI"""
    ctx.ensure_object(dict)
    ctx.obj['db_path'] = db_path


@cli.command()
@click.argument('name')
@click.argument('agent_factory_path')
@click.option('--host', default='localhost', help='Service host')
@click.option('--port', type=int, help='Service port (auto-allocated if not specified)')
@click.option('--description', default='', help='Service description')
@click.option('--tags', help='Comma-separated tags')
@click.option('--auto-start', is_flag=True, help='Start service after registration')
@click.option('--max-sessions', type=int, default=0, help='Maximum concurrent sessions')
@click.option('--session-timeout', type=int, default=1800, help='Session timeout in seconds')
@click.option('--auto-restart', is_flag=True, default=True, help='Enable auto-restart')
@click.option('--health-check-interval', type=int, default=10, help='Health check interval')
@click.pass_context
def register(ctx, name, agent_factory_path, host, port, description, tags, auto_start,
             max_sessions, session_timeout, auto_restart, health_check_interval):
    """Register a new agent service."""
    
    async def _register():
        manager = AgentManager(ctx.obj['db_path'])
        
        try:
            # Parse tags
            tag_set = set()
            if tags:
                tag_set = set([tag.strip() for tag in tags.split(',')])
            
            # Create config
            config = ServiceConfig(
                agent_factory_path=agent_factory_path,
                max_sessions=max_sessions,
                session_timeout=session_timeout,
                auto_restart=auto_restart,
                health_check_interval=health_check_interval,
            )
            
            # Register service
            service = await manager.register_service(
                name=name,
                agent_factory_path=agent_factory_path,
                host=host,
                port=port,
                description=description,
                tags=tag_set,
                config=config,
                auto_start=auto_start,
            )
            
            if service:
                console.print(f"✅ Service '{name}' registered successfully", style="green")
                console.print(f"   Service ID: {service.service_id}")
                console.print(f"   Endpoint: {service.endpoint}")
                if auto_start:
                    console.print(f"   Status: {service.status.value}")
            else:
                console.print(f"❌ Failed to register service '{name}'", style="red")
                sys.exit(1)
                
        finally:
            await manager.stop()
    
    asyncio.run(_register())


@cli.command()
@click.argument('service_name')
@click.pass_context
def unregister(ctx, service_name):
    """Unregister a service."""
    
    async def _unregister():
        manager = AgentManager(ctx.obj['db_path'])
        
        try:
            service = manager.get_service_by_name(service_name)
            if not service:
                console.print(f"❌ Service '{service_name}' not found", style="red")
                sys.exit(1)
            
            success = await manager.unregister_service(service.service_id)
            
            if success:
                console.print(f"✅ Service '{service_name}' unregistered successfully", style="green")
            else:
                console.print(f"❌ Failed to unregister service '{service_name}'", style="red")
                sys.exit(1)
                
        finally:
            await manager.stop()
    
    asyncio.run(_unregister())


@cli.command()
@click.argument('service_name')
@click.pass_context
def start(ctx, service_name):
    """Start a service."""
    
    async def _start():
        manager = AgentManager(ctx.obj['db_path'])
        
        try:
            service = manager.get_service_by_name(service_name)
            if not service:
                console.print(f"❌ Service '{service_name}' not found", style="red")
                sys.exit(1)
            
            console.print(f"Starting service '{service_name}'...")
            success = await manager.start_service(service.service_id)
            
            if success:
                console.print(f"✅ Service '{service_name}' started successfully", style="green")
            else:
                console.print(f"❌ Failed to start service '{service_name}'", style="red")
                sys.exit(1)
                
        finally:
            await manager.stop()
    
    asyncio.run(_start())


@cli.command()
@click.argument('service_name')
@click.pass_context
def stop(ctx, service_name):
    """Stop a service."""
    
    async def _stop():
        manager = AgentManager(ctx.obj['db_path'])
        
        try:
            service = manager.get_service_by_name(service_name)
            if not service:
                console.print(f"❌ Service '{service_name}' not found", style="red")
                sys.exit(1)
            
            console.print(f"Stopping service '{service_name}'...")
            success = await manager.stop_service(service.service_id)
            
            if success:
                console.print(f"✅ Service '{service_name}' stopped successfully", style="green")
            else:
                console.print(f"❌ Failed to stop service '{service_name}'", style="red")
                sys.exit(1)
                
        finally:
            await manager.stop()
    
    asyncio.run(_stop())


@cli.command()
@click.argument('service_name')
@click.pass_context
def restart(ctx, service_name):
    """Restart a service."""
    
    async def _restart():
        manager = AgentManager(ctx.obj['db_path'])
        
        try:
            service = manager.get_service_by_name(service_name)
            if not service:
                console.print(f"❌ Service '{service_name}' not found", style="red")
                sys.exit(1)
            
            console.print(f"Restarting service '{service_name}'...")
            success = await manager.restart_service(service.service_id)
            
            if success:
                console.print(f"✅ Service '{service_name}' restarted successfully", style="green")
            else:
                console.print(f"❌ Failed to restart service '{service_name}'", style="red")
                sys.exit(1)
                
        finally:
            await manager.stop()
    
    asyncio.run(_restart())


@cli.command()
@click.option('--status', type=click.Choice(['stopped', 'starting', 'running', 'stopping', 'error', 'unhealthy']))
@click.option('--tags', help='Comma-separated tags to filter by')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table')
@click.pass_context
def list(ctx, status, tags, output_format):
    """List services."""
    
    async def _list():
        manager = AgentManager(ctx.obj['db_path'])
        
        try:
            # Parse filters
            status_filter = ServiceStatus(status) if status else None
            tags_filter = [tag.strip() for tag in tags.split(',')] if tags else None
            
            services = manager.list_services(status=status_filter, tags=tags_filter)
            
            if output_format == 'json':
                service_data = []
                for service in services:
                    service_data.append({
                        'service_id': service.service_id,
                        'name': service.name,
                        'status': service.status.value,
                        'host': service.host,
                        'port': service.port,
                        'endpoint': service.endpoint,
                        'tags': list(service.tags),
                        'created_at': service.created_at.isoformat(),
                    })
                console.print(JSON.from_data(service_data))
            else:
                # Table format
                table = Table(title="Agent Services")
                table.add_column("Name", style="cyan")
                table.add_column("Status", style="magenta")
                table.add_column("Endpoint", style="blue")
                table.add_column("Tags", style="green")
                table.add_column("Created", style="yellow")
                
                for service in services:
                    status_emoji = {
                        ServiceStatus.RUNNING: "🟢",
                        ServiceStatus.STOPPED: "🔴",
                        ServiceStatus.STARTING: "🟡",
                        ServiceStatus.STOPPING: "🟡",
                        ServiceStatus.ERROR: "❌",
                        ServiceStatus.UNHEALTHY: "🟠",
                    }.get(service.status, "❓")
                    
                    table.add_row(
                        service.name,
                        f"{status_emoji} {service.status.value}",
                        service.endpoint,
                        ", ".join(service.tags),
                        service.created_at.strftime('%Y-%m-%d %H:%M'),
                    )
                
                console.print(table)
                
        finally:
            await manager.stop()
    
    asyncio.run(_list())


@cli.command()
@click.argument('service_name')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table')
@click.pass_context
def status(ctx, service_name, output_format):
    """Show detailed status of a service."""
    
    async def _status():
        manager = AgentManager(ctx.obj['db_path'])
        
        try:
            service = manager.get_service_by_name(service_name)
            if not service:
                console.print(f"❌ Service '{service_name}' not found", style="red")
                sys.exit(1)
            
            if output_format == 'json':
                service_data = {
                    'service_id': service.service_id,
                    'name': service.name,
                    'description': service.description,
                    'status': service.status.value,
                    'host': service.host,
                    'port': service.port,
                    'endpoint': service.endpoint,
                    'tags': list(service.tags),
                    'agent_type': service.agent_type,
                    'version': service.version,
                    'created_at': service.created_at.isoformat(),
                    'started_at': service.started_at.isoformat() if service.started_at else None,
                    'restart_count': service.restart_count,
                    'error_message': service.error_message,
                    'config': service.config.model_dump(),
                    'stats': service.stats.model_dump(),
                }
                console.print(JSON.from_data(service_data))
            else:
                # Create info panel
                info_text = f"""
[bold]Service ID:[/bold] {service.service_id}
[bold]Name:[/bold] {service.name}
[bold]Description:[/bold] {service.description}
[bold]Status:[/bold] {service.status.value}
[bold]Endpoint:[/bold] {service.endpoint}
[bold]Tags:[/bold] {', '.join(service.tags) if service.tags else 'None'}
[bold]Agent Type:[/bold] {service.agent_type}
[bold]Version:[/bold] {service.version}
[bold]Created:[/bold] {service.created_at.strftime('%Y-%m-%d %H:%M:%S')}
[bold]Started:[/bold] {service.started_at.strftime('%Y-%m-%d %H:%M:%S') if service.started_at else 'Not started'}
[bold]Restart Count:[/bold] {service.restart_count}
"""
                if service.error_message:
                    info_text += f"[bold]Error:[/bold] {service.error_message}\n"
                
                console.print(Panel(info_text.strip(), title="Service Information"))
                
                # Stats table
                stats_table = Table(title="Statistics")
                stats_table.add_column("Metric", style="cyan")
                stats_table.add_column("Value", style="magenta")
                
                stats_table.add_row("Active Connections", str(service.stats.active_connections))
                stats_table.add_row("Total Connections", str(service.stats.total_connections))
                stats_table.add_row("Active Sessions", str(service.stats.active_sessions))
                stats_table.add_row("Total Sessions", str(service.stats.total_sessions))
                stats_table.add_row("Error Count", str(service.stats.error_count))
                stats_table.add_row("Uptime (sec)", str(service.stats.uptime_seconds))
                
                console.print(stats_table)
                
        finally:
            await manager.stop()
    
    asyncio.run(_status())


@cli.command()
@click.pass_context
def stats(ctx):
    """Show system statistics."""
    
    async def _stats():
        manager = AgentManager(ctx.obj['db_path'])
        
        try:
            stats = manager.get_system_stats()
            
            # Services summary
            services_table = Table(title="Services Summary")
            services_table.add_column("Status", style="cyan")
            services_table.add_column("Count", style="magenta")
            
            for status, count in stats['services'].items():
                services_table.add_row(status.title(), str(count))
            
            console.print(services_table)
            
            # Connections summary
            connections_table = Table(title="Connections Summary")
            connections_table.add_column("Metric", style="cyan")
            connections_table.add_column("Count", style="magenta")
            
            connections_table.add_row("Total Connections", str(stats['connections']['total_connections']))
            
            for status, count in stats['connections']['by_status'].items():
                connections_table.add_row(f"  {status.title()}", str(count))
            
            console.print(connections_table)
            
        finally:
            await manager.stop()
    
    asyncio.run(_stats())


@cli.command()
@click.option('--interval', type=int, default=10, help='Health check interval in seconds')
@click.pass_context
def daemon(ctx, interval):
    """Run MyAgent manager as a daemon."""

    async def _daemon():
        manager = AgentManager(ctx.obj['db_path'])

        try:
            await manager.start(health_check_interval=interval)
            console.print("🚀 MyAgent Manager daemon started", style="green")
            console.print(f"   Health check interval: {interval}s")
            console.print("   Press Ctrl+C to stop")

            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            console.print("\n🛑 Shutting down MyAgent Manager daemon...", style="yellow")
        finally:
            await manager.stop()
            console.print("✅ MyAgent Manager daemon stopped", style="green")

    try:
        asyncio.run(_daemon())
    except KeyboardInterrupt:
        pass


@cli.command('cleanup-connections')
@click.option('--force', is_flag=True, help='Force cleanup without confirmation')
@click.pass_context
def cleanup_connections(ctx, force):
    """Clean up stale connections."""

    async def _cleanup():
        manager = AgentManager(ctx.obj['db_path'])

        try:
            # Get all connections
            connections = manager.get_active_connections()

            if not connections:
                console.print("✅ No connections to clean up", style="green")
                return

            console.print(f"Found {len(connections)} connection(s):", style="yellow")
            for conn in connections:
                console.print(f"  • {conn.connection_id} -> {conn.target_service_id}")

            if not force:
                confirm = console.input("\nClean up all connections? [y/N]: ")
                if confirm.lower() != 'y':
                    console.print("Aborted", style="yellow")
                    return

            # Clear all connections
            for conn in connections:
                manager.unregister_connection(conn.connection_id)

            console.print(f"✅ Cleaned up {len(connections)} connection(s)", style="green")

        finally:
            await manager.stop()

    asyncio.run(_cleanup())


# Import and register server commands
from .api import api as api_cmd
from .proxy import proxy as proxy_cmd

cli.add_command(api_cmd, name='api')
cli.add_command(proxy_cmd, name='proxy')


if __name__ == '__main__':
    cli()