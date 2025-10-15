from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SlideTask:
    """Represents a single slide task produced by the plan agent.

    Attributes:
        id: 1-indexed slide identifier
        title: Slide title
        objective: What insight this slide must communicate
        insights: Optional list of expected insights or key points
        query_suggestions: Optional list of SQL ideas to try
        chart_hint: Optional preferred chart type or layout suggestion
        notes: Any extra hints for the solver
    """

    id: int
    title: str
    objective: str
    insights: list[str] = field(default_factory=list)
    query_suggestions: list[str] = field(default_factory=list)
    chart_hint: str | None = None
    notes: str | None = None

    def short_summary(self) -> str:
        summary = f"[Slide {self.id}] {self.title}: {self.objective}"
        if self.insights:
            summary += f" | Insights: {', '.join(self.insights[:2])}"
        if self.chart_hint:
            summary += f" | Chart: {self.chart_hint}"
        return summary

