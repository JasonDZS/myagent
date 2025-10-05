#!/usr/bin/env python3
"""
MyAgent Manager CLI - Unified Entry Point

Provides a unified command-line interface for managing MyAgent services.

Usage:
    python -m myagent.manager.cli [COMMAND] [OPTIONS]

    Or use the installed command:
    myagent-manager [COMMAND] [OPTIONS]

Available Commands:
    Service Management (from manager.py):
        register    - Register a new agent service
        unregister  - Unregister a service
        start       - Start a service
        stop        - Stop a service
        restart     - Restart a service
        list        - List all services
        status      - Show service status
        stats       - Show system statistics
        daemon      - Run manager as a daemon

    Server Commands:
        api         - Run HTTP API server
        proxy       - Run WebSocket proxy server

Examples:
    # Register and start a service
    myagent-manager register my_agent examples/agent.py --auto-start

    # List all services
    myagent-manager list

    # Start API server
    myagent-manager api --port 8000

    # Start proxy server
    myagent-manager proxy --port 9000
"""

import sys

# Simply delegate to the manager CLI which already has all commands
from .manager import cli

if __name__ == '__main__':
    cli()
