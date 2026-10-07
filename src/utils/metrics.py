"""Metrics calculation and analysis."""
from typing import List
from collections import Counter

from src.models.review_models import Trace, TraceMetrics, Opportunity


class MetricsAnalyzer:
    """Analyzes traces to calculate aggregate metrics and find improvement opportunities."""

    def aggregate(self, traces: List[Trace]) -> TraceMetrics:
        """
        Calculate aggregate metrics from multiple traces.

        Args:
            traces: List of Trace objects

        Returns:
            TraceMetrics object with aggregated statistics
        """
        if not traces:
            return TraceMetrics(
                num_traces=0,
                avg_quality_score=0.0,
                avg_retry_count=0.0,
                avg_issues_found=0.0,
                top_issue_types=[],
                avg_duration=0.0,
            )

        # Calculate averages
        total_quality = sum(t.verified_review.quality_score for t in traces)
        total_retries = sum(t.verified_review.retry_count for t in traces)
        total_issues = sum(len(t.verified_review.review.issues) for t in traces)
        total_duration = sum(t.duration for t in traces)

        avg_quality_score = total_quality / len(traces)
        avg_retry_count = total_retries / len(traces)
        avg_issues_found = total_issues / len(traces)
        avg_duration = total_duration / len(traces)

        # Collect issue categories
        all_categories = []
        for trace in traces:
            for issue in trace.verified_review.review.issues:
                all_categories.append(issue.category)

        category_counts = Counter(all_categories)
        top_issue_types = category_counts.most_common(10)

        return TraceMetrics(
            num_traces=len(traces),
            avg_quality_score=avg_quality_score,
            avg_retry_count=avg_retry_count,
            avg_issues_found=avg_issues_found,
            top_issue_types=top_issue_types,
            avg_duration=avg_duration,
        )

    def find_opportunities(self, traces: List[Trace], metrics: TraceMetrics) -> List[Opportunity]:
        """
        Identify improvement opportunities from traces and metrics.

        Args:
            traces: List of Trace objects
            metrics: Aggregate metrics

        Returns:
            List of Opportunity objects
        """
        opportunities = []

        # Opportunity 1: Low quality scores
        if metrics.avg_quality_score < 75:
            low_quality_traces = [t.id for t in traces if t.verified_review.quality_score < 70]

            opportunities.append(Opportunity(
                category='review_depth',
                description=f'Reviews lack depth (avg score: {metrics.avg_quality_score:.1f}). Common feedback suggests missing security or complexity analysis.',
                evidence=low_quality_traces[:5],
                priority=5,
                metric_value=metrics.avg_quality_score,
            ))

        # Opportunity 2: High retry rates
        if metrics.avg_retry_count > 1.0:
            high_retry_traces = [t.id for t in traces if t.verified_review.retry_count > 1]

            opportunities.append(Opportunity(
                category='first_pass_accuracy',
                description=f'High retry rate ({metrics.avg_retry_count:.2f} avg). Reviews need multiple attempts to pass quality threshold.',
                evidence=high_retry_traces[:5],
                priority=4,
                metric_value=metrics.avg_retry_count,
            ))

        # Opportunity 3: Few issues found (potential false negatives)
        if metrics.avg_issues_found < 2.0:
            few_issues_traces = [t.id for t in traces if len(t.verified_review.review.issues) < 2]

            opportunities.append(Opportunity(
                category='detection_sensitivity',
                description=f'Low issue detection ({metrics.avg_issues_found:.1f} avg). May be missing issues or code is very clean.',
                evidence=few_issues_traces[:5],
                priority=3,
                metric_value=metrics.avg_issues_found,
            ))

        # Opportunity 4: Tool usage patterns
        tool_usage = Counter()
        for trace in traces:
            for tool in trace.verified_review.review.tools_used:
                tool_usage[tool] += 1

        rarely_used_tools = [tool for tool, count in tool_usage.items() if count < len(traces) * 0.3]
        if rarely_used_tools:
            opportunities.append(Opportunity(
                category='tool_utilization',
                description=f'Some tools rarely used: {", ".join(rarely_used_tools[:3])}. May need prompt adjustment to encourage tool usage.',
                evidence=[t.id for t in traces[:3]],
                priority=2,
                metric_value=len(rarely_used_tools),
            ))

        # Sort by priority
        opportunities.sort(key=lambda o: o.priority, reverse=True)

        return opportunities
