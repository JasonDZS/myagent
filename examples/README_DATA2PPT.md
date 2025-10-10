# Data to PPT Examples

This directory contains examples for generating PPT presentations in JSON format using the myagent framework.

## Examples

### 1. `data2ppt_simple.py` - Simple PPT Generator

A straightforward example that generates professional PPT slides in JSON format based on user topics.

**Features:**
- Generates well-structured PPT slides with charts
- Supports multiple chart types: bar, line, pie, area
- Single and double chart layouts
- Outputs JSON format compatible with PPT renderers

**Usage:**

```bash
# Basic usage with default topic
uv run python examples/data2ppt_simple.py

# Custom topic
uv run python examples/data2ppt_simple.py "创建一个关于2024年产品销售分析的PPT"

# English topic
uv run python examples/data2ppt_simple.py "Create a quarterly business review presentation"
```

**Output:**
- JSON file saved to: `./workdir/ppt/presentation.json`
- Includes slides with charts and data visualizations

### 2. `data2ppt.py` - Database-Driven PPT Generator

A comprehensive example that analyzes database data and generates PPT presentations.

**Features:**
- Connects to MySQL or SQLite databases
- Analyzes data using SQL queries
- Generates data-driven PPT slides with insights
- Supports schema inspection and data querying

**Prerequisites:**

For SQLite (default):
```bash
export DB_TYPE=sqlite
export SQLITE_DATABASE=./your_database.db
```

For MySQL:
```bash
export DB_TYPE=mysql
export MYSQL_HOST=localhost
export MYSQL_USER=your_user
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=your_database
export MYSQL_PORT=3306  # optional
```

**Usage:**

```bash
# With SQLite
DB_TYPE=sqlite SQLITE_DATABASE=./data.db uv run python examples/data2ppt.py "分析用户数据并生成报告"

# With MySQL (requires pymysql)
uv run python examples/data2ppt.py "分析销售数据，生成季度报告"
```

## PPT JSON Format

The generated JSON follows this structure:

```json
[
  {
    "id": 1,
    "title": "Slide Title",
    "text": "Slide content text",
    "charts": [
      {
        "type": "bar",
        "title": "Chart Title",
        "data": [
          {"name": "Category 1", "value": 100},
          {"name": "Category 2", "value": 150}
        ],
        "horizontal": false
      }
    ],
    "layout": "single"
  }
]
```

### Field Specifications

**Required Fields:**
- `id` (integer): Unique slide identifier (starting from 1)
- `title` (string): Slide title
- `text` (string): Slide content/description

**Optional Fields:**
- `charts` (array): Array of chart objects
  - `type` (string): Chart type - "bar", "line", "pie", "area" (default: "bar")
  - `title` (string): Chart title
  - `data` (array): Data points with `name` (string) and `value` (number)
  - `horizontal` (boolean): For bar charts, whether to display horizontally
- `layout` (string): "single" (1 chart) or "double" (2 charts side-by-side)

## Chart Types

### Bar Chart (`type: "bar"`)
- Default chart type
- Supports vertical and horizontal orientations
- Multi-color columns
- Good for comparing categories

### Line Chart (`type: "line"`)
- Shows trends over time
- Smooth curves with data points highlighted
- Best for sequential/time-series data

### Pie Chart (`type: "pie"`)
- Displays proportions and percentages
- Shows part-to-whole relationships
- Includes legend and percentage labels

### Area Chart (`type: "area"`)
- Emphasizes magnitude of change over time
- Gradient fill from top to bottom
- Good for cumulative data

## Examples

### Text-Only Slide
```json
{
  "id": 1,
  "title": "Introduction",
  "text": "Welcome to our presentation..."
}
```

### Single Chart Slide
```json
{
  "id": 2,
  "title": "Quarterly Sales",
  "text": "Sales performance by quarter shows steady growth.",
  "charts": [
    {
      "type": "line",
      "title": "Q1-Q4 Sales Trend",
      "data": [
        {"name": "Q1", "value": 2800},
        {"name": "Q2", "value": 3000},
        {"name": "Q3", "value": 3200},
        {"name": "Q4", "value": 3800}
      ]
    }
  ],
  "layout": "single"
}
```

### Double Chart Slide
```json
{
  "id": 3,
  "title": "Revenue vs Expenses",
  "text": "Financial comparison for the current period.",
  "charts": [
    {
      "type": "pie",
      "title": "Revenue Sources",
      "data": [
        {"name": "Product Sales", "value": 1938},
        {"name": "Services", "value": 912}
      ]
    },
    {
      "type": "pie",
      "title": "Expense Breakdown",
      "data": [
        {"name": "Operations", "value": 1329},
        {"name": "Marketing", "value": 604},
        {"name": "R&D", "value": 484}
      ]
    }
  ],
  "layout": "double"
}
```

## References

For complete PPT format specification, see: `docs/PPT_FORMAT.md`
