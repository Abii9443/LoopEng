"""Trace-specific storage operations."""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import structlog

from src.storage.sqlite_store import SQLiteStore
from src.models.trace import ExecutionTrace
from src.models.metrics import SystemMetrics

logger = structlog.get_logger()


class TraceStore:
    """High-level interface for trace storage and retrieval."""

    def __init__(self):
        """Initialize trace store."""
        self.db = SQLiteStore()

    def save(self, trace: ExecutionTrace):
        """
        Save execution trace.

        Args:
            trace: Execution trace to save
        """
        self.db.save_trace(trace)
        logger.info(
            "Trace saved",
            trace_id=trace.id,
            success=trace.success,
            duration_ms=trace.duration_ms
        )

    def get(self, trace_id: str) -> Optional[ExecutionTrace]:
        """
        Get trace by ID.

        Args:
            trace_id: Trace ID

        Returns:
            ExecutionTrace if found, None otherwise
        """
        return self.db.get_trace(trace_id)

    def get_recent(self, limit: int = 100, success_only: bool = False) -> List[ExecutionTrace]:
        """
        Get recent traces.

        Args:
            limit: Maximum number of traces to return
            success_only: If True, only return successful traces

        Returns:
            List of traces ordered by timestamp (newest first)
        """
        return self.db.get_recent_traces(limit=limit, success_only=success_only)

    def get_for_analysis(
        self,
        batch_size: int = 100,
        include_failures: bool = True
    ) -> List[ExecutionTrace]:
        """
        Get traces for hill climbing analysis.

        Args:
            batch_size: Number of traces to retrieve
            include_failures: Whether to include failed traces

        Returns:
            List of traces suitable for analysis
        """
        traces = self.db.get_recent_traces(
            limit=batch_size,
            success_only=not include_failures
        )

        logger.info(
            "Retrieved traces for analysis",
            count=len(traces),
            include_failures=include_failures
        )

        return traces

    def calculate_metrics(
        self,
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None
    ) -> SystemMetrics:
        """
        Calculate aggregate metrics for a time window.

        Args:
            window_start: Start of time window (default: 24 hours ago)
            window_end: End of time window (default: now)

        Returns:
            SystemMetrics object
        """
        if not window_end:
            window_end = datetime.now()
        if not window_start:
            window_start = window_end - timedelta(hours=24)

        # Get all traces in window
        all_traces = self.db.get_recent_traces(limit=10000)  # Get many traces
        traces_in_window = [
            t for t in all_traces
            if window_start <= t.timestamp <= window_end
        ]

        if not traces_in_window:
            logger.warning("No traces found in window")
            return SystemMetrics(
                timestamp=datetime.now(),
                window_start=window_start,
                window_end=window_end,
                total_reviews_processed=0,
                avg_response_time_ms=0.0,
                verification_pass_rate=0.0,
                avg_verification_score=0.0,
                criteria_breakdown={},
                improvement_cycles=0,
                score_trend=[]
            )

        # Calculate metrics
        total_reviews = len(traces_in_window)
        avg_response_time = sum(t.duration_ms for t in traces_in_window) / total_reviews

        # Verification metrics (only for traces with verification)
        verified_traces = [t for t in traces_in_window if t.verification]

        if verified_traces:
            pass_rate = sum(1 for t in verified_traces if t.verification.passed) / len(verified_traces)
            avg_score = sum(t.verification.overall_score for t in verified_traces) / len(verified_traces)

            # Calculate criteria breakdown
            criteria_breakdown = {}
            criteria_keys = list(verified_traces[0].verification.criteria_scores.keys())
            for criterion in criteria_keys:
                scores = [
                    t.verification.criteria_scores[criterion].score
                    for t in verified_traces
                ]
                criteria_breakdown[criterion] = sum(scores) / len(scores)
        else:
            pass_rate = 0.0
            avg_score = 0.0
            criteria_breakdown = {}

        # Get historical trend (last 5 batches)
        score_trend = self._calculate_score_trend(all_traces)

        metrics = SystemMetrics(
            timestamp=datetime.now(),
            window_start=window_start,
            window_end=window_end,
            total_reviews_processed=total_reviews,
            avg_response_time_ms=avg_response_time,
            verification_pass_rate=pass_rate,
            avg_verification_score=avg_score,
            criteria_breakdown=criteria_breakdown,
            improvement_cycles=0,  # TODO: Track from improvements table
            score_trend=score_trend
        )

        logger.info(
            "Metrics calculated",
            total_reviews=total_reviews,
            pass_rate=f"{pass_rate:.2%}",
            avg_score=f"{avg_score:.2f}"
        )

        return metrics

    def _calculate_score_trend(self, traces: List[ExecutionTrace], batch_size: int = 50) -> List[float]:
        """Calculate score trend from recent traces."""
        verified_traces = [t for t in traces if t.verification]

        if not verified_traces:
            return []

        # Split into batches and calculate average score for each
        trend = []
        for i in range(0, min(len(verified_traces), 250), batch_size):
            batch = verified_traces[i:i + batch_size]
            if batch:
                avg = sum(t.verification.overall_score for t in batch) / len(batch)
                trend.append(round(avg, 3))

        return trend[-5:]  # Return last 5 batches

    def get_failure_patterns(self, limit: int = 100) -> Dict:
        """
        Analyze failure patterns in recent traces.

        Args:
            limit: Number of traces to analyze

        Returns:
            Dictionary with failure analysis
        """
        traces = self.db.get_recent_traces(limit=limit)
        failed_traces = [t for t in traces if not t.success or (t.verification and not t.verification.passed)]

        if not failed_traces:
            return {
                "total_failures": 0,
                "failure_rate": 0.0,
                "common_issues": []
            }

        failure_rate = len(failed_traces) / len(traces)

        # Analyze common issues in failed verifications
        common_issues = {}
        for trace in failed_traces:
            if trace.verification:
                for criterion, score_obj in trace.verification.criteria_scores.items():
                    if score_obj.score < 0.7:  # Below threshold
                        if criterion not in common_issues:
                            common_issues[criterion] = {"count": 0, "avg_score": 0.0}
                        common_issues[criterion]["count"] += 1

        # Calculate average scores for common issues
        for criterion in common_issues:
            scores = [
                t.verification.criteria_scores[criterion].score
                for t in failed_traces
                if t.verification and criterion in t.verification.criteria_scores
            ]
            if scores:
                common_issues[criterion]["avg_score"] = sum(scores) / len(scores)

        # Sort by frequency
        sorted_issues = sorted(
            [{"criterion": k, **v} for k, v in common_issues.items()],
            key=lambda x: x["count"],
            reverse=True
        )

        return {
            "total_failures": len(failed_traces),
            "failure_rate": failure_rate,
            "common_issues": sorted_issues[:5]  # Top 5
        }

    def get_stats(self) -> Dict:
        """Get overall storage statistics."""
        return {
            "total_traces": self.db.get_count("traces"),
            "total_metrics": self.db.get_count("metrics"),
            "total_improvements": self.db.get_count("improvements"),
            "total_ab_tests": self.db.get_count("ab_test_results")
        }
