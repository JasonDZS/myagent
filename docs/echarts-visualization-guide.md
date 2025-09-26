# ECharts 前端可视化指南

基于 MyAgent DataVisualTool 参数的 ECharts 前端实现指南

## 概述

本指南展示如何使用 MyAgent 的 `DataVisualTool` 参数在前端通过 ECharts 创建相应的可视化图表。

## DataVisualTool 参数结构

```typescript
interface DataVisualToolParams {
  sql: string;                    // SQL 查询语句
  chart_type: 'pie' | 'line' | 'scatter' | 'bar';  // 图表类型
  x_field?: string;               // X轴字段名（饼图可选）
  y_fields: string[];             // Y轴字段名数组
  title?: string;                 // 图表标题（可选）
}
```

## 1. 数据获取与处理

### 1.1 执行 SQL 查询并获取数据

```javascript
// 通过 API 调用 DataVisualTool 获取数据和原始数据记录
async function getChartData(params) {
  const response = await fetch('/api/data-visual', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  
  const result = await response.json();
  
  if (result.error) {
    throw new Error(result.error);
  }
  
  // 期望返回格式：
  // {
  //   output: "Visualization created successfully. Chart saved to: ./workdir/charts/...",
  //   data: [{field1: value1, field2: value2}, ...],  // DataFrame记录
  //   system: "Data visualization completed: ..."
  // }
  return {
    message: result.output,
    data: result.data || [],
    system: result.system
  };
}
```

### 1.2 数据转换函数

```javascript
function transformDataForECharts(rawData, chartType, xField, yFields) {
  switch (chartType) {
    case 'pie':
      return transformPieData(rawData, xField, yFields[0]);
    case 'bar':
      return transformBarData(rawData, xField, yFields);
    case 'line':
      return transformLineData(rawData, xField, yFields);
    case 'scatter':
      return transformScatterData(rawData, xField, yFields);
    default:
      throw new Error(`Unsupported chart type: ${chartType}`);
  }
}
```

## 2. 各图表类型实现

### 2.1 饼图 (Pie Chart)

```javascript
function transformPieData(data, xField, valueField) {
  return data.map(row => ({
    name: row[xField],
    value: row[valueField]
  }));
}

function createPieChart(chartDom, data, title) {
  const myChart = echarts.init(chartDom);
  
  const option = {
    title: {
      text: title || 'Pie Chart',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b} : {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: 'Data',
        type: 'pie',
        radius: '50%',
        data: data,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  };
  
  myChart.setOption(option);
  return myChart;
}
```

### 2.2 柱状图 (Bar Chart)

```javascript
function transformBarData(data, xField, yFields) {
  const categories = data.map(row => row[xField]);
  const series = yFields.map(field => ({
    name: field,
    type: 'bar',
    data: data.map(row => row[field])
  }));
  
  return { categories, series };
}

function createBarChart(chartDom, data, xField, yFields, title) {
  const myChart = echarts.init(chartDom);
  const { categories, series } = transformBarData(data, xField, yFields);
  
  const option = {
    title: {
      text: title || 'Bar Chart',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: yFields,
      top: 'bottom'
    },
    xAxis: {
      type: 'category',
      data: categories,
      name: xField
    },
    yAxis: {
      type: 'value',
      name: 'Values'
    },
    series: series
  };
  
  myChart.setOption(option);
  return myChart;
}
```

### 2.3 折线图 (Line Chart)

```javascript
function transformLineData(data, xField, yFields) {
  const categories = data.map(row => row[xField]);
  const series = yFields.map(field => ({
    name: field,
    type: 'line',
    data: data.map(row => row[field]),
    smooth: true
  }));
  
  return { categories, series };
}

function createLineChart(chartDom, data, xField, yFields, title) {
  const myChart = echarts.init(chartDom);
  const { categories, series } = transformLineData(data, xField, yFields);
  
  const option = {
    title: {
      text: title || 'Line Chart',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: yFields,
      top: 'bottom'
    },
    xAxis: {
      type: 'category',
      data: categories,
      name: xField
    },
    yAxis: {
      type: 'value',
      name: 'Values'
    },
    series: series
  };
  
  myChart.setOption(option);
  return myChart;
}
```

### 2.4 散点图 (Scatter Chart)

```javascript
function transformScatterData(data, xField, yFields) {
  const series = yFields.map(field => ({
    name: field,
    type: 'scatter',
    data: data.map(row => [row[xField], row[field]])
  }));
  
  return { series };
}

function createScatterChart(chartDom, data, xField, yFields, title) {
  const myChart = echarts.init(chartDom);
  const { series } = transformScatterData(data, xField, yFields);
  
  const option = {
    title: {
      text: title || 'Scatter Chart',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: function (params) {
        return `${params.seriesName}<br/>${xField}: ${params.data[0]}<br/>Value: ${params.data[1]}`;
      }
    },
    legend: {
      data: yFields,
      top: 'bottom'
    },
    xAxis: {
      type: 'value',
      name: xField,
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
  
  myChart.setOption(option);
  return myChart;
}
```

## 3. 统一的图表创建器

```javascript
async function createChartFromParams(chartDom, params) {
  try {
    // 1. 获取数据
    const result = await getChartData(params);
    const { data, message, system } = result;
    
    if (!data || data.length === 0) {
      throw new Error('No data returned from query');
    }
    
    // 2. 验证字段是否存在（从数据记录中获取字段列表）
    const columns = Object.keys(data[0]);
    const missingFields = [];
    if (params.x_field && !columns.includes(params.x_field)) {
      missingFields.push(params.x_field);
    }
    params.y_fields.forEach(field => {
      if (!columns.includes(field)) {
        missingFields.push(field);
      }
    });
    
    if (missingFields.length > 0) {
      throw new Error(`Missing fields: ${missingFields.join(', ')}. Available fields: ${columns.join(', ')}`);
    }
    
    // 3. 根据图表类型创建相应图表
    let chart;
    switch (params.chart_type) {
      case 'pie':
        const pieData = transformPieData(data, params.x_field, params.y_fields[0]);
        chart = createPieChart(chartDom, pieData, params.title);
        break;
      
      case 'bar':
        chart = createBarChart(chartDom, data, params.x_field, params.y_fields, params.title);
        break;
      
      case 'line':
        chart = createLineChart(chartDom, data, params.x_field, params.y_fields, params.title);
        break;
      
      case 'scatter':
        chart = createScatterChart(chartDom, data, params.x_field, params.y_fields, params.title);
        break;
      
      default:
        throw new Error(`Unsupported chart type: ${params.chart_type}`);
    }
    
    // 显示后端处理信息（可选）
    console.log('Backend processing:', message);
    console.log('System info:', system);
    
    return chart;
  } catch (error) {
    console.error('Chart creation failed:', error);
    throw error;
  }
}
```

## 4. 使用示例

### 4.1 HTML 结构

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
</head>
<body>
    <div id="chart-container" style="width: 800px; height: 600px;"></div>
</body>
</html>
```

### 4.2 JavaScript 调用

```javascript
// 示例1: 创建柱状图
const barParams = {
  sql: "SELECT month, sales, profit FROM monthly_data ORDER BY month",
  chart_type: "bar",
  x_field: "month",
  y_fields: ["sales", "profit"],
  title: "Monthly Sales and Profit"
};

const chartDom = document.getElementById('chart-container');
createChartFromParams(chartDom, barParams);

// 示例2: 创建饼图
const pieParams = {
  sql: "SELECT category, count FROM category_stats",
  chart_type: "pie",
  x_field: "category",
  y_fields: ["count"],
  title: "Category Distribution"
};

createChartFromParams(chartDom, pieParams);

// 示例3: 创建多条折线图
const lineParams = {
  sql: "SELECT date, temperature, humidity FROM weather_data ORDER BY date",
  chart_type: "line",
  x_field: "date",
  y_fields: ["temperature", "humidity"],
  title: "Weather Trends"
};

createChartFromParams(chartDom, lineParams);
```

## 5. 响应式设计

```javascript
function makeChartResponsive(chart) {
  // 监听窗口大小变化
  window.addEventListener('resize', function() {
    chart.resize();
  });
  
  // 设置响应式配置
  const responsiveOption = {
    responsive: true,
    maintainAspectRatio: false
  };
  
  chart.setOption(responsiveOption);
}
```

## 6. 错误处理

```javascript
function handleChartError(error, chartDom) {
  console.error('Chart error:', error);
  
  // 显示错误信息
  chartDom.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">
      <div>
        <h3>Chart Error</h3>
        <p>${error.message}</p>
      </div>
    </div>
  `;
}
```

## 7. 完整集成示例

```javascript
class DataVisualizer {
  constructor(apiEndpoint) {
    this.apiEndpoint = apiEndpoint;
  }
  
  async visualize(containerId, params) {
    const chartDom = document.getElementById(containerId);
    
    try {
      // 显示加载状态
      this.showLoading(chartDom);
      
      // 创建图表
      const chart = await createChartFromParams(chartDom, params);
      
      // 添加响应式支持
      makeChartResponsive(chart);
      
      return chart;
    } catch (error) {
      handleChartError(error, chartDom);
      throw error;
    }
  }
  
  showLoading(chartDom) {
    chartDom.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100%;">
        <div>Loading chart...</div>
      </div>
    `;
  }
}

// 使用示例
const visualizer = new DataVisualizer('/api/data-visual');

visualizer.visualize('my-chart', {
  sql: "SELECT * FROM sales_data",
  chart_type: "bar",
  x_field: "month",
  y_fields: ["revenue"],
  title: "Monthly Revenue"
});
```

## 8. 后端 API 集成说明

### 8.1 后端 API 响应格式

基于最新的 `DataVisualTool` 实现，后端 API 应该返回 `ToolResultExpanded` 格式：

```json
{
  "output": "Visualization created successfully. Chart saved to: ./workdir/charts/chart_20231201_143022_bar.png\nData rows: 150, Chart type: bar",
  "data": [
    {"month": "Jan", "sales": 1000, "profit": 200},
    {"month": "Feb", "sales": 1200, "profit": 250},
    {"month": "Mar", "sales": 1100, "profit": 220}
  ],
  "system": "Data visualization completed: bar chart with 2 y-field(s)",
  "error": null
}
```

### 8.2 错误响应格式

```json
{
  "output": null,
  "data": null,
  "system": null,
  "error": "Missing fields in query result: [sales]. Available fields: [month, revenue]"
}
```

### 8.3 前端数据处理

前端主要使用 `data` 字段中的结构化数据来渲染图表，而 `output` 字段提供后端处理信息，`system` 字段提供执行状态。

```javascript
// 处理后端响应
function processBackendResponse(response) {
  if (response.error) {
    throw new Error(response.error);
  }
  
  return {
    chartData: response.data,           // 用于图表渲染
    processingInfo: response.output,    // 后端处理信息
    systemInfo: response.system        // 系统状态信息
  };
}
```

## 9. 数据流架构图

```
前端请求参数
     ↓
┌─────────────────────┐
│   DataVisualTool    │
│   (后端工具)         │
├─────────────────────┤
│ 1. 执行SQL查询       │
│ 2. 创建matplotlib图表│
│ 3. 保存PNG文件       │
│ 4. 返回结构化数据     │
└─────────────────────┘
     ↓
ToolResultExpanded
├─ output: 图表文件信息
├─ data: DataFrame记录 ──→ 前端ECharts渲染
├─ system: 执行状态
└─ error: 错误信息
```

## 总结

本指南提供了基于 MyAgent DataVisualTool 参数的完整 ECharts 前端实现方案，包括：

1. **参数映射**: DataVisualTool 参数到 ECharts 配置的转换
2. **图表类型支持**: 饼图、柱状图、折线图、散点图
3. **多字段支持**: 支持多个 y_fields 在同一图表中显示
4. **数据处理**: 利用后端返回的结构化数据（data字段）进行前端渲染
5. **错误处理**: 完善的错误处理和用户反馈
6. **响应式设计**: 自适应不同屏幕尺寸
7. **统一接口**: 提供统一的图表创建接口
8. **双重输出**: 后端生成PNG文件，前端使用相同数据创建交互式图表

### 核心优势

- **数据一致性**: 前后端使用相同的数据源确保图表一致性
- **灵活性**: 前端可以创建交互式图表，后端提供静态图表文件
- **可扩展性**: 通过 `ToolResultExpanded` 的 `data` 字段可以传递丰富的结构化数据
- **分离关注点**: 后端专注数据处理，前端专注用户体验

通过这个指南，前端开发者可以轻松地将 MyAgent 的数据可视化功能集成到 Web 应用中，同时享受后端强大的数据处理能力和前端灵活的交互体验。