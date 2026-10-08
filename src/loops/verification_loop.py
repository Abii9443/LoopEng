"""Loop 2: Verification Loop - Response quality verification with retry logic."""
from datetime import datetime
from typing import Optional, Tuple
import structlog

from src.config import settings
from src.models.trace import ExecutionTrace
from src.models.verification import VerificationResult
from src.evaluators.response_grader import ResponseGrader
from src.storage.trace_store import TraceStore

logger = structlog.get_logger()


class VerificationLoop:
    """
    Loop 2: Verification Loop.

    Verifies response quality against multiple criteria:
    - Relevance
    - Tone
    - Completeness
    - Actionability
    - Accuracy

    If verification fails, provides feedback for retry.
    """

    def __init__(self):
        """Initialize verification loop."""
        self.grader = ResponseGrader()
        self.trace_store = TraceStore()
        self.threshold = settings.verification_threshold

        logger.info(
            "Verification Loop initialized",
            threshold=self.threshold
        )

    def verify(self, trace: ExecutionTrace, review) -> VerificationResult:
        """
        Verify response quality.

        Args:
            trace: Execution trace with response
            review: Original review (needed for context)

        Returns:
            VerificationResult with scores and feedback
        """
        logger.info(
            "Starting verification",
            trace_id=trace.id,
            response_id=trace.response.id
        )

        # Grade all criteria
        criteria_scores = self.grader.grade_all_criteria(review, trace.response)

        # Calculate weighted overall score
        overall_score = sum(
            score.score * score.weight
            for score in criteria_scores.values()
        )

        # Determine if passed
        passed = overall_score >= self.threshold

        # Generate feedback
        feedback = self._generate_feedback(criteria_scores, overall_score, passed)

        # Generate improvement suggestions
        suggestions = self._generate_suggestions(criteria_scores, review)

        # Create verification result
        result = VerificationResult(
            trace_id=trace.id,
            timestamp=datetime.now(),
            criteria_scores=criteria_scores,
            overall_score=overall_score,
            passed=passed,
            feedback=feedback,
            improvement_suggestions=suggestions
        )

        # Update trace with verification
        trace.verification = result
        trace.success = passed

        # Update in storage
        self.trace_store.save(trace)

        logger.info(
            "Verification complete",
            trace_id=trace.id,
            overall_score=f"{overall_score:.2f}",
            passed=passed,
            num_suggestions=len(suggestions)
        )

        return result

    def verify_with_retry(
        self,
        trace: ExecutionTrace,
        review,
        agent_loop,
        max_retries: Optional[int] = None
    ) -> Tuple[ExecutionTrace, VerificationResult]:
        """
        Verify response with automatic retry on failure.

        Args:
            trace: Initial execution trace
            review: Original review
            agent_loop: Agent loop instance for retries
            max_retries: Maximum retry attempts (default from settings)

        Returns:
            Tuple of (final_trace, final_verification_result)
        """
        if max_retries is None:
            max_retries = settings.max_retries

        current_trace = trace
        retry_count = 0

        logger.info(
            "Starting verification with retry",
            trace_id=trace.id,
            max_retries=max_retries
        )

        while retry_count <= max_retries:
            # Verify current response
            verification = self.verify(current_trace, review)

            # If passed, we're done
            if verification.passed:
                logger.info(
                    "Verification passed",
                    trace_id=current_trace.id,
                    retry_count=retry_count,
                    overall_score=f"{verification.overall_score:.2f}"
                )
                return current_trace, verification

            # If not passed and no retries left, return as is
            if retry_count >= max_retries:
                logger.warning(
                    "Verification failed after max retries",
                    trace_id=current_trace.id,
                    retry_count=retry_count,
                    overall_score=f"{verification.overall_score:.2f}"
                )
                return current_trace, verification

            # Retry with feedback
            retry_count += 1
            logger.info(
                "Retrying with feedback",
                trace_id=current_trace.id,
                retry_count=retry_count,
                current_score=f"{verification.overall_score:.2f}"
            )

            # Generate retry
            import asyncio
            current_trace = asyncio.run(agent_loop.process_review(
                review=review,
                feedback=verification.feedback,
                original_response=current_trace.response.text,
                version=retry_count + 1
            ))

        # Should not reach here, but return last attempt
        return current_trace, current_trace.verification

    def _generate_feedback(
        self,
        criteria_scores: dict,
        overall_score: float,
        passed: bool
    ) -> str:
        """Generate detailed feedback for the response."""
        if passed:
            # Positive feedback
            strengths = [
                f"{criterion}: {score.rationale}"
                for criterion, score in criteria_scores.items()
                if score.score >= 0.8
            ]

            if strengths:
                feedback = f"Good response (score: {overall_score:.2f}). Strengths: " + "; ".join(strengths[:2])
            else:
                feedback = f"Response passed verification (score: {overall_score:.2f})."

        else:
            # Constructive feedback
            weaknesses = [
                f"{criterion} ({score.score:.2f}): {score.rationale}"
                for criterion, score in criteria_scores.items()
                if score.score < self.threshold
            ]

            feedback = f"Response needs improvement (score: {overall_score:.2f}). Issues: " + "; ".join(weaknesses)

        return feedback

    def _generate_suggestions(self, criteria_scores: dict, review) -> list:
        """Generate actionable improvement suggestions."""
        suggestions = []

        for criterion, score in criteria_scores.items():
            if score.score < self.threshold:
                suggestion = self._get_criterion_suggestion(criterion, score, review)
                if suggestion:
                    suggestions.append(suggestion)

        return suggestions

    def _get_criterion_suggestion(self, criterion: str, score, review) -> Optional[str]:
        """Get specific suggestion for a criterion."""
        if criterion == "relevance":
            if review.issues:
                return f"Address specific issues: {', '.join(i.category for i in review.issues[:3])}"
            return "Ensure response directly addresses review content"

        elif criterion == "tone":
            if review.sentiment and review.sentiment.label == "negative":
                return "Add more empathetic language (e.g., 'We sincerely apologize', 'We understand your frustration')"
            elif review.sentiment and review.sentiment.label == "positive":
                return "Express more gratitude (e.g., 'Thank you so much', 'We truly appreciate')"
            return "Adjust tone to match review sentiment"

        elif criterion == "completeness":
            if review.issues:
                return f"Ensure all {len(review.issues)} identified issues are addressed"
            return "Provide more comprehensive response covering all aspects"

        elif criterion == "actionability":
            return "Add clear next steps: contact information (email/phone) and specific actions customer can take"

        elif criterion == "accuracy":
            return "Avoid specific claims that cannot be verified; stick to factual information"

        return None

    def get_statistics(self) -> dict:
        """Get verification statistics from recent traces."""
        traces = self.trace_store.get_recent(limit=100)
        verified_traces = [t for t in traces if t.verification]

        if not verified_traces:
            return {
                "total_verified": 0,
                "pass_rate": 0.0,
                "avg_score": 0.0,
                "avg_retries": 0.0
            }

        passed_count = sum(1 for t in verified_traces if t.verification.passed)
        pass_rate = passed_count / len(verified_traces)
        avg_score = sum(t.verification.overall_score for t in verified_traces) / len(verified_traces)

        # Calculate average retries (version - 1)
        avg_retries = sum(t.response.version - 1 for t in verified_traces) / len(verified_traces)

        return {
            "total_verified": len(verified_traces),
            "pass_rate": pass_rate,
            "avg_score": avg_score,
            "avg_retries": avg_retries
        }
