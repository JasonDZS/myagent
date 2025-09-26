# WebSocket Server Setup

MyAgent provides a built-in WebSocket server for real-time agent interactions. This guide covers server setup, configuration, and deployment.

## Quick Start

### 1. Basic Server Setup

Create a simple agent and start the WebSocket server:

```python
# weather_agent.py
from myagent import create_toolcall_agent
from myagent.tool import BaseTool
from myagent.tool.base_tool import ToolResult

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather for a location"
    
    async def execute(self, location: str) -> ToolResult:
        # Mock weather data for demo
        return ToolResult(output=f"Weather in {location}: Sunny, 72°F")

def create_agent():
    return create_toolcall_agent(
        name="weather-agent",
        tools=[WeatherTool()],
        system_prompt="You are a helpful weather assistant."
    )

if __name__ == "__main__":
    # This enables CLI usage
    pass
```

### 2. Start the Server

```bash
# Start server with CLI
uv run python -m myagent.cli.server server weather_agent.py --port 8889

# Or specify host and port
uv run python -m myagent.cli.server server weather_agent.py --host 0.0.0.0 --port 8080
```

### 3. Test Connection

```javascript
// Simple WebSocket client test
const ws = new WebSocket('ws://localhost:8889');

ws.onopen = () => {
    console.log('Connected to agent');
    
    // Send user message
    ws.send(JSON.stringify({
        type: 'USER_MESSAGE',
        data: {
            message: 'What is the weather in New York?'
        }
    }));
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
};
```

## Programmatic Server Setup

### Basic Server

```python
import asyncio
from myagent.ws.server import AgentWebSocketServer

async def main():
    # Create server
    server = AgentWebSocketServer(
        agent_factory=create_agent,
        host="localhost",
        port=8889
    )
    
    # Start server
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Server Configuration

```python
from myagent.ws.server import AgentWebSocketServer
from myagent.ws.events import SystemEvents
import logging

async def create_advanced_agent():
    agent = create_toolcall_agent(
        name="advanced-agent",
        tools=[WeatherTool(), CalculatorTool()],
        system_prompt="""You are a multi-purpose assistant.
        Always be helpful and provide clear explanations.""",
        max_steps=10
    )
    return agent

async def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    server = AgentWebSocketServer(
        agent_factory=create_advanced_agent,
        host="0.0.0.0",  # Accept connections from any IP
        port=8889,
        max_connections=100,  # Limit concurrent connections
        heartbeat_interval=30,  # Seconds between heartbeats
        timeout=300  # Connection timeout in seconds
    )
    
    # Add custom event handlers
    @server.on_connect
    async def on_connect(session_id: str, websocket):
        print(f"New connection: {session_id}")
    
    @server.on_disconnect  
    async def on_disconnect(session_id: str):
        print(f"Client disconnected: {session_id}")
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("Shutting down server...")
        await server.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## Command Line Interface

### CLI Options

```bash
uv run python -m myagent.cli.server server --help
```

**Arguments:**
- `agent_file`: Python file containing agent factory function
- `--host`: Server host (default: localhost)  
- `--port`: Server port (default: 8889)
- `--reload`: Auto-reload on file changes (development)
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR)

**Examples:**
```bash
# Basic usage
uv run python -m myagent.cli.server server my_agent.py

# Custom host and port
uv run python -m myagent.cli.server server my_agent.py --host 0.0.0.0 --port 3000

# Development mode with auto-reload
uv run python -m myagent.cli.server server my_agent.py --reload

# Debug logging
uv run python -m myagent.cli.server server my_agent.py --log-level DEBUG
```

## Agent Factory Requirements

Your agent file must provide a way to create agents:

### Method 1: create_agent() Function

```python
# my_agent.py
def create_agent():
    """Factory function to create agent instances"""
    return create_toolcall_agent(
        name="my-agent",
        tools=[...],
        system_prompt="..."
    )
```

### Method 2: if __name__ == "__main__" Block

```python
# my_agent.py
async def main():
    agent = create_toolcall_agent(...)
    # Agent usage code here

def create_agent():
    return create_toolcall_agent(...)

if __name__ == "__main__":
    asyncio.run(main())
```

The CLI will automatically detect and use the `create_agent()` function.

## Server Configuration

### Environment Variables

```env
# WebSocket Server Configuration
WS_HOST=localhost
WS_PORT=8889
WS_MAX_CONNECTIONS=100
WS_HEARTBEAT_INTERVAL=30
WS_TIMEOUT=300

# Agent Configuration  
OPENAI_API_KEY=your_api_key
LLM_MODEL=gpt-4
LLM_MAX_TOKENS=2048

# Logging
LOG_LEVEL=INFO
```

### Configuration Class

```python
from myagent.config import settings

# Access WebSocket settings
print(f"Host: {settings.websocket.host}")
print(f"Port: {settings.websocket.port}")
print(f"Max connections: {settings.websocket.max_connections}")
```

## Server Events and Monitoring

### Event Handling

```python
from myagent.ws.server import AgentWebSocketServer
from myagent.ws.events import SystemEvents

server = AgentWebSocketServer(create_agent)

@server.on_event(SystemEvents.SESSION_CREATED)
async def handle_session_created(data):
    print(f"New session: {data['session_id']}")

@server.on_event(SystemEvents.AGENT_RESPONSE)
async def handle_agent_response(data):
    print(f"Agent responded to {data['session_id']}")

@server.on_event(SystemEvents.ERROR)
async def handle_error(data):
    print(f"Error in session {data['session_id']}: {data['error']}")
```

### Server Status

```python
# Get server status
status = server.get_status()
print(f"Running: {status['running']}")
print(f"Active sessions: {status['active_sessions']}")
print(f"Total connections: {status['total_connections']}")
```

### Health Check Endpoint

The server automatically provides health check information:

```python
# Access health check data
health = await server.get_health_check()
print(f"Server health: {health}")
```

## Security Considerations

### CORS Configuration

```python
from myagent.ws.server import AgentWebSocketServer

server = AgentWebSocketServer(
    create_agent,
    cors_origins=["https://myapp.com", "https://localhost:3000"],
    cors_allow_credentials=True
)
```

### Authentication

```python
from myagent.ws.server import AgentWebSocketServer

async def authenticate_user(websocket, path):
    # Check authorization header
    auth_header = websocket.request_headers.get('Authorization')
    if not auth_header or not validate_token(auth_header):
        await websocket.close(code=4001, reason="Unauthorized")
        return False
    return True

server = AgentWebSocketServer(
    create_agent,
    auth_handler=authenticate_user
)
```

### Rate Limiting

```python
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_requests=10, window=60):
        self.max_requests = max_requests
        self.window = window
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        client_requests = self.requests[client_id]
        
        # Remove old requests
        client_requests[:] = [req for req in client_requests if now - req < self.window]
        
        # Check limit
        if len(client_requests) >= self.max_requests:
            return False
        
        # Add current request
        client_requests.append(now)
        return True

rate_limiter = RateLimiter()

@server.middleware
async def rate_limit_middleware(websocket, session_id):
    if not rate_limiter.is_allowed(session_id):
        await websocket.close(code=4029, reason="Rate limit exceeded")
        return False
    return True
```

## Deployment

### Development Deployment

```bash
# Simple development server
uv run python -m myagent.cli.server server my_agent.py --reload
```

### Production Deployment

#### Using systemd (Linux)

```ini
# /etc/systemd/system/myagent.service
[Unit]
Description=MyAgent WebSocket Server
After=network.target

[Service]
Type=simple
User=myagent
WorkingDirectory=/opt/myagent
Environment=OPENAI_API_KEY=your_key_here
ExecStart=/opt/myagent/venv/bin/python -m myagent.cli.server server agent.py --host 0.0.0.0 --port 8889
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable myagent
sudo systemctl start myagent
sudo systemctl status myagent
```

#### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8889

# Set environment variables
ENV OPENAI_API_KEY=""
ENV WS_HOST=0.0.0.0
ENV WS_PORT=8889

# Run server
CMD ["python", "-m", "myagent.cli.server", "server", "agent.py"]
```

```bash
# Build and run
docker build -t myagent-server .
docker run -p 8889:8889 -e OPENAI_API_KEY=your_key myagent-server
```

#### Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  myagent-server:
    build: .
    ports:
      - "8889:8889"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - WS_HOST=0.0.0.0
      - WS_PORT=8889
      - LOG_LEVEL=INFO
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
```

```bash
# Start with docker-compose
docker-compose up -d
```

### Reverse Proxy (nginx)

```nginx
# /etc/nginx/sites-available/myagent
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8889;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket specific settings
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

### Load Balancing

For high-traffic deployments, run multiple server instances:

```python
# server1.py (port 8889)
# server2.py (port 8890) 
# server3.py (port 8891)

# Use nginx or HAProxy to balance load
```

```nginx
# nginx load balancer
upstream myagent_servers {
    server localhost:8889;
    server localhost:8890;
    server localhost:8891;
}

server {
    listen 80;
    location / {
        proxy_pass http://myagent_servers;
        # ... other proxy settings
    }
}
```

## Monitoring and Logging

### Structured Logging

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        return json.dumps(log_entry)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler('myagent.log'),
        logging.StreamHandler()
    ]
)

# Apply JSON formatter
for handler in logging.root.handlers:
    handler.setFormatter(JSONFormatter())
```

### Metrics Collection

```python
from collections import Counter
import time

class ServerMetrics:
    def __init__(self):
        self.connections = 0
        self.total_messages = Counter()
        self.response_times = []
        self.start_time = time.time()
    
    def record_connection(self):
        self.connections += 1
    
    def record_message(self, message_type: str):
        self.total_messages[message_type] += 1
    
    def record_response_time(self, duration: float):
        self.response_times.append(duration)
        # Keep only last 1000 response times
        self.response_times = self.response_times[-1000:]
    
    def get_stats(self) -> dict:
        return {
            'uptime': time.time() - self.start_time,
            'connections': self.connections,
            'total_messages': dict(self.total_messages),
            'avg_response_time': sum(self.response_times) / len(self.response_times) if self.response_times else 0
        }

# Use in server
metrics = ServerMetrics()

@server.on_connect
async def track_connection(session_id, websocket):
    metrics.record_connection()
```

## Troubleshooting

### Common Issues

#### Port Already in Use
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port
lsof -i :8889

# Kill process
kill -9 <PID>

# Or use different port
uv run python -m myagent.cli.server server agent.py --port 8890
```

#### Connection Refused
```
WebSocketException: Connection was refused
```

**Solutions:**
1. Check if server is running
2. Verify host/port configuration
3. Check firewall settings
4. Ensure agent factory function exists

#### Memory Issues
```
MemoryError: Unable to allocate memory
```

**Solutions:**
1. Limit concurrent connections
2. Implement connection cleanup
3. Monitor memory usage
4. Use connection pooling

### Debug Mode

```bash
# Enable debug logging
uv run python -m myagent.cli.server server agent.py --log-level DEBUG
```

### Health Checks

```python
# Add health check endpoint
@server.route('/health')
async def health_check():
    return {
        'status': 'healthy',
        'connections': len(server.connections),
        'uptime': server.get_uptime()
    }
```

## Next Steps

- **[Protocol Documentation](protocol.md)** - WebSocket message format
- **[Client Integration](client-integration.md)** - Building client applications  
- **[Session Management](session-management.md)** - Managing agent sessions
- **[Examples](../examples/websocket-agent.md)** - Complete WebSocket examples