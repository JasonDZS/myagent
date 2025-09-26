"""CLI for MyAgent WebSocket server deployment."""

import argparse
import asyncio
import importlib.util
import signal
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from myagent.logger import logger
from myagent.ws.server import AgentWebSocketServer


def load_agent_from_file(file_path: str) -> Callable[[], Any]:
    """Dynamically load Agent from Python file"""
    file_path = Path(file_path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"❌ Agent file does not exist: {file_path}")

    if not file_path.suffix == ".py":
        raise ValueError(f"❌ Agent file must be a Python file: {file_path}")

    try:
        # Dynamically load module
        spec = importlib.util.spec_from_file_location("agent_module", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {file_path}")

        module = importlib.util.module_from_spec(spec)

        # Add module to sys.modules to avoid import issues
        sys.modules["agent_module"] = module
        spec.loader.exec_module(module)

        # Look for agent variable
        if not hasattr(module, "agent"):
            raise AttributeError(
                f"❌ 'agent' variable not found in {file_path}\\n"
                f"Please ensure the file defines a variable named 'agent'"
            )

        agent_template = module.agent

        # Validate if it's a valid Agent instance
        if not hasattr(agent_template, "run") and not hasattr(agent_template, "arun"):
            raise AttributeError(
                "❌ agent variable is not a valid Agent instance\\nAgent must have 'run' or 'arun' method"
            )

        # Create factory function, re-execute module each time to create new instance
        def agent_factory():
            try:
                # Re-execute module to create fresh instance, avoiding deep copy issues
                fresh_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(fresh_module)

                if not hasattr(fresh_module, "agent"):
                    raise AttributeError("Agent module must contain 'agent' variable")

                return fresh_module.agent
            except Exception as e:
                logger.error(f"Failed to create agent instance: {e}")
                raise RuntimeError(f"Could not create agent instance: {e}") from e

        return agent_factory

    except ImportError as e:
        raise ImportError(f"❌ Failed to import Agent file: {e}") from e
    except SyntaxError as e:
        raise SyntaxError(f"❌ Agent file syntax error: {e}") from e
    except Exception as e:
        raise RuntimeError(f"❌ Error loading Agent file: {e}") from e


async def run_server(args):
    """Run WebSocket server"""
    print(f"🔍 Loading Agent file: {args.agent_file}")

    try:
        agent_factory = load_agent_from_file(args.agent_file)

        # Test agent creation
        test_agent = agent_factory()
        agent_name = getattr(test_agent, "name", "unknown")
        print(f"✅ Agent loaded successfully: {agent_name}")

    except Exception as e:
        print(f"❌ {e}")
        return 1

    # Create server
    server = AgentWebSocketServer(
        agent_factory_func=agent_factory, host=args.host, port=args.port
    )

    # Set up asyncio signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    shutdown_requested = False

    def handle_shutdown():
        nonlocal shutdown_requested
        if not shutdown_requested:
            shutdown_requested = True
            print("\\n🛑 Shutting down server...")
            # Create shutdown task
            shutdown_task = loop.create_task(server.shutdown())

    # Use asyncio signal handling, which works better in event loop
    loop.add_signal_handler(signal.SIGINT, handle_shutdown)
    loop.add_signal_handler(signal.SIGTERM, handle_shutdown)

    try:
        await server.start_server()
        print("🛑 Server stopped")
        return 0
    except KeyboardInterrupt:
        print("\\n🛑 Server stopped")
        return 0
    except Exception as e:
        print(f"❌ Server error: {e}")
        return 1


def create_server_parser(subparsers):
    """Create server subcommand parser"""
    server_parser = subparsers.add_parser(
        "server",
        help="Start MyAgent WebSocket server",
        description="Deploy MyAgent instance as WebSocket service",
    )

    server_parser.add_argument(
        "agent_file",
        help="Agent configuration file path (Python file, must contain 'agent' variable)",
    )

    server_parser.add_argument(
        "--host", default="localhost", help="Server host address (default: localhost)"
    )

    server_parser.add_argument(
        "--port", type=int, default=8080, help="Server port (default: 8080)"
    )

    server_parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    return server_parser


def main():
    """CLI main entry point"""
    parser = argparse.ArgumentParser(
        prog="myagent-ws",
        description="MyAgent WebSocket deployment tool",
        epilog="""
Examples:
  myagent-ws server my_agent.py                    # Start server
  myagent-ws server my_agent.py --host 0.0.0.0     # Listen on all addresses
  myagent-ws server my_agent.py --port 9000        # Specify port
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version", action="version", version="MyAgent WebSocket Server 1.0.0"
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", metavar="COMMAND"
    )

    # server subcommand
    create_server_parser(subparsers)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Set log level
    if getattr(args, "debug", False):
        import logging

        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Execute command
    if args.command == "server":
        try:
            return asyncio.run(run_server(args))
        except KeyboardInterrupt:
            print("\\n🛑 Operation interrupted")
            return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())
