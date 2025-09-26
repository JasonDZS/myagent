# Installation Guide

This guide covers different installation methods for MyAgent and how to set up your development environment.

## Prerequisites

- **Python 3.10+** - MyAgent requires Python 3.10 or later
- **OpenAI API Key** - Or another supported LLM provider
- **Git** (for development installation)

## Installation Methods

### 1. PyPI Installation (Recommended)

The easiest way to install MyAgent is from PyPI:

```bash
pip install myagent
```

Or using uv (faster):
```bash
uv add myagent
```

### 2. Optional Dependencies

MyAgent has several optional feature sets you can install:

```bash
# WebSocket server support
pip install myagent[websocket]

# Trace viewer web interface  
pip install myagent[trace-viewer]

# Development tools (linting, testing, etc.)
pip install myagent[dev]

# All optional dependencies
pip install myagent[websocket,trace-viewer,dev]
```

### 3. Development Installation

If you want to contribute to MyAgent or need the latest features:

```bash
# Clone the repository
git clone https://github.com/yourusername/myagent.git
cd myagent

# Install in development mode with uv
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"
```

## Environment Setup

### 1. Environment Variables

Create a `.env` file in your project root:

```env
# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1  # optional

# Model Configuration
LLM_MODEL=gpt-4
LLM_MAX_TOKENS=2048

# Tracing Configuration
TRACE_ENABLED=true
TRACE_STORAGE=sqlite

# WebSocket Server Configuration  
WS_HOST=localhost
WS_PORT=8889

# Optional: Web Search (if using search tools)
SERPER_API_KEY=your_serper_api_key_here

# Optional: Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database

# Logging Configuration
LOG_LEVEL=INFO
```

### 2. Verify Installation

Test your installation:

```python
import myagent
print(f"MyAgent version: {myagent.__version__}")

# Test basic imports
from myagent import create_toolcall_agent, BaseTool
print("✅ Basic imports successful")

# Test LLM configuration
from myagent import LLM
llm = LLM()
print("✅ LLM configuration successful")
```

## Platform-Specific Notes

### Windows

```bash
# Using pip
pip install myagent

# Using conda (if preferred)
conda install -c conda-forge myagent
```

### macOS

```bash
# Using pip
pip install myagent

# Using Homebrew + pip
brew install python
pip install myagent

# Using uv (recommended)
brew install uv
uv add myagent
```

### Linux

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip
pip install myagent

# CentOS/RHEL/Fedora
sudo yum install python3 python3-pip  # or dnf
pip install myagent

# Using uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv add myagent
```

## Docker Installation

Use MyAgent in a Docker container:

```dockerfile
FROM python:3.11-slim

# Install MyAgent
RUN pip install myagent[websocket,trace-viewer]

# Copy your application
COPY . /app
WORKDIR /app

# Set environment variables
ENV OPENAI_API_KEY=your_key_here

# Run your application
CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t my-agent-app .
docker run --env-file .env my-agent-app
```

## Virtual Environment Setup

### Using venv (Built-in)

```bash
# Create virtual environment
python -m venv myagent-env

# Activate (Linux/macOS)
source myagent-env/bin/activate

# Activate (Windows)
myagent-env\Scripts\activate

# Install MyAgent
pip install myagent

# Deactivate when done
deactivate
```

### Using conda

```bash
# Create conda environment
conda create -n myagent python=3.11
conda activate myagent

# Install MyAgent
pip install myagent

# Deactivate when done
conda deactivate
```

### Using uv (Recommended)

```bash
# Create project with virtual environment
uv init my-agent-project
cd my-agent-project

# Add MyAgent dependency
uv add myagent

# Run Python with the virtual environment
uv run python your_script.py
```

## Development Environment

If you plan to develop with MyAgent, set up the full development environment:

```bash
# Clone and install in development mode
git clone https://github.com/yourusername/myagent.git
cd myagent

# Install with development dependencies
uv sync --extra dev

# Install pre-commit hooks
make pre-commit-install

# Run tests to verify setup
make test

# Run linting
make lint

# Format code
make format
```

## Troubleshooting Installation

### Common Issues

#### 1. Python Version Error
```
ERROR: Package 'myagent' requires a different Python version
```

**Solution**: Upgrade to Python 3.10+
```bash
# Check your Python version
python --version

# Upgrade Python (varies by platform)
# On macOS with Homebrew:
brew install python@3.11

# On Ubuntu:
sudo apt install python3.11
```

#### 2. Missing Dependencies
```
ModuleNotFoundError: No module named 'pydantic'
```

**Solution**: Install with all dependencies
```bash
pip install --upgrade myagent
```

#### 3. Permission Errors (Linux/macOS)
```
ERROR: Could not install packages due to permissions
```

**Solution**: Use virtual environment or user installation
```bash
# User installation
pip install --user myagent

# Or create virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install myagent
```

#### 4. SSL Certificate Issues
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution**: Update certificates or use trusted hosts
```bash
# Update pip and certificates
pip install --upgrade pip certifi

# Or temporarily use trusted host
pip install --trusted-host pypi.org --trusted-host pypi.python.org myagent
```

#### 5. Network/Proxy Issues
```
ERROR: Could not find a version that satisfies the requirement
```

**Solution**: Configure proxy or use alternative index
```bash
# Configure proxy
pip install --proxy http://user:password@proxy.server:port myagent

# Use alternative index
pip install -i https://pypi.douban.com/simple/ myagent
```

### Verification Commands

After installation, verify everything works:

```bash
# Check package info
pip show myagent

# List installed dependencies
pip list | grep myagent

# Test CLI (if applicable)
myagent-server --help

# Run example
python -c "
import myagent
from myagent import create_toolcall_agent
print('✅ Installation successful!')
print(f'Version: {myagent.__version__}')
"
```

## Next Steps

After successful installation:

1. **[Quick Start](quick-start.md)** - Create your first agent
2. **[Basic Concepts](basic-concepts.md)** - Understand the framework
3. **[Configuration](configuration.md)** - Advanced configuration options
4. **[Examples](../../examples/)** - Browse working examples

## Getting Help

If you encounter installation issues:

- Check the [Troubleshooting Guide](../troubleshooting.md)
- Search [GitHub Issues](https://github.com/yourusername/myagent/issues)
- Ask for help in [Discussions](https://github.com/yourusername/myagent/discussions)