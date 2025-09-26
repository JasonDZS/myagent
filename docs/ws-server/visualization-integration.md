# WebSocket 可视化集成指南

本指南详细说明前端如何通过 MyAgent WebSocket 消息获取可视化数据和参数，并实现实时数据可视化。

## 概述

当用户请求数据可视化时，MyAgent 会执行 `DataVisualTool` 工具，前端可以通过监听 `agent.tool_call` 和 `agent.tool_result` 事件来获取可视化参数和数据，实现实时图表渲染。

## 事件流程

```
用户消息 → Agent 分析 → 工具调用 → 工具执行 → 返回结果
    ↓           ↓           ↓           ↓           ↓
  MESSAGE   THINKING   TOOL_CALL   TOOL_RESULT  FINAL_ANSWER
```

## 1. 监听可视化工具调用

### 1.1 TOOL_CALL 事件结构

当 Agent 决定使用 `data_visual` 工具时，会发送以下事件：

```json
{
  "event": "agent.tool_call",
  "session_id": "session-123",
  "step_id": "step_1_data_visual",
  "content": "Calling tool: data_visual",
  "metadata": {
    "tool": "data_visual",
    "args": {
      "sql": "SELECT month, sales, profit FROM monthly_data ORDER BY month",
      "chart_type": "bar",
      "x_field": "month",
      "y_fields": ["sales", "profit"],
      "title": "Monthly Sales and Profit"
    },
    "status": "running"
  },
  "timestamp": "2023-12-01T14:30:20.123Z"
}
```

### 1.2 监听代码示例

```javascript
class VisualizationHandler {
  constructor(websocket) {
    this.websocket = websocket;
    this.pendingVisualizations = new Map();
    this.setupEventListeners();
  }

  setupEventListeners() {
    this.websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.event) {
        case 'agent.tool_call':
          this.handleToolCall(data);
          break;
        case 'agent.tool_result':
          this.handleToolResult(data);
          break;
      }
    };
  }

  handleToolCall(data) {
    if (data.metadata.tool === 'data_visual') {
      const stepId = data.step_id;
      const params = data.metadata.args;
      
      // 存储可视化参数，等待数据返回
      this.pendingVisualizations.set(stepId, {
        params: params,
        timestamp: new Date(),
        status: 'waiting_for_data'
      });
      
      // 显示加载状态
      this.showVisualizationLoading(stepId, params);
      
      console.log('📊 Visualization requested:', params);
    }
  }

  showVisualizationLoading(stepId, params) {
    const containerId = `chart-${stepId}`;
    const container = document.getElementById(containerId) || this.createChartContainer(stepId);
    
    container.innerHTML = `
      <div class="chart-loading">
        <div class="spinner"></div>
        <h3>正在生成${params.chart_type}图表...</h3>
        <p>标题: ${params.title || '未指定'}</p>
        <p>数据源: ${params.sql.substring(0, 50)}...</p>
      </div>
    `;
  }
}
```

## 2. 接收可视化结果数据

### 2.1 TOOL_RESULT 事件结构

工具执行完成后，会发送包含可视化数据的结果事件：

```json
{
  "event": "agent.tool_result",
  "session_id": "session-123",
  "step_id": "step_1_data_visual",
  "content": "Visualization created successfully. Chart saved to: ./workdir/charts/chart_20231201_143022_bar.png\nData rows: 150, Chart type: bar",
  "metadata": {
    "tool": "data_visual",
    "status": "success",
    "error": null,
    "data": [
      {"month": "Jan", "sales": 1000, "profit": 200},
      {"month": "Feb", "sales": 1200, "profit": 250},
      {"month": "Mar", "sales": 1100, "profit": 220},
      {"month": "Apr", "sales": 1300, "profit": 280},
      {"month": "May", "sales": 1150, "profit": 240}
    ]
  },
  "timestamp": "2023-12-01T14:30:22.456Z"
}
```

### 2.2 处理可视化数据

```javascript
handleToolResult(data) {
  if (data.metadata.tool === 'data_visual') {
    const stepId = data.step_id;
    const pending = this.pendingVisualizations.get(stepId);
    
    if (!pending) {
      console.warn('未找到对应的可视化请求:', stepId);
      return;
    }
    
    if (data.metadata.status === 'success') {
      const chartData = data.metadata.data;
      const params = pending.params;
      
      // 创建可视化
      this.createVisualization(stepId, params, chartData, data.content);
      
      // 清理待处理状态
      this.pendingVisualizations.delete(stepId);
      
      console.log('✅ Visualization created successfully:', stepId);
    } else {
      // 处理错误
      this.handleVisualizationError(stepId, data.metadata.error || data.content);
    }
  }
}

createVisualization(stepId, params, data, backendMessage) {
  try {
    // 验证数据
    if (!data || data.length === 0) {
      throw new Error('No data returned from query');
    }
    
    // 获取或创建容器
    const containerId = `chart-${stepId}`;
    const container = document.getElementById(containerId) || this.createChartContainer(stepId);
    
    // 创建ECharts图表
    const chart = this.createEChartsVisualization(container, params, data);
    
    // 添加后端信息显示
    this.addBackendInfo(container, backendMessage, params);
    
    // 存储图表实例以便后续操作
    this.charts = this.charts || new Map();
    this.charts.set(stepId, chart);
    
  } catch (error) {
    console.error('Visualization creation failed:', error);
    this.handleVisualizationError(stepId, error.message);
  }
}
```

## 3. ECharts 集成实现

### 3.1 通用图表创建函数

```javascript
createEChartsVisualization(container, params, data) {
  const chart = echarts.init(container);
  
  // 根据图表类型创建配置
  let option;
  switch (params.chart_type) {
    case 'pie':
      option = this.createPieOption(params, data);
      break;
    case 'bar':
      option = this.createBarOption(params, data);
      break;
    case 'line':
      option = this.createLineOption(params, data);
      break;
    case 'scatter':
      option = this.createScatterOption(params, data);
      break;
    default:
      throw new Error(`Unsupported chart type: ${params.chart_type}`);
  }
  
  // 设置图表选项
  chart.setOption(option);
  
  // 添加响应式支持
  this.makeChartResponsive(chart);
  
  return chart;
}

createBarOption(params, data) {
  const categories = data.map(row => row[params.x_field]);
  const series = params.y_fields.map(field => ({
    name: field,
    type: 'bar',
    data: data.map(row => row[field]),
    animation: true,
    animationDuration: 1000
  }));
  
  return {
    title: {
      text: params.title || `${params.chart_type.toUpperCase()} Chart`,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: params.y_fields,
      top: 'bottom'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      name: params.x_field,
      nameLocation: 'middle',
      nameGap: 30
    },
    yAxis: {
      type: 'value',
      name: 'Values'
    },
    series: series
  };
}

createLineOption(params, data) {
  const categories = data.map(row => row[params.x_field]);
  const series = params.y_fields.map(field => ({
    name: field,
    type: 'line',
    data: data.map(row => row[field]),
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    animation: true,
    animationDuration: 1000
  }));
  
  return {
    title: {
      text: params.title || 'Line Chart',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: params.y_fields,
      top: 'bottom'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      name: params.x_field
    },
    yAxis: {
      type: 'value',
      name: 'Values'
    },
    series: series
  };
}

createPieOption(params, data) {
  const pieData = data.map(row => ({
    name: row[params.x_field],
    value: row[params.y_fields[0]]
  }));
  
  return {
    title: {
      text: params.title || 'Pie Chart',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b} : {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      data: pieData.map(item => item.name)
    },
    series: [
      {
        name: 'Data',
        type: 'pie',
        radius: '50%',
        data: pieData,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        animation: true,
        animationType: 'scale',
        animationEasing: 'elasticOut',
        animationDelay: function (idx) {
          return Math.random() * 200;
        }
      }
    ]
  };
}

createScatterOption(params, data) {
  const series = params.y_fields.map(field => ({
    name: field,
    type: 'scatter',
    data: data.map(row => [row[params.x_field], row[field]]),
    symbolSize: 8,
    animation: true
  }));
  
  return {
    title: {
      text: params.title || 'Scatter Chart',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: function (params) {
        return `${params.seriesName}<br/>${params.data[0]}: ${params.data[1]}`;
      }
    },
    legend: {
      data: params.y_fields,
      top: 'bottom'
    },
    xAxis: {
      type: 'value',
      name: params.x_field,
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: 'Values',
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series: series
  };
}
```

### 3.2 辅助功能

```javascript
// 创建图表容器
createChartContainer(stepId) {
  const container = document.createElement('div');
  container.id = `chart-${stepId}`;
  container.className = 'chart-container';
  container.style.cssText = `
    width: 100%;
    height: 400px;
    margin: 20px 0;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 10px;
    background: white;
  `;
  
  // 添加到页面
  const chatContainer = document.getElementById('chat-container') || document.body;
  chatContainer.appendChild(container);
  
  return container;
}

// 添加后端信息显示
addBackendInfo(container, message, params) {
  const infoDiv = document.createElement('div');
  infoDiv.className = 'chart-info';
  infoDiv.style.cssText = `
    margin-top: 10px;
    padding: 8px;
    background: #f5f5f5;
    border-radius: 4px;
    font-size: 12px;
    color: #666;
  `;
  
  infoDiv.innerHTML = `
    <details>
      <summary>📊 图表详情</summary>
      <div style="margin-top: 8px;">
        <p><strong>SQL查询:</strong> <code>${params.sql}</code></p>
        <p><strong>图表类型:</strong> ${params.chart_type}</p>
        <p><strong>X轴字段:</strong> ${params.x_field || 'N/A'}</p>
        <p><strong>Y轴字段:</strong> ${params.y_fields.join(', ')}</p>
        <p><strong>后端消息:</strong> ${message}</p>
      </div>
    </details>
  `;
  
  container.appendChild(infoDiv);
}

// 响应式支持
makeChartResponsive(chart) {
  const resizeHandler = () => {
    chart.resize();
  };
  
  window.addEventListener('resize', resizeHandler);
  
  // 使用ResizeObserver监听容器大小变化
  if (window.ResizeObserver) {
    const resizeObserver = new ResizeObserver(resizeHandler);
    resizeObserver.observe(chart.getDom());
  }
}

// 错误处理
handleVisualizationError(stepId, errorMessage) {
  const containerId = `chart-${stepId}`;
  const container = document.getElementById(containerId) || this.createChartContainer(stepId);
  
  container.innerHTML = `
    <div class="chart-error">
      <div style="text-align: center; padding: 40px; color: #ff4d4f;">
        <h3>❌ 图表生成失败</h3>
        <p>${errorMessage}</p>
        <button onclick="this.parentElement.parentElement.remove()" 
                style="margin-top: 10px; padding: 5px 15px; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;">
          关闭
        </button>
      </div>
    </div>
  `;
  
  // 清理待处理状态
  this.pendingVisualizations.delete(stepId);
}
```

## 4. 完整使用示例

### 4.1 HTML 结构

```html
<!DOCTYPE html>
<html>
<head>
    <title>MyAgent 可视化集成</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        .chart-container {
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: white;
        }
        
        .chart-loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 2s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div id="chat-container">
        <!-- 图表将动态插入这里 -->
    </div>

    <script>
        // 初始化WebSocket连接和可视化处理器
        const websocket = new WebSocket('ws://localhost:8080');
        const visualizationHandler = new VisualizationHandler(websocket);
        
        websocket.onopen = function() {
            console.log('WebSocket连接已建立');
            
            // 创建会话
            websocket.send(JSON.stringify({
                event: 'user.create_session'
            }));
        };
        
        // 示例：发送可视化请求
        function requestVisualization() {
            websocket.send(JSON.stringify({
                event: 'user.message',
                session_id: 'your-session-id',
                content: '请创建一个显示月度销售和利润的柱状图'
            }));
        }
    </script>
</body>
</html>
```

### 4.2 集成到现有应用

```javascript
// 集成到现有聊天应用
class ChatApp {
  constructor() {
    this.websocket = new WebSocket('ws://localhost:8080');
    this.visualizationHandler = new VisualizationHandler(this.websocket);
    this.sessionId = null;
    
    this.setupWebSocket();
  }
  
  setupWebSocket() {
    this.websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // 处理可视化事件
      this.visualizationHandler.handleMessage(data);
      
      // 处理其他聊天事件
      switch (data.event) {
        case 'agent.session_created':
          this.sessionId = data.session_id;
          console.log('会话创建成功:', this.sessionId);
          break;
        case 'agent.thinking':
          this.displayThinking(data.content);
          break;
        case 'agent.final_answer':
          this.displayFinalAnswer(data.content);
          break;
      }
    };
  }
  
  sendMessage(message) {
    if (!this.sessionId) {
      console.error('会话未创建');
      return;
    }
    
    this.websocket.send(JSON.stringify({
      event: 'user.message',
      session_id: this.sessionId,
      content: message
    }));
  }
}
```

## 5. 事件时序图

```
用户           前端           WebSocket       Agent         DataVisualTool
 |              |                |              |                |
 |--请求可视化-->|                |              |                |
 |              |--MESSAGE------>|              |                |
 |              |                |--execute---->|                |
 |              |                |              |--analyze------>|
 |              |<--THINKING-----|<-------------|                |
 |<-显示思考过程-|                |              |                |
 |              |<--TOOL_CALL----|<-------------|--决定使用工具--->|
 |<-显示加载状态-|                |              |                |
 |              |                |              |--execute_tool->|
 |              |                |              |                |--执行SQL
 |              |                |              |                |--生成图表
 |              |                |              |                |--返回数据
 |              |<--TOOL_RESULT--|<-------------|<---------------|
 |<-创建ECharts-|                |              |                |
 |              |<--FINAL_ANSWER-|<-------------|                |
 |<-显示完成信息-|                |              |                |
```

## 6. 最佳实践

### 6.1 性能优化
- 使用 `requestAnimationFrame` 优化图表渲染
- 对大数据集进行分页或采样显示
- 使用虚拟滚动处理大量图表

### 6.2 用户体验
- 显示加载状态和进度指示器
- 提供图表交互功能（缩放、平移、数据筛选）
- 支持图表导出功能（PNG、SVG、PDF）

### 6.3 错误处理
- 优雅处理网络断连和重连
- 提供用户友好的错误信息
- 实现重试机制

### 6.4 数据安全
- 验证和清理来自WebSocket的数据
- 对敏感数据进行适当的脱敏处理
- 实现适当的访问控制

## 总结

通过监听 `agent.tool_call` 和 `agent.tool_result` 事件，前端可以：

1. **获取可视化参数**: 从 `TOOL_CALL` 事件的 `metadata.args` 中获取
2. **获取可视化数据**: 从 `TOOL_RESULT` 事件的 `metadata.data` 中获取
3. **实时渲染图表**: 使用 ECharts 创建交互式可视化
4. **提供良好体验**: 显示加载状态、错误处理、响应式设计

这种架构实现了后端数据处理和前端交互体验的完美结合，为用户提供了强大的数据可视化能力。