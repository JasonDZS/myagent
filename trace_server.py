#!/usr/bin/env python3
"""
Simple HTTP server to serve trace files and provide API endpoints.

Usage:
    python trace_server.py [--port 8000] [--traces-dir workdir/traces]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Global configuration
TRACES_DIR = Path("workdir/traces")
STATIC_DIR = Path(".")


def scan_trace_files(traces_dir: Path) -> List[Dict]:
    """Scan the traces directory for JSON files and extract metadata."""
    trace_files = []
    
    if not traces_dir.exists():
        return trace_files
    
    for file_path in traces_dir.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract metadata from the file
            metadata = {
                "filename": file_path.name,
                "filepath": str(file_path),
                "file_size": file_path.stat().st_size,
                "modified_time": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                "created_time": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
            }
            
            # If it's an exported trace file with metadata
            if "metadata" in data and "traces" in data:
                metadata.update({
                    "type": "exported_traces",
                    "export_time": data["metadata"].get("export_time"),
                    "total_traces": data["metadata"].get("total_traces", 0),
                    "exported_count": data["metadata"].get("exported_count", 0),
                    "traces_preview": [
                        {
                            "id": trace.get("id"),
                            "name": trace.get("name"),
                            "status": trace.get("status"),
                            "start_time": trace.get("start_time"),
                            "runs_count": len(trace.get("runs", []))
                        }
                        for trace in data["traces"][:3]  # Preview first 3 traces
                    ]
                })
            # If it's a single trace file
            elif "id" in data and "runs" in data:
                metadata.update({
                    "type": "single_trace",
                    "trace_id": data.get("id"),
                    "trace_name": data.get("name"),
                    "trace_status": data.get("status"),
                    "runs_count": len(data.get("runs", []))
                })
            else:
                metadata["type"] = "unknown"
            
            trace_files.append(metadata)
            
        except Exception as e:
            # If file can't be parsed, still include it with error info
            trace_files.append({
                "filename": file_path.name,
                "filepath": str(file_path),
                "type": "error",
                "error": str(e),
                "file_size": file_path.stat().st_size,
                "modified_time": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            })
    
    # Sort by modification time (newest first)
    trace_files.sort(key=lambda x: x.get("modified_time", ""), reverse=True)
    return trace_files


@app.route("/")
def index():
    """Serve the main trace viewer page."""
    return send_from_directory(STATIC_DIR, "trace_viewer.html")


@app.route("/api/traces")
def list_traces():
    """List all available trace files with metadata."""
    try:
        trace_files = scan_trace_files(TRACES_DIR)
        return jsonify({
            "success": True,
            "trace_files": trace_files,
            "total_files": len(trace_files),
            "traces_dir": str(TRACES_DIR)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/traces/<filename>")
def get_trace_file(filename: str):
    """Get a specific trace file by filename."""
    try:
        file_path = TRACES_DIR / filename
        
        if not file_path.exists():
            return jsonify({
                "success": False,
                "error": f"File {filename} not found"
            }), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify({
            "success": True,
            "filename": filename,
            "data": data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/traces/all")
def get_all_traces():
    """Get all traces from all files, flattened into a single list."""
    try:
        all_traces = []
        trace_files = scan_trace_files(TRACES_DIR)
        
        for file_info in trace_files:
            if file_info.get("type") == "error":
                continue
                
            try:
                file_path = Path(file_info["filepath"])
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract traces based on file type
                if file_info.get("type") == "exported_traces":
                    for trace in data.get("traces", []):
                        trace["_source_file"] = file_info["filename"]
                        all_traces.append(trace)
                elif file_info.get("type") == "single_trace":
                    data["_source_file"] = file_info["filename"]
                    all_traces.append(data)
                    
            except Exception as e:
                print(f"Error processing file {file_info['filename']}: {e}")
                continue
        
        return jsonify({
            "success": True,
            "traces": all_traces,
            "total_traces": len(all_traces),
            "metadata": {
                "export_time": datetime.now().isoformat(),
                "total_files_processed": len([f for f in trace_files if f.get("type") != "error"])
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/search")
def search_traces():
    """Search traces by query parameters."""
    try:
        query = request.args.get("q", "").lower()
        status = request.args.get("status", "")
        run_type = request.args.get("run_type", "")
        limit = int(request.args.get("limit", 50))
        
        # Get all traces
        response = get_all_traces()
        if not response.is_json:
            return response
            
        data = response.get_json()
        if not data.get("success"):
            return response
            
        traces = data["traces"]
        
        # Apply filters
        filtered_traces = []
        for trace in traces:
            # Text search
            if query:
                searchable_text = " ".join([
                    str(trace.get("name", "")),
                    str(trace.get("request", "")),
                    str(trace.get("response", ""))
                ]).lower()
                
                if query not in searchable_text:
                    continue
            
            # Status filter
            if status and trace.get("status") != status:
                continue
                
            # Run type filter (search in runs)
            if run_type:
                has_run_type = any(
                    run.get("run_type") == run_type 
                    for run in trace.get("runs", [])
                )
                if not has_run_type:
                    continue
            
            filtered_traces.append(trace)
        
        # Limit results
        filtered_traces = filtered_traces[:limit]
        
        return jsonify({
            "success": True,
            "traces": filtered_traces,
            "total_results": len(filtered_traces),
            "query_params": {
                "query": query,
                "status": status,
                "run_type": run_type,
                "limit": limit
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/stats")
def get_stats():
    """Get statistics about all traces with flattened structure insights."""
    try:
        # Get all traces
        response = get_all_traces()
        if not response.is_json:
            return response
            
        data = response.get_json()
        if not data.get("success"):
            return response
            
        traces = data["traces"]
        
        # Calculate statistics
        stats = {
            "total_traces": len(traces),
            "status_breakdown": {},
            "run_type_breakdown": {},
            "avg_duration_ms": 0,
            "total_runs": 0,
            "error_rate": 0,
            "recent_activity": [],
            # New flattened structure insights
            "structure_analysis": {
                "flattened_traces": 0,
                "legacy_traces": 0,
                "think_to_tool_ratio": 0,
                "avg_tools_per_trace": 0
            }
        }
        
        total_duration = 0
        duration_count = 0
        think_count = 0
        tool_count = 0
        
        for trace in traces:
            # Status breakdown
            status = trace.get("status", "unknown")
            stats["status_breakdown"][status] = stats["status_breakdown"].get(status, 0) + 1
            
            # Duration calculation
            if trace.get("start_time") and trace.get("end_time"):
                try:
                    start = datetime.fromisoformat(trace["start_time"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(trace["end_time"].replace("Z", "+00:00"))
                    duration = (end - start).total_seconds() * 1000
                    total_duration += duration
                    duration_count += 1
                except:
                    pass
            
            # Run analysis with flattened structure detection
            runs = trace.get("runs", [])
            stats["total_runs"] += len(runs)
            
            has_act_runs = False
            trace_think_count = 0
            trace_tool_count = 0
            
            for run in runs:
                run_type = run.get("run_type", "unknown")
                stats["run_type_breakdown"][run_type] = stats["run_type_breakdown"].get(run_type, 0) + 1
                
                # Track structure type
                if run_type == "act":
                    has_act_runs = True
                elif run_type == "think":
                    trace_think_count += 1
                    think_count += 1
                elif run_type == "tool":
                    trace_tool_count += 1
                    tool_count += 1
            
            # Classify trace structure
            if has_act_runs:
                stats["structure_analysis"]["legacy_traces"] += 1
            else:
                stats["structure_analysis"]["flattened_traces"] += 1
        
        # Calculate averages and rates
        if duration_count > 0:
            stats["avg_duration_ms"] = round(total_duration / duration_count, 2)
        
        if stats["total_traces"] > 0:
            error_count = stats["status_breakdown"].get("error", 0)
            stats["error_rate"] = round((error_count / stats["total_traces"]) * 100, 2)
        
        # Flattened structure insights
        if think_count > 0:
            stats["structure_analysis"]["think_to_tool_ratio"] = round(tool_count / think_count, 2)
        if stats["total_traces"] > 0:
            stats["structure_analysis"]["avg_tools_per_trace"] = round(tool_count / stats["total_traces"], 2)
        
        # Recent activity (last 10 traces)
        stats["recent_activity"] = [
            {
                "id": trace.get("id"),
                "name": trace.get("name"),
                "status": trace.get("status"),
                "start_time": trace.get("start_time"),
                "runs_count": len(trace.get("runs", [])),
                "structure": "flattened" if not any(run.get("run_type") == "act" for run in trace.get("runs", [])) else "legacy"
            }
            for trace in sorted(traces, key=lambda x: x.get("start_time", ""), reverse=True)[:10]
        ]
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/structure-analysis")
def analyze_trace_structure():
    """Analyze trace structure patterns and provide insights on flattened vs legacy structures."""
    try:
        # Get all traces
        response = get_all_traces()
        if not response.is_json:
            return response
            
        data = response.get_json()
        if not data.get("success"):
            return response
            
        traces = data["traces"]
        
        analysis = {
            "summary": {
                "total_traces": len(traces),
                "flattened_traces": 0,
                "legacy_traces": 0,
                "migration_progress": 0  # percentage of flattened traces
            },
            "structure_patterns": {
                "think_only": 0,      # traces with only think runs
                "think_tool": 0,      # flattened: think + tool
                "think_act_tool": 0,  # legacy: think + act + tool
                "other": 0
            },
            "performance_comparison": {
                "flattened": {
                    "avg_runs_per_trace": 0,
                    "avg_duration_ms": 0,
                    "total_traces": 0
                },
                "legacy": {
                    "avg_runs_per_trace": 0,
                    "avg_duration_ms": 0,
                    "total_traces": 0
                }
            },
            "examples": {
                "flattened": [],
                "legacy": []
            }
        }
        
        flattened_durations = []
        legacy_durations = []
        flattened_run_counts = []
        legacy_run_counts = []
        
        for trace in traces:
            runs = trace.get("runs", [])
            run_types = [run.get("run_type", "unknown") for run in runs]
            
            has_think = "think" in run_types
            has_act = "act" in run_types  
            has_tool = "tool" in run_types
            
            # Duration calculation
            duration_ms = None
            if trace.get("start_time") and trace.get("end_time"):
                try:
                    start = datetime.fromisoformat(trace["start_time"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(trace["end_time"].replace("Z", "+00:00"))
                    duration_ms = (end - start).total_seconds() * 1000
                except:
                    pass
            
            # Classify structure
            if has_act:
                # Legacy structure
                analysis["summary"]["legacy_traces"] += 1
                analysis["structure_patterns"]["think_act_tool"] += 1
                
                if duration_ms:
                    legacy_durations.append(duration_ms)
                legacy_run_counts.append(len(runs))
                
                # Add example
                if len(analysis["examples"]["legacy"]) < 3:
                    analysis["examples"]["legacy"].append({
                        "id": trace.get("id"),
                        "name": trace.get("name"),
                        "runs_count": len(runs),
                        "run_types": list(set(run_types)),
                        "duration_ms": duration_ms
                    })
                    
            else:
                # Flattened structure
                analysis["summary"]["flattened_traces"] += 1
                
                if has_think and has_tool:
                    analysis["structure_patterns"]["think_tool"] += 1
                elif has_think and not has_tool:
                    analysis["structure_patterns"]["think_only"] += 1
                else:
                    analysis["structure_patterns"]["other"] += 1
                
                if duration_ms:
                    flattened_durations.append(duration_ms)
                flattened_run_counts.append(len(runs))
                
                # Add example
                if len(analysis["examples"]["flattened"]) < 3:
                    analysis["examples"]["flattened"].append({
                        "id": trace.get("id"),
                        "name": trace.get("name"),
                        "runs_count": len(runs),
                        "run_types": list(set(run_types)),
                        "duration_ms": duration_ms
                    })
        
        # Calculate migration progress
        if analysis["summary"]["total_traces"] > 0:
            analysis["summary"]["migration_progress"] = round(
                (analysis["summary"]["flattened_traces"] / analysis["summary"]["total_traces"]) * 100, 1
            )
        
        # Performance comparison
        if flattened_durations:
            analysis["performance_comparison"]["flattened"]["avg_duration_ms"] = round(
                sum(flattened_durations) / len(flattened_durations), 2
            )
            analysis["performance_comparison"]["flattened"]["total_traces"] = len(flattened_durations)
        
        if legacy_durations:
            analysis["performance_comparison"]["legacy"]["avg_duration_ms"] = round(
                sum(legacy_durations) / len(legacy_durations), 2
            )
            analysis["performance_comparison"]["legacy"]["total_traces"] = len(legacy_durations)
        
        if flattened_run_counts:
            analysis["performance_comparison"]["flattened"]["avg_runs_per_trace"] = round(
                sum(flattened_run_counts) / len(flattened_run_counts), 1
            )
        
        if legacy_run_counts:
            analysis["performance_comparison"]["legacy"]["avg_runs_per_trace"] = round(
                sum(legacy_run_counts) / len(legacy_run_counts), 1
            )
        
        return jsonify({
            "success": True,
            "analysis": analysis
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def main():
    parser = argparse.ArgumentParser(description="Agent Trace Viewer Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--traces-dir", type=str, default="workdir/traces", 
                       help="Directory containing trace files")
    parser.add_argument("--host", type=str, default="localhost", help="Host to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Set global traces directory
    global TRACES_DIR
    TRACES_DIR = Path(args.traces_dir)
    
    print(f"🚀 Starting Agent Trace Viewer Server")
    print(f"📁 Traces directory: {TRACES_DIR.absolute()}")
    print(f"🌐 Server URL: http://{args.host}:{args.port}")
    print(f"📊 API endpoints:")
    print(f"   - GET /api/traces - List all trace files")
    print(f"   - GET /api/traces/all - Get all traces")
    print(f"   - GET /api/traces/<filename> - Get specific trace file")
    print(f"   - GET /api/search?q=<query> - Search traces")
    print(f"   - GET /api/stats - Get trace statistics (with flattened insights)")
    print(f"   - GET /api/structure-analysis - Analyze flattened vs legacy structures")
    print()
    
    # Check if traces directory exists
    if not TRACES_DIR.exists():
        print(f"⚠️  Warning: Traces directory {TRACES_DIR} does not exist")
        print(f"   Creating directory...")
        TRACES_DIR.mkdir(parents=True, exist_ok=True)
    
    # List existing trace files
    trace_files = scan_trace_files(TRACES_DIR)
    if trace_files:
        print(f"📋 Found {len(trace_files)} trace files:")
        for file_info in trace_files[:5]:  # Show first 5
            print(f"   - {file_info['filename']} ({file_info.get('type', 'unknown')})")
        if len(trace_files) > 5:
            print(f"   ... and {len(trace_files) - 5} more")
    else:
        print(f"📭 No trace files found in {TRACES_DIR}")
    
    print()
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()