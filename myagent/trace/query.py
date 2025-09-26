"""
Query interface for trace data analysis and retrieval.

This module provides rich query capabilities for analyzing
traced execution data, similar to LangSmith's query interface.
"""

from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from .models import Run
from .models import RunStatus
from .models import RunType
from .models import Trace


class SortOrder(str, Enum):
    """Sort order options."""

    ASC = "asc"
    DESC = "desc"


class TraceFilter(BaseModel):
    """Filter criteria for traces."""

    # Time range
    start_time: datetime | None = Field(
        None, description="Filter traces after this time"
    )
    end_time: datetime | None = Field(
        None, description="Filter traces before this time"
    )

    # Status
    status: RunStatus | None = Field(None, description="Filter by trace status")

    # Metadata filters
    user_id: str | None = Field(None, description="Filter by user ID")
    session_id: str | None = Field(None, description="Filter by session ID")
    tags: list[str] | None = Field(None, description="Filter by tags (any match)")
    environment: str | None = Field(None, description="Filter by environment")

    # Content filters
    request_contains: str | None = Field(None, description="Filter by request content")
    response_contains: str | None = Field(
        None, description="Filter by response content"
    )

    # Metrics filters
    min_duration_ms: float | None = Field(
        None, description="Minimum duration in milliseconds"
    )
    max_duration_ms: float | None = Field(
        None, description="Maximum duration in milliseconds"
    )
    min_cost: float | None = Field(None, description="Minimum cost")
    max_cost: float | None = Field(None, description="Maximum cost")
    min_tokens: int | None = Field(None, description="Minimum token count")
    max_tokens: int | None = Field(None, description="Maximum token count")

    # Error filters
    has_errors: bool | None = Field(
        None, description="Filter traces with/without errors"
    )


class RunFilter(BaseModel):
    """Filter criteria for runs."""

    # Basic filters
    trace_id: str | None = Field(None, description="Filter by trace ID")
    run_type: RunType | None = Field(None, description="Filter by run type")
    status: RunStatus | None = Field(None, description="Filter by run status")
    name_contains: str | None = Field(None, description="Filter by run name")

    # Time range
    start_time: datetime | None = Field(None, description="Filter runs after this time")
    end_time: datetime | None = Field(None, description="Filter runs before this time")

    # Metrics filters
    min_duration_ms: float | None = Field(
        None, description="Minimum duration in milliseconds"
    )
    max_duration_ms: float | None = Field(
        None, description="Maximum duration in milliseconds"
    )

    # Error filters
    has_errors: bool | None = Field(None, description="Filter runs with/without errors")

    # Hierarchy filters
    is_root: bool | None = Field(None, description="Filter root runs (no parent)")
    parent_run_id: str | None = Field(None, description="Filter by parent run ID")


class SortCriteria(BaseModel):
    """Sorting criteria for query results."""

    field: str = Field(..., description="Field to sort by")
    order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")


class QueryOptions(BaseModel):
    """Options for query execution."""

    limit: int = Field(default=100, description="Maximum number of results")
    offset: int = Field(default=0, description="Number of results to skip")
    sort_by: list[SortCriteria] = Field(
        default_factory=lambda: [SortCriteria(field="start_time")]
    )
    include_runs: bool = Field(
        default=True, description="Include runs in trace results"
    )


class QueryResult(BaseModel):
    """Result of a query operation."""

    total_count: int = Field(..., description="Total number of matching records")
    results: list[Trace | Run] = Field(..., description="Query results")
    query_time_ms: float = Field(
        ..., description="Query execution time in milliseconds"
    )
    has_more: bool = Field(..., description="Whether more results are available")


class TraceQueryEngine:
    """Engine for querying trace data with advanced filtering and analysis."""

    def __init__(self, storage):
        """Initialize with a storage backend."""
        self.storage = storage

    async def query_traces(
        self, filters: TraceFilter | None = None, options: QueryOptions | None = None
    ) -> QueryResult:
        """Query traces with filtering and sorting."""
        start_time = datetime.now(timezone.utc)

        filters = filters or TraceFilter()
        options = options or QueryOptions()

        # Get all traces (in a real implementation, this would be optimized)
        all_traces = await self.storage.list_traces(limit=10000)

        # Apply filters
        filtered_traces = self._filter_traces(all_traces, filters)

        # Apply sorting
        sorted_traces = self._sort_traces(filtered_traces, options.sort_by)

        # Apply pagination
        total_count = len(sorted_traces)
        start_idx = options.offset
        end_idx = start_idx + options.limit
        paginated_traces = sorted_traces[start_idx:end_idx]

        # Include runs if requested
        if options.include_runs:
            for trace in paginated_traces:
                trace.runs = await self.storage.get_runs_by_trace(trace.id)

        # Calculate query time
        end_time = datetime.now(timezone.utc)
        query_time_ms = (end_time - start_time).total_seconds() * 1000

        return QueryResult(
            total_count=total_count,
            results=paginated_traces,
            query_time_ms=query_time_ms,
            has_more=end_idx < total_count,
        )

    async def query_runs(
        self, filters: RunFilter | None = None, options: QueryOptions | None = None
    ) -> QueryResult:
        """Query runs with filtering and sorting."""
        start_time = datetime.now(timezone.utc)

        filters = filters or RunFilter()
        options = options or QueryOptions()

        # Get runs based on filters
        if filters.trace_id:
            all_runs = await self.storage.get_runs_by_trace(filters.trace_id)
        else:
            # Get all runs (in a real implementation, this would be optimized)
            all_traces = await self.storage.list_traces(limit=10000)
            all_runs = []
            for trace in all_traces:
                runs = await self.storage.get_runs_by_trace(trace.id)
                all_runs.extend(runs)

        # Apply filters
        filtered_runs = self._filter_runs(all_runs, filters)

        # Apply sorting
        sorted_runs = self._sort_runs(filtered_runs, options.sort_by)

        # Apply pagination
        total_count = len(sorted_runs)
        start_idx = options.offset
        end_idx = start_idx + options.limit
        paginated_runs = sorted_runs[start_idx:end_idx]

        # Calculate query time
        end_time = datetime.now(timezone.utc)
        query_time_ms = (end_time - start_time).total_seconds() * 1000

        return QueryResult(
            total_count=total_count,
            results=paginated_runs,
            query_time_ms=query_time_ms,
            has_more=end_idx < total_count,
        )

    def _filter_traces(self, traces: list[Trace], filters: TraceFilter) -> list[Trace]:
        """Apply filters to trace list."""
        filtered = traces

        # Time filters
        if filters.start_time:
            filtered = [t for t in filtered if t.start_time >= filters.start_time]
        if filters.end_time:
            filtered = [t for t in filtered if t.start_time <= filters.end_time]

        # Status filter
        if filters.status:
            filtered = [t for t in filtered if t.status == filters.status]

        # Metadata filters
        if filters.user_id:
            filtered = [t for t in filtered if t.metadata.user_id == filters.user_id]
        if filters.session_id:
            filtered = [
                t for t in filtered if t.metadata.session_id == filters.session_id
            ]
        if filters.environment:
            filtered = [
                t for t in filtered if t.metadata.environment == filters.environment
            ]
        if filters.tags:
            filtered = [
                t
                for t in filtered
                if any(tag in t.metadata.tags for tag in filters.tags)
            ]

        # Content filters
        if filters.request_contains:
            filtered = [
                t
                for t in filtered
                if t.request and filters.request_contains.lower() in t.request.lower()
            ]
        if filters.response_contains:
            filtered = [
                t
                for t in filtered
                if t.response
                and filters.response_contains.lower() in t.response.lower()
            ]

        # Metrics filters
        if filters.min_duration_ms is not None:
            filtered = [
                t
                for t in filtered
                if t.duration_ms and t.duration_ms >= filters.min_duration_ms
            ]
        if filters.max_duration_ms is not None:
            filtered = [
                t
                for t in filtered
                if t.duration_ms and t.duration_ms <= filters.max_duration_ms
            ]
        if filters.min_cost is not None:
            filtered = [
                t for t in filtered if t.total_cost and t.total_cost >= filters.min_cost
            ]
        if filters.max_cost is not None:
            filtered = [
                t for t in filtered if t.total_cost and t.total_cost <= filters.max_cost
            ]
        if filters.min_tokens is not None:
            filtered = [
                t
                for t in filtered
                if t.total_tokens and t.total_tokens >= filters.min_tokens
            ]
        if filters.max_tokens is not None:
            filtered = [
                t
                for t in filtered
                if t.total_tokens and t.total_tokens <= filters.max_tokens
            ]

        # Error filters
        if filters.has_errors is not None:
            if filters.has_errors:
                filtered = [
                    t
                    for t in filtered
                    if any(run.status == RunStatus.ERROR for run in t.runs)
                ]
            else:
                filtered = [
                    t
                    for t in filtered
                    if not any(run.status == RunStatus.ERROR for run in t.runs)
                ]

        return filtered

    def _filter_runs(self, runs: list[Run], filters: RunFilter) -> list[Run]:
        """Apply filters to run list."""
        filtered = runs

        # Basic filters
        if filters.run_type:
            filtered = [r for r in filtered if r.run_type == filters.run_type]
        if filters.status:
            filtered = [r for r in filtered if r.status == filters.status]
        if filters.name_contains:
            filtered = [
                r for r in filtered if filters.name_contains.lower() in r.name.lower()
            ]

        # Time filters
        if filters.start_time:
            filtered = [r for r in filtered if r.start_time >= filters.start_time]
        if filters.end_time:
            filtered = [r for r in filtered if r.start_time <= filters.end_time]

        # Metrics filters
        if filters.min_duration_ms is not None:
            filtered = [
                r
                for r in filtered
                if r.duration_ms and r.duration_ms >= filters.min_duration_ms
            ]
        if filters.max_duration_ms is not None:
            filtered = [
                r
                for r in filtered
                if r.duration_ms and r.duration_ms <= filters.max_duration_ms
            ]

        # Error filters
        if filters.has_errors is not None:
            if filters.has_errors:
                filtered = [r for r in filtered if r.status == RunStatus.ERROR]
            else:
                filtered = [r for r in filtered if r.status != RunStatus.ERROR]

        # Hierarchy filters
        if filters.is_root is not None:
            if filters.is_root:
                filtered = [r for r in filtered if r.parent_run_id is None]
            else:
                filtered = [r for r in filtered if r.parent_run_id is not None]
        if filters.parent_run_id:
            filtered = [r for r in filtered if r.parent_run_id == filters.parent_run_id]

        return filtered

    def _sort_traces(
        self, traces: list[Trace], sort_criteria: list[SortCriteria]
    ) -> list[Trace]:
        """Sort traces by multiple criteria."""
        for criteria in reversed(
            sort_criteria
        ):  # Apply in reverse order for stable sort
            reverse = criteria.order == SortOrder.DESC

            if criteria.field == "start_time":
                traces.sort(key=lambda t: t.start_time, reverse=reverse)
            elif criteria.field == "duration_ms":
                traces.sort(key=lambda t: t.duration_ms or 0, reverse=reverse)
            elif criteria.field == "total_cost":
                traces.sort(key=lambda t: t.total_cost or 0, reverse=reverse)
            elif criteria.field == "total_tokens":
                traces.sort(key=lambda t: t.total_tokens or 0, reverse=reverse)
            elif criteria.field == "name":
                traces.sort(key=lambda t: t.name, reverse=reverse)

        return traces

    def _sort_runs(
        self, runs: list[Run], sort_criteria: list[SortCriteria]
    ) -> list[Run]:
        """Sort runs by multiple criteria."""
        for criteria in reversed(
            sort_criteria
        ):  # Apply in reverse order for stable sort
            reverse = criteria.order == SortOrder.DESC

            if criteria.field == "start_time":
                runs.sort(key=lambda r: r.start_time, reverse=reverse)
            elif criteria.field == "duration_ms":
                runs.sort(key=lambda r: r.duration_ms or 0, reverse=reverse)
            elif criteria.field == "name":
                runs.sort(key=lambda r: r.name, reverse=reverse)
            elif criteria.field == "run_type":
                runs.sort(key=lambda r: r.run_type.value, reverse=reverse)

        return runs

    async def get_trace_statistics(
        self, filters: TraceFilter | None = None
    ) -> dict[str, Any]:
        """Get statistical summary of traces."""
        traces_result = await self.query_traces(filters, QueryOptions(limit=10000))
        traces = traces_result.results

        if not traces:
            return {
                "total_traces": 0,
                "avg_duration_ms": 0,
                "total_cost": 0,
                "total_tokens": 0,
                "error_rate": 0,
                "status_distribution": {},
            }

        # Calculate statistics
        total_traces = len(traces)
        durations = [t.duration_ms for t in traces if t.duration_ms]
        costs = [t.total_cost for t in traces if t.total_cost]
        tokens = [t.total_tokens for t in traces if t.total_tokens]

        avg_duration_ms = sum(durations) / len(durations) if durations else 0
        total_cost = sum(costs)
        total_tokens = sum(tokens)

        error_count = len([t for t in traces if t.status == RunStatus.ERROR])
        error_rate = error_count / total_traces if total_traces > 0 else 0

        # Status distribution
        status_counts = {}
        for trace in traces:
            status = trace.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_traces": total_traces,
            "avg_duration_ms": avg_duration_ms,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "error_rate": error_rate,
            "status_distribution": status_counts,
        }

    async def get_run_statistics(
        self, filters: RunFilter | None = None
    ) -> dict[str, Any]:
        """Get statistical summary of runs."""
        runs_result = await self.query_runs(filters, QueryOptions(limit=10000))
        runs = runs_result.results

        if not runs:
            return {
                "total_runs": 0,
                "avg_duration_ms": 0,
                "error_rate": 0,
                "type_distribution": {},
                "status_distribution": {},
            }

        # Calculate statistics
        total_runs = len(runs)
        durations = [r.duration_ms for r in runs if r.duration_ms]
        avg_duration_ms = sum(durations) / len(durations) if durations else 0

        error_count = len([r for r in runs if r.status == RunStatus.ERROR])
        error_rate = error_count / total_runs if total_runs > 0 else 0

        # Type distribution
        type_counts = {}
        for run in runs:
            run_type = run.run_type.value
            type_counts[run_type] = type_counts.get(run_type, 0) + 1

        # Status distribution
        status_counts = {}
        for run in runs:
            status = run.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_runs": total_runs,
            "avg_duration_ms": avg_duration_ms,
            "error_rate": error_rate,
            "type_distribution": type_counts,
            "status_distribution": status_counts,
        }
