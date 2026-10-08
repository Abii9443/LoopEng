"""Pattern detection for hill climbing loop."""
from typing import List, Dict
from collections import defaultdict
import structlog

from src.models.trace import ExecutionTrace
from src.models.improvement import Pattern

logger = structlog.get_logger()


class PatternDetector:
    """Detects patterns in execution traces for improvement opportunities."""

    def __init__(self):
        """Initialize pattern detector."""
        pass

    def analyze(self, traces: List[ExecutionTrace]) -> List[Pattern]:
        """
        Analyze traces to detect patterns.

        Args:
            traces: List of execution traces to analyze

        Returns:
            List of detected patterns
        """
        logger.info("Analyzing traces for patterns", count=len(traces))

        patterns = []

        # Pattern 1: Low scores for specific criteria
        criteria_patterns = self._detect_criteria_patterns(traces)
        patterns.extend(criteria_patterns)

        # Pattern 2: High retry rates
        retry_pattern = self._detect_retry_pattern(traces)
        if retry_pattern:
            patterns.append(retry_pattern)

        # Pattern 3: Sentiment-specific issues
        sentiment_patterns = self._detect_sentiment_patterns(traces)
        patterns.extend(sentiment_patterns)

        # Pattern 4: Issue coverage problems
        coverage_pattern = self._detect_coverage_pattern(traces)
        if coverage_pattern:
            patterns.append(coverage_pattern)

        logger.info("Pattern detection complete", patterns_found=len(patterns))

        return patterns

    def _detect_criteria_patterns(self, traces: List[ExecutionTrace]) -> List[Pattern]:
        """Detect patterns related to specific verification criteria."""
        patterns = []

        verified_traces = [t for t in traces if t.verification]
        if not verified_traces:
            return patterns

        # Calculate average scores per criterion
        criteria_scores = defaultdict(list)
        for trace in verified_traces:
            for criterion, score_obj in trace.verification.criteria_scores.items():
                criteria_scores[criterion].append(score_obj.score)

        # Identify low-scoring criteria
        for criterion, scores in criteria_scores.items():
            avg_score = sum(scores) / len(scores)

            if avg_score < 0.65:  # Below acceptable threshold
                # Find affected traces
                affected = [
                    t.id for t in verified_traces
                    if t.verification.criteria_scores[criterion].score < 0.65
                ]

                pattern = Pattern(
                    description=f"Low {criterion} scores (avg: {avg_score:.2f})",
                    category="quality",
                    severity="high" if avg_score < 0.55 else "medium",
                    frequency=len(affected) / len(verified_traces),
                    affected_traces=affected[:10],  # Sample
                    is_actionable=True
                )
                patterns.append(pattern)

                logger.debug(
                    "Criteria pattern detected",
                    criterion=criterion,
                    avg_score=f"{avg_score:.2f}",
                    affected_count=len(affected)
                )

        return patterns

    def _detect_retry_pattern(self, traces: List[ExecutionTrace]) -> Pattern:
        """Detect high retry rate pattern."""
        retry_counts = [t.response.version - 1 for t in traces]
        avg_retries = sum(retry_counts) / len(traces)

        if avg_retries > 0.5:  # More than 0.5 retries per review on average
            high_retry_traces = [t.id for t in traces if t.response.version > 1]

            return Pattern(
                description=f"High retry rate (avg: {avg_retries:.2f} retries per review)",
                category="performance",
                severity="medium",
                frequency=len(high_retry_traces) / len(traces),
                affected_traces=high_retry_traces[:10],
                is_actionable=True
            )

        return None

    def _detect_sentiment_patterns(self, traces: List[ExecutionTrace]) -> List[Pattern]:
        """Detect sentiment-specific issues."""
        patterns = []

        # Group traces by sentiment
        by_sentiment = defaultdict(list)
        for trace in traces:
            # Try to infer sentiment from trace steps
            for step in trace.steps:
                if step.action == "sentiment_analysis":
                    sentiment = step.output.get("sentiment")
                    if sentiment:
                        by_sentiment[sentiment].append(trace)
                        break

        # Analyze each sentiment group
        for sentiment, sentiment_traces in by_sentiment.items():
            if not sentiment_traces:
                continue

            verified = [t for t in sentiment_traces if t.verification]
            if not verified:
                continue

            avg_score = sum(t.verification.overall_score for t in verified) / len(verified)

            if avg_score < 0.70:
                affected = [t.id for t in verified if t.verification.overall_score < 0.70]

                pattern = Pattern(
                    description=f"Low scores for {sentiment} sentiment reviews (avg: {avg_score:.2f})",
                    category="quality",
                    severity="high" if avg_score < 0.60 else "medium",
                    frequency=len(affected) / len(verified),
                    affected_traces=affected[:10],
                    is_actionable=True
                )
                patterns.append(pattern)

                logger.debug(
                    "Sentiment pattern detected",
                    sentiment=sentiment,
                    avg_score=f"{avg_score:.2f}",
                    affected_count=len(affected)
                )

        return patterns

    def _detect_coverage_pattern(self, traces: List[ExecutionTrace]) -> Pattern:
        """Detect issue coverage problems."""
        # Count traces with completeness issues
        verified = [t for t in traces if t.verification]
        if not verified:
            return None

        low_completeness = [
            t for t in verified
            if "completeness" in t.verification.criteria_scores and
            t.verification.criteria_scores["completeness"].score < 0.70
        ]

        if len(low_completeness) / len(verified) > 0.3:  # 30% have completeness issues
            return Pattern(
                description=f"Incomplete responses: {len(low_completeness)}/{len(verified)} traces",
                category="quality",
                severity="medium",
                frequency=len(low_completeness) / len(verified),
                affected_traces=[t.id for t in low_completeness[:10]],
                is_actionable=True
            )

        return None

    def prioritize_patterns(self, patterns: List[Pattern]) -> List[Pattern]:
        """
        Prioritize patterns by severity and frequency.

        Args:
            patterns: List of detected patterns

        Returns:
            Sorted list (most important first)
        """
        def priority_score(pattern: Pattern) -> float:
            severity_weights = {"high": 3, "medium": 2, "low": 1}
            severity_score = severity_weights.get(pattern.severity, 1)
            return severity_score * pattern.frequency

        sorted_patterns = sorted(patterns, key=priority_score, reverse=True)

        logger.debug(
            "Patterns prioritized",
            count=len(sorted_patterns)
        )

        return sorted_patterns
