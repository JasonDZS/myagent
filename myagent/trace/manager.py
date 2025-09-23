"""
TraceManager for coordinating trace collection and storage.

This module provides the main interface for managing traces and runs
throughout the agent execution lifecycle.
"""

import asyncio
import contextvars
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from ..logger import logger
from .models import Trace, Run, RunType, RunStatus, TraceMetadata
from .storage import TraceStorage, InMemoryTraceStorage


# Context variables for tracking current trace and run
_current_trace: contextvars.ContextVar[Optional[Trace]] = contextvars.ContextVar(
    'current_trace', default=None
)
_current_run: contextvars.ContextVar[Optional[Run]] = contextvars.ContextVar(
    'current_run', default=None
)


class TraceManager:
    """Manages trace collection and storage for agent execution."""
    
    def __init__(self, storage: Optional[TraceStorage] = None, auto_save: bool = True):
        """
        Initialize TraceManager.
        
        Args:
            storage: Storage backend for traces. Defaults to InMemoryTraceStorage.
            auto_save: Whether to automatically save traces and runs to storage.
        """
        self.storage = storage or InMemoryTraceStorage()
        self.auto_save = auto_save
        self._active_traces: Dict[str, Trace] = {}
    
    @asynccontextmanager
    async def trace(
        self,
        name: str,
        request: Optional[str] = None,
        metadata: Optional[Union[TraceMetadata, Dict[str, Any]]] = None,
        **kwargs
    ):
        """
        Context manager for creating and managing a trace.
        
        Args:
            name: Name/description of the trace
            request: Original user request
            metadata: Trace metadata
            **kwargs: Additional metadata fields
        """
        # Create trace metadata
        if isinstance(metadata, dict):
            metadata = TraceMetadata(**metadata)
        elif metadata is None:
            metadata = TraceMetadata()
        
        # Add any additional kwargs to custom_fields
        if kwargs:
            metadata.custom_fields.update(kwargs)
        
        # Create new trace
        trace = Trace(
            name=name,
            request=request,
            metadata=metadata
        ).start()
        
        self._active_traces[trace.id] = trace
        
        # Set trace in context
        token = _current_trace.set(trace)
        
        try:
            logger.info(f"Starting trace: {name} (ID: {trace.id})")
            yield trace
            
            # Mark trace as completed
            trace.end()
            logger.info(f"Completed trace: {name} (Duration: {trace.duration_ms:.2f}ms)")
            
        except Exception as e:
            trace.fail(str(e))
            logger.error(f"Trace failed: {name} - {e}")
            raise
        finally:
            # Save trace if auto_save is enabled
            if self.auto_save:
                await self.storage.save_trace(trace)
            
            # Clean up
            self._active_traces.pop(trace.id, None)
            _current_trace.reset(token)
    
    @asynccontextmanager
    async def run(
        self,
        name: str,
        run_type: RunType,
        inputs: Optional[Dict[str, Any]] = None,
        parent_run_id: Optional[str] = None,
        **metadata
    ):
        """
        Context manager for creating and managing a run.
        
        Args:
            name: Name of the operation
            run_type: Type of the run
            inputs: Input parameters
            parent_run_id: Parent run ID for nested runs
            **metadata: Additional metadata
        """
        # Get current trace
        current_trace = _current_trace.get()
        if not current_trace:
            raise RuntimeError("No active trace found. Use trace() context manager first.")
        
        # Get parent run if not specified
        if parent_run_id is None:
            current_run = _current_run.get()
            if current_run:
                parent_run_id = current_run.id
        
        # Create new run
        run = Run(
            name=name,
            run_type=run_type,
            trace_id=current_trace.id,
            parent_run_id=parent_run_id,
            inputs=inputs or {},
            metadata=metadata
        ).start()
        
        # Add run to trace
        current_trace.add_run(run)
        
        # Set run in context
        token = _current_run.set(run)
        
        try:
            logger.debug(f"Starting run: {name} (Type: {run_type.value}, ID: {run.id})")
            yield run
            
            # Mark run as completed if not already set
            if run.status == RunStatus.RUNNING:
                run.end()
            
            logger.debug(f"Completed run: {name} (Duration: {run.duration_ms:.2f}ms)")
            
        except Exception as e:
            run.fail(str(e), type(e).__name__)
            logger.error(f"Run failed: {name} - {e}")
            raise
        finally:
            # Save run if auto_save is enabled
            if self.auto_save:
                await self.storage.save_run(run)
            
            _current_run.reset(token)
    
    async def create_trace(
        self,
        name: str,
        request: Optional[str] = None,
        metadata: Optional[TraceMetadata] = None
    ) -> Trace:
        """Create a new trace without context manager."""
        trace = Trace(
            name=name,
            request=request,
            metadata=metadata or TraceMetadata()
        )
        
        if self.auto_save:
            await self.storage.save_trace(trace)
        
        return trace
    
    async def create_run(
        self,
        trace_id: str,
        name: str,
        run_type: RunType,
        inputs: Optional[Dict[str, Any]] = None,
        parent_run_id: Optional[str] = None
    ) -> Run:
        """Create a new run without context manager."""
        run = Run(
            name=name,
            run_type=run_type,
            trace_id=trace_id,
            parent_run_id=parent_run_id,
            inputs=inputs or {}
        )
        
        if self.auto_save:
            await self.storage.save_run(run)
        
        return run
    
    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID."""
        return await self.storage.get_trace(trace_id)
    
    async def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run by ID."""
        return await self.storage.get_run(run_id)
    
    async def list_traces(self, limit: int = 100, offset: int = 0) -> List[Trace]:
        """List traces with pagination."""
        return await self.storage.list_traces(limit, offset)
    
    async def get_runs_by_trace(self, trace_id: str) -> List[Run]:
        """Get all runs for a specific trace."""
        return await self.storage.get_runs_by_trace(trace_id)
    
    def get_current_trace(self) -> Optional[Trace]:
        """Get the current trace from context."""
        return _current_trace.get()
    
    def get_current_run(self) -> Optional[Run]:
        """Get the current run from context."""
        return _current_run.get()
    
    async def update_run_output(self, run_id: str, outputs: Dict[str, Any]) -> None:
        """Update the outputs of a specific run."""
        run = await self.get_run(run_id)
        if run:
            run.outputs.update(outputs)
            if self.auto_save:
                await self.storage.save_run(run)
    
    async def update_run_metadata(self, run_id: str, metadata: Dict[str, Any]) -> None:
        """Update the metadata of a specific run."""
        run = await self.get_run(run_id)
        if run:
            run.metadata.update(metadata)
            if self.auto_save:
                await self.storage.save_run(run)
    
    async def set_run_token_usage(self, run_id: str, token_usage: Dict[str, int]) -> None:
        """Set token usage for a run."""
        run = await self.get_run(run_id)
        if run:
            run.token_usage = token_usage
            if self.auto_save:
                await self.storage.save_run(run)
    
    async def set_run_cost(self, run_id: str, cost: float) -> None:
        """Set cost for a run."""
        run = await self.get_run(run_id)
        if run:
            run.cost = cost
            if self.auto_save:
                await self.storage.save_run(run)


# Global trace manager instance
_global_trace_manager: Optional[TraceManager] = None


def get_trace_manager() -> TraceManager:
    """Get the global trace manager instance."""
    global _global_trace_manager
    if _global_trace_manager is None:
        _global_trace_manager = TraceManager()
    return _global_trace_manager


def set_trace_manager(manager: TraceManager) -> None:
    """Set the global trace manager instance."""
    global _global_trace_manager
    _global_trace_manager = manager


# Convenience functions using global manager
async def trace(
    name: str,
    request: Optional[str] = None,
    metadata: Optional[Union[TraceMetadata, Dict[str, Any]]] = None,
    **kwargs
):
    """Create a trace using the global trace manager."""
    return get_trace_manager().trace(name, request, metadata, **kwargs)


async def run(
    name: str,
    run_type: RunType,
    inputs: Optional[Dict[str, Any]] = None,
    parent_run_id: Optional[str] = None,
    **metadata
):
    """Create a run using the global trace manager."""
    return get_trace_manager().run(name, run_type, inputs, parent_run_id, **metadata)


def get_current_trace() -> Optional[Trace]:
    """Get the current trace from context."""
    return _current_trace.get()


def get_current_run() -> Optional[Run]:
    """Get the current run from context."""
    return _current_run.get()