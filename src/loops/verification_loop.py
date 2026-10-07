"""Loop 2: Verification Loop - Quality assurance with retry logic."""
import time
from src.config import settings
from src.models.review_models import ReviewResult, VerifiedReview
from src.loops.agent_loop import AgentLoop
from src.agents.quality_grader import QualityGrader


class VerificationLoop:
    """Loop 2: Verifies review quality and retries if needed."""

    def __init__(
        self,
        threshold: int = None,
        max_retries: int = None,
        prompt_version: str = "base"
    ):
        """
        Initialize the verification loop.

        Args:
            threshold: Quality score threshold (0-100). Uses config default if None.
            max_retries: Maximum retry attempts. Uses config default if None.
            prompt_version: Version of prompt for agent loop
        """
        self.threshold = threshold or settings.quality_threshold
        self.max_retries = max_retries or settings.max_retries
        self.agent_loop = AgentLoop(prompt_version=prompt_version)
        self.grader = QualityGrader()

    def verified_review(self, git_diff: str = None) -> VerifiedReview:
        """
        Perform a code review with quality verification.

        Args:
            git_diff: Optional pre-fetched git diff

        Returns:
            VerifiedReview with quality score and retry information
        """
        print(f"\n[Loop 2] 🔍 Verification Loop - Starting (threshold: {self.threshold}/100)")
        start_time = time.time()

        retry_count = 0
        feedback_history = []

        while retry_count <= self.max_retries:
            # Determine if this is a retry
            attempt_label = f"Attempt {retry_count + 1}" if retry_count > 0 else "Initial attempt"
            print(f"\n[Loop 2] {attempt_label} {'(with feedback)' if feedback_history else ''}")

            # Run the review (Loop 1)
            context = {'feedback': feedback_history} if feedback_history else None
            review, metrics = self.agent_loop.review_code(git_diff=git_diff, context=context)

            # Get git diff if not provided (for grading)
            if git_diff is None:
                from src.tools.git_tools import get_git_diff
                git_diff = get_git_diff()

            # Grade the review quality
            quality_score, grading_feedback = self.grader.grade(review, git_diff)

            print(f"[Loop 2] 📊 Quality Score: {quality_score:.1f}/100", end="")

            # Check if passed
            if quality_score >= self.threshold:
                print(" ✅ PASSED")
                verification_time = time.time() - start_time

                return VerifiedReview(
                    review=review,
                    quality_score=quality_score,
                    quality_feedback=grading_feedback,
                    retry_count=retry_count,
                    passed=True,
                    verification_time=verification_time,
                )

            # Failed - check if we can retry
            print(f" ⚠️  Below threshold")

            if retry_count >= self.max_retries:
                print(f"[Loop 2] Max retries ({self.max_retries}) reached")
                break

            # Add feedback for next iteration
            feedback_history.append(grading_feedback)
            retry_count += 1

            print(f"[Loop 2] 🔄 Retrying ({retry_count}/{self.max_retries})...")

        # Max retries reached - return with failure flag
        verification_time = time.time() - start_time
        print(f"[Loop 2] ⚠️  Review did not pass quality threshold after {retry_count} retries")

        return VerifiedReview(
            review=review,
            quality_score=quality_score,
            quality_feedback=grading_feedback,
            retry_count=retry_count,
            passed=False,
            verification_time=verification_time,
        )
