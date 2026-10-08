"""Loop 4: Hill Climbing Loop - Self-improvement through trace analysis."""
import asyncio
from typing import List, Optional
from datetime import datetime
from collections import defaultdict
import structlog

from src.config import settings, prompt_manager
from src.models.improvement import ImprovementHypothesis, ABTestResult
from src.models.review import Review
from src.storage.trace_store import TraceStore
from src.storage.sqlite_store import SQLiteStore
from src.evaluators.pattern_detector import PatternDetector
from src.evaluators.improvement_engine import ImprovementEngine

logger = structlog.get_logger()


class HillClimbingLoop:
    """
    Loop 4: Hill Climbing Loop.

    Analyzes execution traces to detect patterns and generate improvements:
    1. Fetch recent traces (batch)
    2. Detect patterns (low scores, high retries, etc.)
    3. Generate improvement hypotheses
    4. A/B test hypotheses
    5. Apply successful improvements
    6. Track improvement history
    """

    def __init__(self):
        """Initialize hill climbing loop."""
        self.trace_store = TraceStore()
        self.db = SQLiteStore()
        self.pattern_detector = PatternDetector()
        self.improvement_engine = ImprovementEngine()

        self.batch_size = settings.hill_climbing_batch_size
        self.ab_test_sample_size = settings.ab_test_sample_size
        self.min_improvement = settings.ab_test_min_improvement

        logger.info(
            "Hill Climbing Loop initialized",
            batch_size=self.batch_size,
            ab_test_size=self.ab_test_sample_size
        )

    async def analyze_and_improve(self, coordinator=None) -> List[ImprovementHypothesis]:
        """
        Main hill climbing cycle.

        Args:
            coordinator: LoopCoordinator instance for A/B testing

        Returns:
            List of applied improvements
        """
        logger.info("Starting hill climbing analysis")

        # Step 1: Fetch recent traces
        traces = self.trace_store.get_for_analysis(
            batch_size=self.batch_size,
            include_failures=True
        )

        if len(traces) < 20:
            logger.warning(
                "Insufficient traces for analysis",
                count=len(traces),
                required=20
            )
            return []

        logger.info(f"Analyzing {len(traces)} traces")

        # Step 2: Detect patterns
        patterns = self.pattern_detector.analyze(traces)

        if not patterns:
            logger.info("No patterns detected - system performing well")
            return []

        patterns = self.pattern_detector.prioritize_patterns(patterns)
        logger.info(f"Detected {len(patterns)} patterns")

        # Step 3: Generate hypotheses
        hypotheses = self.improvement_engine.generate_hypotheses(patterns, traces)

        if not hypotheses:
            logger.info("No actionable hypotheses generated")
            return []

        hypotheses = self.improvement_engine.prioritize_hypotheses(hypotheses)
        logger.info(f"Generated {len(hypotheses)} hypotheses")

        # Step 4: Test and apply top hypotheses
        applied_improvements = []

        # Test top 2 hypotheses
        for hypothesis in hypotheses[:2]:
            logger.info(
                "Testing hypothesis",
                hypothesis_id=hypothesis.id,
                pattern=hypothesis.pattern,
                expected_improvement=f"{hypothesis.expected_improvement:.1%}"
            )

            # Save hypothesis
            self.db.save_improvement(hypothesis)

            # A/B test if coordinator available
            if coordinator:
                should_apply = await self._ab_test_hypothesis(
                    hypothesis,
                    coordinator
                )

                if should_apply:
                    self._apply_improvement(hypothesis)
                    applied_improvements.append(hypothesis)
                    logger.info(
                        "Improvement applied",
                        hypothesis_id=hypothesis.id,
                        change_type=hypothesis.change_type
                    )
                else:
                    logger.info(
                        "Improvement rejected (insufficient impact)",
                        hypothesis_id=hypothesis.id
                    )
            else:
                # No coordinator - simulate or apply directly
                logger.warning("No coordinator provided - skipping A/B test")
                # In production, you'd apply cautiously without testing
                # For now, we'll mark as pending
                self.db.update_improvement_status(
                    hypothesis.id,
                    "pending",
                    None
                )

        logger.info(
            "Hill climbing cycle complete",
            patterns_found=len(patterns),
            hypotheses_generated=len(hypotheses),
            improvements_applied=len(applied_improvements)
        )

        return applied_improvements

    async def _ab_test_hypothesis(
        self,
        hypothesis: ImprovementHypothesis,
        coordinator
    ) -> bool:
        """
        A/B test an improvement hypothesis.

        Args:
            hypothesis: Hypothesis to test
            coordinator: LoopCoordinator for processing reviews

        Returns:
            True if should apply, False otherwise
        """
        logger.info("Starting A/B test", hypothesis_id=hypothesis.id)

        # Get test reviews
        test_reviews = self._get_test_reviews(self.ab_test_sample_size * 2)

        if len(test_reviews) < self.ab_test_sample_size:
            logger.warning(
                "Insufficient test reviews",
                available=len(test_reviews),
                needed=self.ab_test_sample_size
            )
            return False

        # Split into baseline and treatment groups
        baseline_reviews = test_reviews[:self.ab_test_sample_size]
        treatment_reviews = test_reviews[self.ab_test_sample_size:self.ab_test_sample_size * 2]

        # Process baseline (current configuration)
        logger.info("Processing baseline group")
        baseline_traces = await coordinator.process_batch(
            baseline_reviews,
            parallel=False
        )

        baseline_scores = [
            t.verification.overall_score
            for t in baseline_traces
            if t.verification
        ]
        baseline_avg = sum(baseline_scores) / len(baseline_scores) if baseline_scores else 0

        # Apply hypothesis temporarily
        self._apply_improvement_temporarily(hypothesis)

        # Process treatment (with improvement)
        logger.info("Processing treatment group")
        treatment_traces = await coordinator.process_batch(
            treatment_reviews,
            parallel=False
        )

        treatment_scores = [
            t.verification.overall_score
            for t in treatment_traces
            if t.verification
        ]
        treatment_avg = sum(treatment_scores) / len(treatment_scores) if treatment_scores else 0

        # Revert temporary change
        self._revert_improvement(hypothesis)

        # Calculate improvement
        improvement = treatment_avg - baseline_avg
        relative_improvement = (improvement / baseline_avg) if baseline_avg > 0 else 0

        # Determine significance (simple threshold for POC)
        is_significant = improvement > 0.05  # At least 5% absolute improvement
        should_apply = is_significant and relative_improvement >= self.min_improvement

        logger.info(
            "A/B test complete",
            hypothesis_id=hypothesis.id,
            baseline_score=f"{baseline_avg:.3f}",
            treatment_score=f"{treatment_avg:.3f}",
            improvement=f"{improvement:.3f}",
            relative_improvement=f"{relative_improvement:.1%}",
            should_apply=should_apply
        )

        # Save test results
        result = ABTestResult(
            hypothesis_id=hypothesis.id,
            timestamp=datetime.now(),
            baseline_traces=[t.id for t in baseline_traces],
            treatment_traces=[t.id for t in treatment_traces],
            baseline_score=baseline_avg,
            treatment_score=treatment_avg,
            improvement=improvement,
            relative_improvement=relative_improvement,
            is_significant=is_significant,
            should_apply=should_apply
        )

        self.db.save_ab_test_result(result)

        # Update hypothesis with actual results
        self.db.update_improvement_status(
            hypothesis.id,
            "applied" if should_apply else "rejected",
            improvement
        )

        return should_apply

    def _get_test_reviews(self, count: int) -> List[Review]:
        """Get sample reviews for A/B testing."""
        # For POC, create synthetic test reviews
        # In production, you'd use a held-out test set

        test_reviews = []

        # Create mix of positive, negative, and neutral
        sentiments = [
            ("negative", 2.0, "The product arrived damaged and doesn't work as advertised."),
            ("negative", 1.5, "Terrible quality. Broke after one use. Very disappointed."),
            ("positive", 5.0, "Excellent product! Exceeded expectations. Highly recommend."),
            ("positive", 4.5, "Great quality and fast shipping. Very satisfied!"),
            ("neutral", 3.0, "Product is okay. Does the job but nothing special."),
        ]

        idx = 0
        while len(test_reviews) < count:
            sentiment, rating, text = sentiments[idx % len(sentiments)]
            idx += 1

            review = Review(
                id=f"test_review_{idx}",
                product_id=f"test_product_{idx % 10}",
                text=text,
                rating=rating
            )
            test_reviews.append(review)

        return test_reviews

    def _apply_improvement(self, hypothesis: ImprovementHypothesis):
        """Apply an improvement hypothesis."""
        if hypothesis.change_type == "prompt":
            # Update prompt in prompt manager
            # Determine which prompt to update based on the pattern
            if "negative" in hypothesis.pattern.lower():
                prompt_manager.update_prompt("negative_review", hypothesis.proposed_value)
            elif "positive" in hypothesis.pattern.lower():
                prompt_manager.update_prompt("positive_review", hypothesis.proposed_value)
            elif "retry" in hypothesis.pattern.lower():
                prompt_manager.update_prompt("system", hypothesis.proposed_value)
            else:
                # Generic - update negative review as default
                prompt_manager.update_prompt("negative_review", hypothesis.proposed_value)

            logger.info(
                "Prompt updated",
                hypothesis_id=hypothesis.id,
                new_version=prompt_manager.get_version()
            )

        elif hypothesis.change_type == "threshold":
            # Would update verification threshold
            # For POC, we log it
            logger.info("Threshold adjustment proposed", hypothesis_id=hypothesis.id)

        elif hypothesis.change_type == "strategy":
            # Would update response strategy
            logger.info("Strategy change proposed", hypothesis_id=hypothesis.id)

    def _apply_improvement_temporarily(self, hypothesis: ImprovementHypothesis):
        """Temporarily apply improvement for A/B testing."""
        # Store current state
        self._temp_prompt_backup = prompt_manager.base_prompts.copy()

        # Apply change
        self._apply_improvement(hypothesis)

    def _revert_improvement(self, hypothesis: ImprovementHypothesis):
        """Revert temporary improvement."""
        if hasattr(self, '_temp_prompt_backup'):
            prompt_manager.base_prompts = self._temp_prompt_backup
            del self._temp_prompt_backup

    def get_improvement_history(self) -> List[dict]:
        """Get history of improvements."""
        # Query improvements from database
        conn = self.db._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, timestamp, pattern, change_type,
                   expected_improvement, actual_improvement, status
            FROM improvements
            ORDER BY timestamp DESC
            LIMIT 20
        """)

        rows = cursor.fetchall()

        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "timestamp": row[1],
                "pattern": row[2],
                "change_type": row[3],
                "expected_improvement": row[4],
                "actual_improvement": row[5],
                "status": row[6]
            })

        return history

    def get_statistics(self) -> dict:
        """Get hill climbing statistics."""
        history = self.get_improvement_history()

        applied = [h for h in history if h["status"] == "applied"]
        rejected = [h for h in history if h["status"] == "rejected"]

        if applied:
            avg_improvement = sum(
                h["actual_improvement"] or 0
                for h in applied
            ) / len(applied)
        else:
            avg_improvement = 0

        return {
            "total_hypotheses": len(history),
            "applied": len(applied),
            "rejected": len(rejected),
            "pending": len([h for h in history if h["status"] == "pending"]),
            "avg_improvement": avg_improvement,
            "current_prompt_version": prompt_manager.get_version()
        }
