"""Pytest configuration and shared fixtures."""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests."""
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="function")
def event_loop(event_loop_policy):
    """Create an instance of the default event loop for each test case."""
    loop = event_loop_policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db_path(temp_dir: Path) -> Path:
    """Create a temporary database path."""
    return temp_dir / "test_manager.db"


@pytest.fixture
def sample_agent_file(temp_dir: Path) -> Path:
    """Create a sample agent factory file for testing."""
    agent_file = temp_dir / "test_agent.py"
    agent_file.write_text('''"""Test agent factory."""
from myagent import create_react_agent

def create_agent():
    """Create a simple test agent."""
    return create_react_agent([], llm_config={"model": "gpt-4", "api_key": "test-key"})
''')
    return agent_file
