"""
Data models for tracing agent execution.

This module defines the core data structures used for tracking
agent execution flows, similar to LangSmith traces and runs.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class RunType(str, Enum):
    """Types of runs that can be tracked."""
    
    AGENT = "agent"              # Agent execution
    THINK = "think"              # Agent thinking process
    ACT = "act"                  # Agent action execution
    TOOL = "tool"                # Tool call
    LLM = "llm"                  # Language model call
    RETRIEVAL = "retrieval"      # Document retrieval
    PREPROCESSING = "preprocessing"  # Data preprocessing
    POSTPROCESSING = "postprocessing"  # Data postprocessing
    CHAIN = "chain"              # Chain of operations
    CUSTOM = "custom"            # Custom operation


class RunStatus(str, Enum):
    """Status of a run."""
    
    PENDING = "pending"          # Not started yet
    RUNNING = "running"          # Currently executing
    SUCCESS = "success"          # Completed successfully
    ERROR = "error"              # Failed with error
    CANCELLED = "cancelled"      # Cancelled before completion


class TraceMetadata(BaseModel):
    """Metadata for a trace."""
    
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    environment: Optional[str] = Field(None, description="Environment (dev/staging/prod)")
    version: Optional[str] = Field(None, description="Agent version")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class Run(BaseModel):
    """Represents a single operation/step in the agent execution."""
    
    # Core identifiers
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique run identifier")
    trace_id: str = Field(..., description="Parent trace identifier")
    parent_run_id: Optional[str] = Field(None, description="Parent run identifier for nested runs")
    
    # Run details
    name: str = Field(..., description="Name of the operation")
    run_type: RunType = Field(..., description="Type of the run")
    status: RunStatus = Field(default=RunStatus.PENDING, description="Current status")
    
    # Timing
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = Field(None, description="End time when completed")
    
    # Input/Output
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Output results")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if failed")
    error_type: Optional[str] = Field(None, description="Error type/class")
    stacktrace: Optional[str] = Field(None, description="Full error stacktrace")
    
    # Additional data
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Tags for this run")
    
    # Metrics
    token_usage: Optional[Dict[str, int]] = Field(None, description="Token usage for LLM calls")
    cost: Optional[float] = Field(None, description="Cost in USD")
    latency_ms: Optional[float] = Field(None, description="Latency in milliseconds")
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def start(self) -> "Run":
        """Mark the run as started."""
        self.status = RunStatus.RUNNING
        self.start_time = datetime.now(timezone.utc)
        return self
    
    def end(self, outputs: Optional[Dict[str, Any]] = None) -> "Run":
        """Mark the run as successfully completed."""
        self.status = RunStatus.SUCCESS
        self.end_time = datetime.now(timezone.utc)
        if outputs:
            self.outputs.update(outputs)
        self._calculate_latency()
        return self
    
    def fail(self, error: str, error_type: Optional[str] = None, stacktrace: Optional[str] = None) -> "Run":
        """Mark the run as failed."""
        self.status = RunStatus.ERROR
        self.end_time = datetime.now(timezone.utc)
        self.error = error
        self.error_type = error_type
        self.stacktrace = stacktrace
        self._calculate_latency()
        return self
    
    def cancel(self) -> "Run":
        """Mark the run as cancelled."""
        self.status = RunStatus.CANCELLED
        self.end_time = datetime.now(timezone.utc)
        self._calculate_latency()
        return self
    
    def _calculate_latency(self):
        """Calculate and set latency in milliseconds."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.latency_ms = delta.total_seconds() * 1000
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get duration in milliseconds."""
        return self.latency_ms
    
    @property
    def is_completed(self) -> bool:
        """Check if the run is completed (success, error, or cancelled)."""
        return self.status in [RunStatus.SUCCESS, RunStatus.ERROR, RunStatus.CANCELLED]


class Trace(BaseModel):
    """Represents a complete trace of user request execution."""
    
    # Core identifiers
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique trace identifier")
    name: str = Field(..., description="Name/description of the trace")
    
    # Timing
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = Field(None, description="End time when completed")
    
    # Request context
    request: Optional[str] = Field(None, description="Original user request")
    response: Optional[str] = Field(None, description="Final response")
    
    # Runs
    runs: List[Run] = Field(default_factory=list, description="List of runs in this trace")
    
    # Metadata
    metadata: TraceMetadata = Field(default_factory=TraceMetadata, description="Trace metadata")
    status: RunStatus = Field(default=RunStatus.PENDING, description="Overall trace status")
    
    # Metrics
    total_cost: Optional[float] = Field(None, description="Total cost in USD")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def add_run(self, run: Run) -> "Trace":
        """Add a run to this trace."""
        run.trace_id = self.id
        self.runs.append(run)
        return self
    
    def start(self) -> "Trace":
        """Mark the trace as started."""
        self.status = RunStatus.RUNNING
        self.start_time = datetime.now(timezone.utc)
        return self
    
    def end(self, response: Optional[str] = None) -> "Trace":
        """Mark the trace as completed."""
        self.end_time = datetime.now(timezone.utc)
        if response:
            self.response = response
        
        # Determine overall status based on runs
        if any(run.status == RunStatus.ERROR for run in self.runs):
            self.status = RunStatus.ERROR
        elif any(run.status == RunStatus.CANCELLED for run in self.runs):
            self.status = RunStatus.CANCELLED
        elif all(run.is_completed for run in self.runs):
            self.status = RunStatus.SUCCESS
        else:
            self.status = RunStatus.RUNNING
        
        # Calculate totals
        self._calculate_totals()
        return self
    
    def fail(self, error: str) -> "Trace":
        """Mark the trace as failed."""
        self.status = RunStatus.ERROR
        self.end_time = datetime.now(timezone.utc)
        self._calculate_totals()
        return self
    
    def _calculate_totals(self):
        """Calculate total metrics from all runs."""
        total_cost = 0.0
        total_tokens = 0
        
        for run in self.runs:
            if run.cost:
                total_cost += run.cost
            if run.token_usage:
                total_tokens += sum(run.token_usage.values())
        
        self.total_cost = total_cost if total_cost > 0 else None
        self.total_tokens = total_tokens if total_tokens > 0 else None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get total duration in milliseconds."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return None
    
    def get_runs_by_type(self, run_type: RunType) -> List[Run]:
        """Get all runs of a specific type."""
        return [run for run in self.runs if run.run_type == run_type]
    
    def get_failed_runs(self) -> List[Run]:
        """Get all failed runs."""
        return [run for run in self.runs if run.status == RunStatus.ERROR]
    
    def get_root_runs(self) -> List[Run]:
        """Get all top-level runs (no parent)."""
        return [run for run in self.runs if run.parent_run_id is None]
    
    def get_child_runs(self, parent_run_id: str) -> List[Run]:
        """Get all child runs of a specific parent."""
        return [run for run in self.runs if run.parent_run_id == parent_run_id]