# WebSocket实时Trace系统部署指南

本指南详细说明如何部署和使用MyAgent框架的WebSocket实时trace监控系统。

## 🏗️ 系统架构

```
┌─────────────────┐    WebSocket     ┌──────────────────┐    Trace Events    ┌─────────────────┐
│   Frontend      │ ◄─────────────► │   Backend        │ ◄──────────────► │   MyAgent       │
│  (Web Browser)  │                 │  (FastAPI)       │                    │   Framework     │
└─────────────────┘                 └──────────────────┘                    └─────────────────┘
```

## 📋 系统要求

### 后端要求
- Python 3.8+
- FastAPI
- uvicorn
- WebSocket支持
- MySQL数据库连接

### 前端要求
- 现代Web浏览器 (支持WebSocket)
- 或React 18+ (如果使用React组件)

## 🛠️ 安装和配置

### 1. 安装Python依赖

```bash
# 安装基础依赖
pip install fastapi uvicorn websockets
pip install pymysql  # MySQL连接器

# 安装MyAgent框架 (如果还没有)
pip install -e .
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# MySQL配置
MYSQL_HOST=localhost
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
MYSQL_PORT=3306

# OpenAI配置 (如果使用OpenAI)
OPENAI_API_KEY=your_openai_api_key

# 其他可选配置
MYSQL_CHARSET=utf8mb4
```

### 3. 验证MySQL连接

确保MySQL服务运行并且可以连接：

```sql
-- 创建测试表 (可选)
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入测试数据
INSERT INTO users (name, email) VALUES 
    ('Alice', 'alice@example.com'),
    ('Bob', 'bob@example.com'),
    ('Charlie', 'charlie@example.com');
```

## 🚀 启动服务

### 方式1: 直接启动 (内置HTML界面)

```bash
# 启动WebSocket服务器
python examples/websocket_trace_server.py

# 服务将在以下地址启动:
# HTTP: http://localhost:8000
# WebSocket: ws://localhost:8000/ws/{session_id}
```

访问 `http://localhost:8000` 查看内置的Web界面。

### 方式2: React前端 + 后端分离

#### 启动后端服务

```bash
# 启动后端API服务
uvicorn examples.websocket_trace_server:app --host 0.0.0.0 --port 8000 --reload
```

#### 设置React前端

```bash
# 创建React项目
npx create-react-app websocket-trace-monitor
cd websocket-trace-monitor

# 安装依赖
npm install recharts lucide-react

# 将React组件复制到src/App.js
cp examples/frontend_react_trace.jsx src/App.js

# 启动React开发服务器
npm start
```

React应用将在 `http://localhost:3000` 启动。

### 方式3: Docker部署 (推荐生产环境)

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装Python依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 安装MyAgent框架
RUN pip install -e .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "examples.websocket_trace_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  websocket-trace-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MYSQL_HOST=mysql
      - MYSQL_USER=myagent
      - MYSQL_PASSWORD=password
      - MYSQL_DATABASE=myagent_db
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - mysql
    networks:
      - myagent-network

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=myagent_db
      - MYSQL_USER=myagent
      - MYSQL_PASSWORD=password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - myagent-network

volumes:
  mysql_data:

networks:
  myagent-network:
    driver: bridge
```

启动Docker服务：

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f websocket-trace-server
```

## 🔧 使用指南

### WebSocket消息协议

客户端发送消息格式：
```json
{
    "action": "start_agent",
    "question": "显示用户表的10条用户数据"
}
```

服务器返回消息格式：
```json
{
    "event_type": "trace_started",
    "timestamp": "2025-09-24T12:00:00.000Z",
    "message_id": "trace_start_abc12345",
    "session_id": "session_xyz789",
    "data": {
        "trace_id": "abc12345-...",
        "trace_name": "websocket-mysql-agent_execution",
        "request": "显示用户表的10条用户数据",
        "agent_name": "websocket-mysql-agent",
        "max_steps": 10
    }
}
```

### 事件类型

| 事件类型 | 描述 | 触发时机 |
|----------|------|----------|
| `connection_established` | WebSocket连接建立 | 客户端连接时 |
| `trace_started` | Trace开始 | Agent开始执行时 |
| `trace_completed` | Trace完成 | Agent执行完成时 |
| `think_completed` | 思考阶段完成 | LLM推理完成时 |
| `tool_completed` | 工具执行完成 | 工具调用完成时 |
| `run_error` | 执行错误 | 出现错误时 |
| `status_update` | 状态更新 | 状态变化时 |

### 客户端JavaScript示例

```javascript
// 建立WebSocket连接
const sessionId = 'session_' + Math.random().toString(36).substring(7);
const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);

// 监听消息
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
    
    // 处理不同类型的事件
    switch(message.event_type) {
        case 'trace_started':
            console.log('Agent started:', message.data.agent_name);
            break;
        case 'think_completed':
            console.log('Thinking completed in:', message.data.duration_ms, 'ms');
            break;
        case 'tool_completed':
            console.log('Tool executed:', message.data.name);
            break;
        // ... 其他事件处理
    }
};

// 发送启动请求
function startAgent(question) {
    const message = {
        action: 'start_agent',
        question: question
    };
    ws.send(JSON.stringify(message));
}
```

## 🐛 故障排除

### 常见问题

1. **WebSocket连接失败**
   ```bash
   # 检查端口是否占用
   lsof -i :8000
   
   # 检查防火墙设置
   sudo ufw status
   ```

2. **MySQL连接错误**
   ```bash
   # 检查MySQL服务状态
   systemctl status mysql
   
   # 测试连接
   mysql -h localhost -u your_username -p
   ```

3. **环境变量未设置**
   ```bash
   # 检查环境变量
   echo $MYSQL_HOST
   echo $OPENAI_API_KEY
   ```

### 调试模式

启用详细日志记录：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 或在启动时设置
uvicorn examples.websocket_trace_server:app --log-level debug
```

### 性能优化

1. **连接池配置**
```python
# 在生产环境中配置MySQL连接池
import pymysql.pool

config = {
    'host': 'localhost',
    'user': 'myagent',
    'password': 'password',
    'database': 'myagent_db',
    'autocommit': True,
    'cursorclass': pymysql.cursors.DictCursor,
}

connection_pool = pymysql.ConnectionPool(
    size=10,  # 连接池大小
    name='myagent_pool',
    **config
)
```

2. **WebSocket消息限流**
```python
# 限制消息发送频率
import asyncio
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_messages=10, time_window=1.0):
        self.max_messages = max_messages
        self.time_window = time_window
        self.clients = defaultdict(list)
    
    async def check_rate_limit(self, session_id):
        now = asyncio.get_event_loop().time()
        client_messages = self.clients[session_id]
        
        # 清理过期消息
        client_messages[:] = [t for t in client_messages if now - t < self.time_window]
        
        if len(client_messages) >= self.max_messages:
            return False
        
        client_messages.append(now)
        return True
```

## 📊 监控和维护

### 健康检查端点

```python
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(connection_manager.active_connections),
        "active_sessions": len(connection_manager.session_agents)
    }
```

### 日志记录

```python
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('websocket_trace.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 在关键位置记录日志
logger.info(f"WebSocket connection established: {session_id}")
logger.error(f"Agent execution failed: {str(e)}")
```

### 性能指标收集

```python
from collections import defaultdict
import time

class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def record_execution_time(self, operation, duration):
        self.metrics[f"{operation}_duration"].append(duration)
    
    def record_connection_count(self):
        self.metrics["active_connections"].append(
            len(connection_manager.active_connections)
        )
    
    def get_stats(self):
        stats = {}
        for key, values in self.metrics.items():
            if values:
                stats[key] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
        return stats
```

## 🔒 安全考虑

### WebSocket安全

1. **身份验证**
```python
# 在WebSocket连接时验证token
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, token: str = None):
    if not verify_token(token):
        await websocket.close(code=4001)
        return
    # ... 继续处理
```

2. **CORS配置**
```python
# 生产环境中限制CORS来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # 指定确切的域名
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

3. **消息验证**
```python
from pydantic import BaseModel, ValidationError

class ClientMessage(BaseModel):
    action: str
    question: str = ""

# 验证客户端消息
try:
    message = ClientMessage.parse_raw(data)
except ValidationError as e:
    await websocket.send_text(json.dumps({"error": "Invalid message format"}))
    return
```

这个部署指南提供了完整的WebSocket实时trace系统的安装、配置和维护说明，确保系统能够稳定、安全地运行在各种环境中。