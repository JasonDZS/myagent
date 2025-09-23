"""
Export functionality for trace data.

This module provides various export formats for trace and run data,
enabling integration with external tools and analysis platforms.
"""

import json
import csv
from datetime import datetime
from io import StringIO
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from .models import Trace, Run
from .query import TraceFilter, RunFilter, TraceQueryEngine


class TraceExporter:
    """Exporter for trace data in various formats."""
    
    def __init__(self, query_engine: TraceQueryEngine):
        """Initialize with a query engine."""
        self.query_engine = query_engine
    
    async def export_traces_to_json(
        self,
        filters: Optional[TraceFilter] = None,
        file_path: Optional[Union[str, Path]] = None,
        ensure_ascii: bool = False
    ) -> str:
        """Export traces to JSON format."""
        traces_result = await self.query_engine.query_traces(filters)
        traces = traces_result.results
        
        # Convert to serializable format
        export_data = {
            "metadata": {
                "export_time": datetime.now().isoformat(),
                "total_traces": traces_result.total_count,
                "exported_count": len(traces)
            },
            "traces": [trace.dict() for trace in traces]
        }
        
        json_data = json.dumps(export_data, indent=2, default=str, ensure_ascii=ensure_ascii)
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write(json_data)
        
        return json_data
    
    async def export_runs_to_json(
        self,
        filters: Optional[RunFilter] = None,
        file_path: Optional[Union[str, Path]] = None,
        ensure_ascii: bool = False
    ) -> str:
        """Export runs to JSON format."""
        runs_result = await self.query_engine.query_runs(filters)
        runs = runs_result.results
        
        # Convert to serializable format
        export_data = {
            "metadata": {
                "export_time": datetime.now().isoformat(),
                "total_runs": runs_result.total_count,
                "exported_count": len(runs)
            },
            "runs": [run.dict() for run in runs]
        }

        json_data = json.dumps(export_data, indent=2, default=str, ensure_ascii=ensure_ascii)

        if file_path:
            with open(file_path, 'w') as f:
                f.write(json_data)
        
        return json_data
    
    async def export_traces_to_csv(
        self,
        filters: Optional[TraceFilter] = None,
        file_path: Optional[Union[str, Path]] = None
    ) -> str:
        """Export traces to CSV format."""
        traces_result = await self.query_engine.query_traces(filters)
        traces = traces_result.results
        
        # Define CSV columns
        columns = [
            "id", "name", "start_time", "end_time", "duration_ms", "status",
            "request", "response", "total_cost", "total_tokens", "user_id",
            "session_id", "environment", "tags", "run_count", "error_count"
        ]
        
        # Prepare CSV data
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        
        for trace in traces:
            error_count = len([r for r in trace.runs if r.status == "error"])
            
            row = {
                "id": trace.id,
                "name": trace.name,
                "start_time": trace.start_time.isoformat() if trace.start_time else "",
                "end_time": trace.end_time.isoformat() if trace.end_time else "",
                "duration_ms": trace.duration_ms or "",
                "status": trace.status.value,
                "request": trace.request or "",
                "response": trace.response or "",
                "total_cost": trace.total_cost or "",
                "total_tokens": trace.total_tokens or "",
                "user_id": trace.metadata.user_id or "",
                "session_id": trace.metadata.session_id or "",
                "environment": trace.metadata.environment or "",
                "tags": ",".join(trace.metadata.tags),
                "run_count": len(trace.runs),
                "error_count": error_count
            }
            writer.writerow(row)
        
        csv_data = output.getvalue()
        output.close()
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write(csv_data)
        
        return csv_data
    
    async def export_runs_to_csv(
        self,
        filters: Optional[RunFilter] = None,
        file_path: Optional[Union[str, Path]] = None
    ) -> str:
        """Export runs to CSV format."""
        runs_result = await self.query_engine.query_runs(filters)
        runs = runs_result.results
        
        # Define CSV columns
        columns = [
            "id", "trace_id", "parent_run_id", "name", "run_type", "status",
            "start_time", "end_time", "duration_ms", "error", "error_type",
            "cost", "token_usage", "inputs", "outputs"
        ]
        
        # Prepare CSV data
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        
        for run in runs:
            row = {
                "id": run.id,
                "trace_id": run.trace_id,
                "parent_run_id": run.parent_run_id or "",
                "name": run.name,
                "run_type": run.run_type.value,
                "status": run.status.value,
                "start_time": run.start_time.isoformat() if run.start_time else "",
                "end_time": run.end_time.isoformat() if run.end_time else "",
                "duration_ms": run.duration_ms or "",
                "error": run.error or "",
                "error_type": run.error_type or "",
                "cost": run.cost or "",
                "token_usage": json.dumps(run.token_usage) if run.token_usage else "",
                "inputs": json.dumps(run.inputs) if run.inputs else "",
                "outputs": json.dumps(run.outputs) if run.outputs else ""
            }
            writer.writerow(row)
        
        csv_data = output.getvalue()
        output.close()
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write(csv_data)
        
        return csv_data
    
    async def export_trace_summary(
        self,
        filters: Optional[TraceFilter] = None,
        file_path: Optional[Union[str, Path]] = None
    ) -> str:
        """Export a summary report of traces."""
        # Get statistics
        stats = await self.query_engine.get_trace_statistics(filters)
        
        # Get sample traces
        traces_result = await self.query_engine.query_traces(filters)
        traces = traces_result.results[:10]  # Top 10 traces
        
        # Generate summary report
        report_lines = [
            "# Trace Summary Report",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Statistics",
            f"Total Traces: {stats['total_traces']}",
            f"Average Duration: {stats['avg_duration_ms']:.2f}ms",
            f"Total Cost: ${stats['total_cost']:.4f}",
            f"Total Tokens: {stats['total_tokens']}",
            f"Error Rate: {stats['error_rate']:.2%}",
            "",
            "## Status Distribution",
        ]
        
        for status, count in stats['status_distribution'].items():
            percentage = (count / stats['total_traces']) * 100 if stats['total_traces'] > 0 else 0
            report_lines.append(f"- {status}: {count} ({percentage:.1f}%)")
        
        if traces:
            report_lines.extend([
                "",
                "## Sample Traces",
            ])
            
            for i, trace in enumerate(traces, 1):
                duration = f"{trace.duration_ms:.2f}ms" if trace.duration_ms else "N/A"
                cost = f"${trace.total_cost:.4f}" if trace.total_cost else "N/A"
                report_lines.extend([
                    f"### {i}. {trace.name} ({trace.id[:8]}...)",
                    f"- Status: {trace.status.value}",
                    f"- Duration: {duration}",
                    f"- Cost: {cost}",
                    f"- Runs: {len(trace.runs)}",
                    f"- Started: {trace.start_time.isoformat() if trace.start_time else 'N/A'}",
                    ""
                ])
        
        report = "\n".join(report_lines)
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write(report)
        
        return report
    
    def export_trace_tree(self, trace: Trace) -> str:
        """Export a visual tree representation of a trace."""
        lines = [f"Trace: {trace.name} ({trace.id[:8]}...)"]
        lines.append(f"Status: {trace.status.value}")
        lines.append(f"Duration: {trace.duration_ms:.2f}ms" if trace.duration_ms else "Duration: N/A")
        lines.append("")
        
        # Build run hierarchy
        root_runs = [r for r in trace.runs if r.parent_run_id is None]
        
        def add_run_to_tree(run: Run, prefix: str = "", is_last: bool = True):
            # Format run info
            status_icon = "✓" if run.status.value == "success" else "✗" if run.status.value == "error" else "~"
            duration = f"{run.duration_ms:.2f}ms" if run.duration_ms else "N/A"
            
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{status_icon} {run.name} ({run.run_type.value}) - {duration}")
            
            # Add child runs
            child_runs = [r for r in trace.runs if r.parent_run_id == run.id]
            child_prefix = prefix + ("    " if is_last else "│   ")
            
            for i, child in enumerate(child_runs):
                is_last_child = i == len(child_runs) - 1
                add_run_to_tree(child, child_prefix, is_last_child)
        
        # Add all root runs
        for i, root_run in enumerate(root_runs):
            is_last_root = i == len(root_runs) - 1
            add_run_to_tree(root_run, "", is_last_root)
        
        return "\n".join(lines)