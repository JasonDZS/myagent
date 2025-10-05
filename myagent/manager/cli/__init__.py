"""CLI tools for WebSocket management system."""

from .manager import cli

__all__ = ["cli", "main"]


def main():
    """Main entry point for myagent-manager CLI."""
    cli()