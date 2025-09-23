# 🔍 Agent Trace Viewer

A comprehensive web-based visualization tool for analyzing agent execution traces, similar to LangSmith's trace viewer. This tool provides detailed insights into agent workflows, run hierarchies, and performance metrics.

## ✨ Features

### 📊 Trace List View
- **Overview**: Browse all available traces with key metadata
- **Status Indicators**: Visual status badges (success, error, running)
- **Quick Stats**: Duration, run count, and timing information
- **Search & Filter**: Find traces by content, status, or run type

### 🌳 Interactive Execution Tree
- **Hierarchical View**: Visualize parent-child relationships between runs
- **Expandable Cards**: Click to see detailed run information
- **Run Type Badges**: Color-coded badges for different run types (AGENT, THINK, ACT, TOOL, LLM)
- **Rich Details**: Inputs, outputs, timing, errors, and metadata for each run

### 🎯 Run Type Support
Different run types display specialized information:

- **AGENT**: Step execution with context and state
- **THINK**: Thinking process with decision making
- **ACT**: Action execution with results
- **TOOL**: Tool calls with parameters and responses
- **LLM**: Language model calls with token usage and cost
- **CUSTOM**: User-defined run types

### 📈 Analytics Dashboard
- **Real-time Stats**: Total traces, runs, error rates, and average duration
- **Performance Metrics**: Duration analysis and bottleneck identification
- **Error Tracking**: Failed runs and error patterns

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Modern web browser

### Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements-trace-viewer.txt
   ```

2. **Ensure Trace Directory Exists**
   ```bash
   mkdir -p workdir/traces
   ```

3. **Start the Server**
   ```bash
   python trace_server.py
   ```

4. **Open in Browser**
   Navigate to `http://localhost:8000`

### Alternative Ports/Hosts
```bash
# Custom port
python trace_server.py --port 8080

# Custom traces directory
python trace_server.py --traces-dir /path/to/traces

# External access
python trace_server.py --host 0.0.0.0

# Debug mode
python trace_server.py --debug
```

## 📁 Trace File Format

The viewer supports two trace file formats:

### 1. Exported Traces (Recommended)
```json
{
  "metadata": {
    "export_time": "2025-09-23T16:23:44.042477",
    "total_traces": 1,
    "exported_count": 1
  },
  "traces": [
    {
      "id": "trace-uuid",
      "name": "agent_execution",
      "start_time": "2025-09-23T08:23:01.776002+00:00",
      "end_time": "2025-09-23T08:23:44.042067+00:00",
      "request": "User request text",
      "response": "Agent response text",
      "status": "success",
      "runs": [...]
    }
  ]
}
```

### 2. Single Trace Files
```json
{
  "id": "trace-uuid",
  "name": "agent_execution",
  "start_time": "2025-09-23T08:23:01.776002+00:00",
  "end_time": "2025-09-23T08:23:44.042067+00:00",
  "request": "User request text",
  "response": "Agent response text",
  "status": "success",
  "runs": [...]
}
```

### Run Structure
Each run contains:
```json
{
  "id": "run-uuid",
  "trace_id": "parent-trace-uuid",
  "parent_run_id": "parent-run-uuid-or-null",
  "name": "run_name",
  "run_type": "agent|think|act|tool|llm|custom",
  "status": "success|error|running|cancelled",
  "start_time": "ISO-timestamp",
  "end_time": "ISO-timestamp",
  "inputs": {...},
  "outputs": {...},
  "error": "error message if failed",
  "error_type": "error class name",
  "stacktrace": "full stacktrace",
  "metadata": {...},
  "token_usage": {...},
  "cost": 0.001,
  "latency_ms": 1234.56
}
```

## 🎛️ API Reference

### GET /api/traces/all
Get all traces from all files.
```json
{
  "success": true,
  "traces": [...],
  "total_traces": 10,
  "metadata": {
    "export_time": "2025-09-23T...",
    "total_files_processed": 5
  }
}
```

### GET /api/traces
List all trace files with metadata.
```json
{
  "success": true,
  "trace_files": [
    {
      "filename": "traces.json",
      "type": "exported_traces",
      "total_traces": 5,
      "file_size": 12345,
      "modified_time": "2025-09-23T..."
    }
  ]
}
```

### GET /api/traces/{filename}
Get specific trace file content.

### GET /api/search
Search traces with query parameters:
- `q`: Text search query
- `status`: Filter by status (success, error, running)
- `run_type`: Filter by run type (agent, tool, llm, etc.)
- `limit`: Maximum results (default: 50)

### GET /api/stats
Get comprehensive statistics about all traces.

## 🎨 UI Components

### Trace List
- **Clickable Items**: Click any trace to view details
- **Status Badges**: Color-coded status indicators
- **Meta Information**: Duration, run count, timestamps
- **Request Preview**: Truncated request text with full view on hover

### Trace Detail View
- **Header Section**: Metadata, timing, and request/response
- **Execution Tree**: Hierarchical view of all runs
- **Expandable Runs**: Click to see detailed run information
- **Rich Content**: JSON-formatted inputs/outputs with syntax highlighting

### Run Cards
- **Type Badges**: Color-coded by run type
- **Timing Info**: Start, end, and duration
- **Status Indicators**: Success, error, running states
- **Nested Structure**: Visual parent-child relationships

### Detail Sections
- **⏱️ Timing**: Start/end times and duration
- **📥 Inputs**: Formatted input parameters
- **📤 Outputs**: Formatted output results
- **❌ Errors**: Error messages and stack traces
- **🎯 Token Usage**: LLM token consumption (when applicable)
- **📋 Metadata**: Additional run metadata

## 🔧 Customization

### Styling
The viewer uses CSS custom properties for easy theming:
```css
:root {
  --primary-color: #3b82f6;
  --success-color: #16a34a;
  --error-color: #dc2626;
  --warning-color: #d97706;
}
```

### Run Type Colors
Each run type has a specific color scheme:
- **AGENT**: Purple (`#7c3aed`)
- **THINK**: Orange (`#d97706`)
- **ACT**: Green (`#16a34a`)
- **TOOL**: Cyan (`#0891b2`)
- **LLM**: Red (`#dc2626`)

## 🐛 Troubleshooting

### Common Issues

1. **No traces showing**
   - Check if `workdir/traces` directory exists
   - Verify JSON files are valid
   - Check server console for errors

2. **API not responding**
   - Ensure Flask and Flask-CORS are installed
   - Check if port 8000 is available
   - Try running with `--debug` flag

3. **JSON parsing errors**
   - Validate trace file JSON format
   - Check for trailing commas or syntax errors
   - Use a JSON validator tool

4. **Missing run details**
   - Verify run objects have required fields
   - Check parent_run_id relationships
   - Ensure run_type is valid

### Debug Mode
Run with debug flag for detailed error messages:
```bash
python trace_server.py --debug
```

## 📝 Development

### Project Structure
```
myagent/
├── trace_viewer.html      # Frontend HTML/CSS/JS
├── trace_server.py        # Backend Flask server
├── requirements-trace-viewer.txt  # Python dependencies
├── workdir/
│   └── traces/           # Trace JSON files
└── TRACE_VIEWER_README.md # This file
```

### Adding New Features

1. **Frontend**: Modify `trace_viewer.html`
2. **Backend**: Add endpoints to `trace_server.py`
3. **API**: Follow the existing JSON response format

### Testing
Place sample trace files in `workdir/traces/` and refresh the viewer.

## 📊 Example Usage

1. **Generate Traces**: Run your agent with tracing enabled
2. **Export Traces**: Use the trace exporter to create JSON files
3. **Start Viewer**: `python trace_server.py`
4. **Analyze**: Browse traces, drill down into runs, identify bottlenecks

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper testing
4. Submit a pull request

## 📄 License

This trace viewer is part of the myagent project and follows the same license terms.

---

**Happy Tracing! 🚀**