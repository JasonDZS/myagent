"""
Storage implementations for trace data.

This module provides different storage backends for persisting
trace and run data.
"""

from abc import ABC
from abc import abstractmethod

from .models import Run
from .models import Trace


class TraceStorage(ABC):
    """Abstract base class for trace storage implementations."""

    @abstractmethod
    async def save_trace(self, trace: Trace) -> None:
        """Save a trace to storage."""
        pass

    @abstractmethod
    async def get_trace(self, trace_id: str) -> Trace | None:
        """Retrieve a trace by ID."""
        pass

    @abstractmethod
    async def list_traces(self, limit: int = 100, offset: int = 0) -> list[Trace]:
        """List traces with pagination."""
        pass

    @abstractmethod
    async def save_run(self, run: Run) -> None:
        """Save a run to storage."""
        pass

    @abstractmethod
    async def get_run(self, run_id: str) -> Run | None:
        """Retrieve a run by ID."""
        pass

    @abstractmethod
    async def get_runs_by_trace(self, trace_id: str) -> list[Run]:
        """Get all runs for a specific trace."""
        pass

    @abstractmethod
    async def delete_trace(self, trace_id: str) -> bool:
        """Delete a trace and all its runs."""
        pass


class InMemoryTraceStorage(TraceStorage):
    """In-memory implementation of trace storage for development/testing."""

    def __init__(self):
        self._traces: dict[str, Trace] = {}
        self._runs: dict[str, Run] = {}

    async def save_trace(self, trace: Trace) -> None:
        """Save a trace to memory."""
        self._traces[trace.id] = trace
        # Also save all runs
        for run in trace.runs:
            self._runs[run.id] = run

    async def get_trace(self, trace_id: str) -> Trace | None:
        """Retrieve a trace by ID."""
        trace = self._traces.get(trace_id)
        if trace:
            # Rebuild runs list from stored runs
            trace.runs = [
                run for run in self._runs.values() if run.trace_id == trace_id
            ]
        return trace

    async def list_traces(self, limit: int = 100, offset: int = 0) -> list[Trace]:
        """List traces with pagination."""
        traces = list(self._traces.values())
        # Sort by start time (newest first)
        traces.sort(key=lambda t: t.start_time, reverse=True)
        return traces[offset : offset + limit]

    async def save_run(self, run: Run) -> None:
        """Save a run to memory."""
        self._runs[run.id] = run
        # Add to trace if it exists
        if run.trace_id in self._traces:
            trace = self._traces[run.trace_id]
            if run not in trace.runs:
                trace.runs.append(run)

    async def get_run(self, run_id: str) -> Run | None:
        """Retrieve a run by ID."""
        return self._runs.get(run_id)

    async def get_runs_by_trace(self, trace_id: str) -> list[Run]:
        """Get all runs for a specific trace."""
        return [run for run in self._runs.values() if run.trace_id == trace_id]

    async def delete_trace(self, trace_id: str) -> bool:
        """Delete a trace and all its runs."""
        if trace_id not in self._traces:
            return False

        # Delete all runs for this trace
        run_ids_to_delete = [
            run_id for run_id, run in self._runs.items() if run.trace_id == trace_id
        ]
        for run_id in run_ids_to_delete:
            del self._runs[run_id]

        # Delete the trace
        del self._traces[trace_id]
        return True

    def clear(self) -> None:
        """Clear all data from memory."""
        self._traces.clear()
        self._runs.clear()

    @property
    def trace_count(self) -> int:
        """Get total number of traces."""
        return len(self._traces)

    @property
    def run_count(self) -> int:
        """Get total number of runs."""
        return len(self._runs)
