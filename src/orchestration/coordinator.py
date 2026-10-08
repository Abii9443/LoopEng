"""Main coordinator that connects all 4 loops."""
import asyncio
from typing import List, Optional
import structlog

from src.config import settings
from src.models.review import Review
from src.models.trace import ExecutionTrace
from src.loops.agent_loop import AgentLoop
from src.loops.verification_loop import VerificationLoop
from src.storage.trace_store import TraceStore

logger = structlog.get_logger()


class LoopCoordinator:
    """
    Coordinates all 4 loops:
    - Loop 1: Agent Loop (review processing)
    - Loop 2: Verification Loop (quality checking)
    - Loop 3: Event Loop (orchestration)
    - Loop 4: Hill Climbing Loop (improvement)
    """

    def __init__(self):
        """Initialize coordinator with all loops."""
        self.agent_loop = AgentLoop()
        self.verification_loop = VerificationLoop()
        self.trace_store = TraceStore()

        self.reviews_processed = 0
        self.hill_climbing_frequency = settings.hill_climbing_frequency

        logger.info(
            "Loop Coordinator initialized",
            hill_climbing_frequency=self.hill_climbing_frequency
        )

    async def process_review(
        self,
        review: Review,
        with_verification: bool = True,
        with_retry: bool = True
    ) -> ExecutionTrace:
        """
        Process a single review through Loop 1 and Loop 2.

        Args:
            review: Review to process
            with_verification: Whether to run verification
            with_retry: Whether to retry on verification failure

        Returns:
            Final execution trace
        """
        logger.info(
            "Processing review",
            review_id=review.id,
            rating=review.rating
        )

        # Loop 1: Agent Loop - Process review
        trace = await self.agent_loop.process_review(review)

        # Loop 2: Verification Loop - Check quality
        if with_verification:
            if with_retry:
                trace, verification = self.verification_loop.verify_with_retry(
                    trace=trace,
                    review=review,
                    agent_loop=self.agent_loop
                )
            else:
                verification = self.verification_loop.verify(trace, review)

        # Increment counter
        self.reviews_processed += 1

        # Check if we should trigger hill climbing
        should_trigger_improvement = (
            self.reviews_processed % self.hill_climbing_frequency == 0
        )

        if should_trigger_improvement:
            logger.info(
                "Hill climbing trigger point reached",
                reviews_processed=self.reviews_processed
            )
            # Note: Hill climbing will be triggered by event loop

        logger.info(
            "Review processing complete",
            review_id=review.id,
            trace_id=trace.id,
            success=trace.success,
            verification_score=f"{trace.verification.overall_score:.2f}" if trace.verification else "N/A"
        )

        return trace

    async def process_batch(
        self,
        reviews: List[Review],
        parallel: bool = False
    ) -> List[ExecutionTrace]:
        """
        Process a batch of reviews.

        Args:
            reviews: List of reviews to process
            parallel: Whether to process in parallel

        Returns:
            List of execution traces
        """
        logger.info(
            "Processing batch",
            count=len(reviews),
            parallel=parallel
        )

        if parallel:
            # Process reviews concurrently
            tasks = [
                self.process_review(review)
                for review in reviews
            ]
            traces = await asyncio.gather(*tasks)
        else:
            # Process sequentially
            traces = []
            for review in reviews:
                trace = await self.process_review(review)
                traces.append(trace)

        # Calculate batch metrics
        successful = sum(1 for t in traces if t.success)
        if traces and traces[0].verification:
            verified = sum(1 for t in traces if t.verification and t.verification.passed)
            avg_score = sum(
                t.verification.overall_score
                for t in traces if t.verification
            ) / len(traces)
        else:
            verified = 0
            avg_score = 0.0

        logger.info(
            "Batch processing complete",
            total=len(traces),
            successful=successful,
            verified=verified,
            avg_score=f"{avg_score:.2f}"
        )

        return traces

    def get_status(self) -> dict:
        """Get coordinator status."""
        return {
            "reviews_processed": self.reviews_processed,
            "next_hill_climbing_at": (
                self.hill_climbing_frequency -
                (self.reviews_processed % self.hill_climbing_frequency)
            ),
            "agent_stats": self.agent_loop.get_stats(),
            "verification_stats": self.verification_loop.get_statistics(),
            "storage_stats": self.trace_store.get_stats()
        }

    def get_metrics(self) -> dict:
        """Get comprehensive metrics."""
        metrics = self.trace_store.calculate_metrics()
        failure_patterns = self.trace_store.get_failure_patterns()

        return {
            "system_metrics": metrics.model_dump(),
            "failure_patterns": failure_patterns,
            "coordinator_status": self.get_status()
        }
