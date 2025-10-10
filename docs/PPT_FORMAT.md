# PPT 内容格式文档

## 概述

本文档说明了 AI 数据报告生成平台中 PPT 幻灯片的数据格式和渲染规范。

## 数据结构

### Slide 接口

幻灯片的核心数据结构定义在 `src/lib/mockData.ts` 中：

```typescript
export interface Slide {
  id: number;              // 幻灯片唯一标识
  title: string;           // 幻灯片标题
  text: string;            // 幻灯片正文内容
  charts?: Array<{         // 可选的图表数组
    data: Array<{ name: string; value: number }>;
    title?: string;        // 图表标题（可选）
    horizontal?: boolean;  // 是否横向显示（可选，默认 false）
  }>;
  layout?: "single" | "double";  // 布局类型（可选，默认 "single"）
}
```

## 字段说明

### 必填字段

#### `id: number`
- **说明**：幻灯片的唯一标识符
- **用途**：用于 React 列表渲染的 key 值和编辑时识别特定幻灯片
- **示例**：`1`, `2`, `3`

#### `title: string`
- **说明**：幻灯片的主标题
- **渲染**：使用 `<h1>` 标签，支持编辑模式下的内联编辑
- **样式**：大标题样式，底部有间距
- **示例**：`"数据分析报告概览"`, `"产品类型与销售额分布"`

#### `text: string`
- **说明**：幻灯片的正文内容
- **渲染**：使用 `<p>` 标签，支持多行文本和换行符 `\n`
- **样式**：次要文本颜色（muted-foreground）
- **示例**：
```typescript
text: "本报告基于上传的销售数据，通过 AI 自动分析生成。"
```

### 可选字段

#### `charts?: Array<ChartData>`

图表数组，每个图表对象包含：

##### `type?: "bar" | "line" | "pie" | "area"`
- **说明**：图表类型
- **默认值**：`"bar"`（柱状图）
- **可选值**：
  - `"bar"` - 柱状图
  - `"line"` - 折线图
  - `"pie"` - 饼图
  - `"area"` - 面积图

##### `data: Array<{ name: string; value: number }>`
- **说明**：图表数据点数组
- **格式**：每个数据点包含名称和数值
- **示例**：
```typescript
data: [
  { name: "护肤类", value: 241628 },
  { name: "护发类", value: 174523 },
  { name: "化妆品类", value: 161498 }
]
```

##### `title?: string`
- **说明**：图表的标题
- **用途**：显示在图表上方
- **示例**：`"不同产品类型的销售额对比"`

##### `horizontal?: boolean`
- **说明**：控制柱状图方向（仅对 `type="bar"` 有效）
- **默认值**：`false`（垂直柱状图）
- **true**：横向柱状图
- **false**：纵向柱状图

#### `layout?: "single" | "double"`
- **说明**：图表布局方式
- **默认值**：`"single"`
- **single**：单列布局（`grid-cols-1`），适合一个图表
- **double**：双列布局（`grid-cols-2`），适合两个图表并排显示

## 布局规则

### 无图表幻灯片

当 `charts` 为空或未定义时：
- 仅显示标题和正文
- 正文占据主要空间

### 单图表布局

```typescript
{
  id: 3,
  title: "客户群体与销售量分析",
  text: "客户群体分析显示...",
  charts: [
    {
      title: "各客户群体销售量对比",
      data: [...],
      horizontal: false
    }
  ],
  layout: "single"  // 可省略，默认为 single
}
```

**渲染效果**：
- 标题 + 正文在顶部
- 单个图表在下方占据全宽

### 双图表布局

```typescript
{
  id: 2,
  title: "收入与支出分析",
  text: "本季度总收入 2,850 万元...",
  charts: [
    {
      title: "收入来源分布",
      data: [...],
      horizontal: false
    },
    {
      title: "支出构成分析",
      data: [...],
      horizontal: false
    }
  ],
  layout: "double"  // 必须指定为 double
}
```

**渲染效果**：
- 标题 + 正文在顶部
- 两个图表并排显示（50% 宽度各一个）

## 编辑模式

### 可编辑字段

在编辑模式下（`isEditing={true}`），以下字段支持内联编辑：

1. **标题**（`title`）
   - `contentEditable={true}`
   - 失焦时触发 `onBlur` 事件保存
   - 显示虚线轮廓提示可编辑

2. **正文**（`text`）
   - `contentEditable={true}`
   - 失焦时触发 `onBlur` 事件保存
   - 显示虚线轮廓提示可编辑

### 编辑回调

```typescript
interface SlideContentProps {
  slide: SlideData;
  isEditing?: boolean;
  onTextChange?: (id: number, field: string, value: string) => void;
}
```

编辑完成时调用：
```typescript
onTextChange(slide.id, "title", newTitleValue);
onTextChange(slide.id, "text", newTextValue);
```

## 样式规范

### 容器
- 白色背景 (`bg-white`)
- 圆角 (`rounded-lg`)
- 内边距 12 单位 (`p-12`)
- 全宽全高 (`w-full h-full`)
- Flex 纵向布局 (`flex flex-col`)

### 标题区域
- 底部间距 8 单位 (`mb-8`)
- 标题与正文间距 6 单位 (`mb-6`)

### 图表区域
- 占据剩余空间 (`flex-1`)
- 使用 Grid 布局
- 图表间距 8 单位 (`gap-8`)

## 完整示例

### 示例 1：仅文本幻灯片

```typescript
{
  id: 1,
  title: "数据分析报告概览",
  text: "本报告基于上传的销售数据，通过 AI 自动分析生成。涵盖产品类型分布、客户群体特征、销售趋势等多个维度的深度洞察。报告共包含 5 个分析页面，帮助您快速了解业务现状和优化方向。",
  layout: "single"
}
```

### 示例 2：折线图幻灯片

```typescript
{
  id: 4,
  title: "月度销售趋势分析",
  text: "过去 6 个月的销售数据呈现稳步上升趋势，总体增长率达到 23.5%。",
  charts: [
    {
      type: "line",
      title: "月度销售额变化趋势",
      data: [
        { name: "1月", value: 85423 },
        { name: "2月", value: 92156 },
        { name: "3月", value: 118963 },
        { name: "4月", value: 103847 },
        { name: "5月", value: 125632 },
        { name: "6月", value: 114628 }
      ]
    }
  ],
  layout: "single"
}
```

### 示例 3：饼图双图表幻灯片

```typescript
{
  id: 2,
  title: "收入与支出分析",
  text: "本季度总收入 2,850 万元，主要来源为产品销售（68%）和服务收入（32%）。",
  charts: [
    {
      type: "pie",
      title: "收入来源分布",
      data: [
        { name: "产品销售", value: 1938 },
        { name: "服务收入", value: 912 }
      ]
    },
    {
      type: "pie",
      title: "支出构成分析",
      data: [
        { name: "运营成本", value: 1329 },
        { name: "营销费用", value: 604 },
        { name: "研发投入", value: 484 }
      ]
    }
  ],
  layout: "double"
}
```

### 示例 4：面积图与柱状图组合

```typescript
{
  id: 2,
  title: "系统性能指标",
  text: "平均响应时间 120ms，P99 响应时间 850ms，均在合理范围内。",
  charts: [
    {
      type: "area",
      title: "每日平均响应时间（ms）",
      data: [
        { name: "第1周", value: 115 },
        { name: "第2周", value: 122 },
        { name: "第3周", value: 118 },
        { name: "第4周", value: 125 }
      ]
    },
    {
      type: "bar",
      title: "错误类型分布",
      data: [
        { name: "超时错误", value: 45 },
        { name: "4xx错误", value: 32 },
        { name: "5xx错误", value: 18 },
        { name: "其他错误", value: 5 }
      ],
      horizontal: true
    }
  ],
  layout: "double"
}
```

## 注意事项

1. **必填字段**：`id`、`title`、`text` 必须提供
2. **图表数量**：
   - `layout: "single"` 时建议 1 个图表
   - `layout: "double"` 时建议 2 个图表
   - 超过 2 个图表时会自动平铺（双列布局下每行 2 个）
3. **数据类型**：图表数据的 `value` 必须是 `number` 类型
4. **换行处理**：正文 `text` 中的 `\n` 会被保留并正确渲染为换行
5. **编辑限制**：当前版本图表数据不支持可视化编辑，仅标题和正文可编辑

## 图表类型详解

图表通过 `ChartBlock.tsx` 组件渲染，使用 Recharts 库，支持以下四种类型：

### 1. 柱状图（Bar Chart）- `type: "bar"`
- **默认类型**：未指定 `type` 时默认使用柱状图
- **方向控制**：
  - `horizontal={false}` 或未指定：垂直柱状图（从下往上）
  - `horizontal={true}`：横向柱状图（从左往右）
- **适用场景**：对比不同类别的数值大小
- **特点**：多色彩显示，每个柱子不同颜色

### 2. 折线图（Line Chart）- `type: "line"`
- **适用场景**：展示数据随时间或序列变化的趋势
- **特点**：
  - 平滑曲线（`type="monotone"`）
  - 数据点高亮显示
  - 紫色主题色（`#6366f1`）
- **示例**：月度销售趋势、性能变化趋势

### 3. 饼图（Pie Chart）- `type: "pie"`
- **适用场景**：展示各部分占整体的比例关系
- **特点**：
  - 自动显示百分比标签
  - 多色彩扇区
  - 包含图例（Legend）
- **示例**：收入来源分布、支出构成分析

### 4. 面积图（Area Chart）- `type: "area"`
- **适用场景**：强调数据量随时间的累积效果
- **特点**：
  - 渐变填充（从深到浅）
  - 平滑曲线
  - 紫色主题色系
- **示例**：累计销售额、系统响应时间趋势

## 图表样式配置

### 颜色方案
```typescript
// 柱状图和饼图使用的颜色数组（循环使用）
COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981']
```

### 统一样式
- 高度：固定 250px
- 工具提示（Tooltip）：白色背景，圆角边框
- 网格线：虚线，透明度 30%
- 自动响应式尺寸

## 相关文件

- 数据定义：`src/lib/mockData.ts`
- 内容渲染：`src/components/SlideContent.tsx`
- 图表组件：`src/components/ChartBlock.tsx`
- 图表子组件：
  - 折线图：`src/components/charts/LineChartComponent.tsx`
  - 饼图：`src/components/charts/PieChartComponent.tsx`
  - 面积图：`src/components/charts/AreaChartComponent.tsx`
- 幻灯片查看：`src/components/SlideViewer.tsx`
- 幻灯片编辑：`src/components/SlideEditor.tsx`
