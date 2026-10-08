"""Response quality grader for verification loop."""
from typing import Dict, List
import re
import structlog

from src.config import settings
from src.models.review import Review, Issue
from src.models.response import Response
from src.models.verification import VerificationCriteria, CriteriaScore

logger = structlog.get_logger()


class ResponseGrader:
    """Grades response quality against multiple criteria."""

    def __init__(self):
        """Initialize response grader."""
        self.weights = settings.get_verification_weights()

    def grade_all_criteria(
        self,
        review: Review,
        response: Response
    ) -> Dict[str, CriteriaScore]:
        """
        Grade response against all criteria.

        Args:
            review: Original review
            response: Generated response

        Returns:
            Dictionary of criterion name to CriteriaScore
        """
        criteria_scores = {}

        # Grade each criterion
        criteria_scores[VerificationCriteria.RELEVANCE] = self.grade_relevance(review, response)
        criteria_scores[VerificationCriteria.TONE] = self.grade_tone(review, response)
        criteria_scores[VerificationCriteria.COMPLETENESS] = self.grade_completeness(review, response)
        criteria_scores[VerificationCriteria.ACTIONABILITY] = self.grade_actionability(review, response)
        criteria_scores[VerificationCriteria.ACCURACY] = self.grade_accuracy(review, response)

        logger.debug(
            "All criteria graded",
            review_id=review.id,
            response_id=response.id,
            scores={k: f"{v.score:.2f}" for k, v in criteria_scores.items()}
        )

        return criteria_scores

    def grade_relevance(self, review: Review, response: Response) -> CriteriaScore:
        """
        Grade relevance: Does the response address the review content?

        Uses keyword overlap and semantic matching.
        """
        score = 0.0
        rationale_parts = []

        # Extract key terms from review
        review_words = set(review.text.lower().split())
        response_words = set(response.text.lower().split())

        # Calculate word overlap (excluding common words)
        common_words = {"the", "a", "an", "is", "was", "are", "were", "i", "you", "we", "it", "this", "that"}
        review_words = review_words - common_words
        response_words = response_words - common_words

        if review_words:
            overlap = len(review_words & response_words) / len(review_words)
            score += overlap * 0.4  # 40% weight on word overlap
            rationale_parts.append(f"Word overlap: {overlap:.1%}")

        # Check if response addresses sentiment
        if review.sentiment:
            sentiment = review.sentiment.label
            if sentiment == "negative":
                if any(word in response.text.lower() for word in ["sorry", "apolog", "unfortunate", "regret"]):
                    score += 0.3  # 30% for appropriate tone
                    rationale_parts.append("Acknowledges negative sentiment")
                else:
                    rationale_parts.append("Missing acknowledgment of issue")
            elif sentiment == "positive":
                if any(word in response.text.lower() for word in ["thank", "appreciate", "glad", "pleased"]):
                    score += 0.3
                    rationale_parts.append("Thanks for positive feedback")

        # Check if response addresses issues
        if review.issues and len(review.issues) > 0:
            issues_mentioned = sum(
                1 for issue in review.issues
                if any(word in response.text.lower() for word in issue.category.split("_"))
            )
            if issues_mentioned > 0:
                score += 0.3 * (issues_mentioned / len(review.issues))
                rationale_parts.append(f"Addresses {issues_mentioned}/{len(review.issues)} issues")
            else:
                rationale_parts.append("Issues not explicitly addressed")
        else:
            score += 0.3  # No issues to address

        # Ensure score is between 0 and 1
        score = min(1.0, max(0.0, score))

        rationale = "; ".join(rationale_parts) if rationale_parts else "Basic relevance check passed"

        return CriteriaScore(
            criterion=VerificationCriteria.RELEVANCE,
            score=score,
            weight=self.weights[VerificationCriteria.RELEVANCE],
            rationale=rationale
        )

    def grade_tone(self, review: Review, response: Response) -> CriteriaScore:
        """
        Grade tone: Is the tone appropriate for the review sentiment?
        """
        score = 0.5  # Base score
        rationale_parts = []

        if not review.sentiment:
            return CriteriaScore(
                criterion=VerificationCriteria.TONE,
                score=0.5,
                weight=self.weights[VerificationCriteria.TONE],
                rationale="No sentiment data available"
            )

        sentiment = review.sentiment.label
        response_lower = response.text.lower()

        # Define tone indicators
        empathy_words = ["sorry", "apologize", "understand", "regret", "unfortunate", "concern"]
        gratitude_words = ["thank", "appreciate", "grateful", "pleased", "delighted"]
        professional_words = ["contact", "assist", "help", "support", "resolve"]
        cold_words = ["however", "unfortunately", "cannot", "unable", "policy"]

        empathy_count = sum(1 for word in empathy_words if word in response_lower)
        gratitude_count = sum(1 for word in gratitude_words if word in response_lower)
        professional_count = sum(1 for word in professional_words if word in response_lower)
        cold_count = sum(1 for word in cold_words if word in response_lower)

        if sentiment == "negative":
            # Should be empathetic and professional
            if empathy_count >= 2:
                score += 0.3
                rationale_parts.append(f"Good empathy ({empathy_count} indicators)")
            elif empathy_count >= 1:
                score += 0.15
                rationale_parts.append("Some empathy shown")
            else:
                score -= 0.2
                rationale_parts.append("Lacks empathy for negative experience")

            if professional_count >= 1:
                score += 0.2
                rationale_parts.append("Professional assistance offered")

            if cold_count > 2:
                score -= 0.15
                rationale_parts.append("Tone too formal/cold")

        elif sentiment == "positive":
            # Should be grateful and warm
            if gratitude_count >= 1:
                score += 0.4
                rationale_parts.append(f"Expresses gratitude ({gratitude_count} times)")
            else:
                score -= 0.2
                rationale_parts.append("Missing gratitude for positive feedback")

            if professional_count >= 1:
                score += 0.1
                rationale_parts.append("Professional touch")

        else:  # neutral
            # Should be balanced and professional
            if professional_count >= 1:
                score += 0.3
                rationale_parts.append("Professional tone maintained")

            if empathy_count >= 1 or gratitude_count >= 1:
                score += 0.2
                rationale_parts.append("Appropriate warmth")

        # Ensure score is between 0 and 1
        score = min(1.0, max(0.0, score))

        rationale = "; ".join(rationale_parts) if rationale_parts else "Tone assessment complete"

        return CriteriaScore(
            criterion=VerificationCriteria.TONE,
            score=score,
            weight=self.weights[VerificationCriteria.TONE],
            rationale=rationale
        )

    def grade_completeness(self, review: Review, response: Response) -> CriteriaScore:
        """
        Grade completeness: Does the response cover all important points?
        """
        score = 0.5  # Base score
        rationale_parts = []

        # Check if issues are addressed
        if review.issues and len(review.issues) > 0:
            covered_issues = 0
            for issue in review.issues:
                # Check if issue category or related words appear in response
                category_words = issue.category.replace("_", " ").split()
                if any(word in response.text.lower() for word in category_words):
                    covered_issues += 1

            coverage_ratio = covered_issues / len(review.issues)
            score = 0.3 + (coverage_ratio * 0.7)  # 30-100% based on coverage
            rationale_parts.append(f"Covers {covered_issues}/{len(review.issues)} identified issues")
        else:
            score = 0.8  # No specific issues to cover
            rationale_parts.append("No specific issues to address")

        # Check for essential response elements
        has_greeting = any(word in response.text.lower() for word in ["hello", "hi", "thank", "dear"])
        has_acknowledgment = len(response.text) > 50  # At least a substantial response
        has_next_steps = any(word in response.text.lower() for word in ["contact", "reach", "call", "email", "visit"])

        if has_greeting:
            rationale_parts.append("Includes greeting/acknowledgment")
        if has_next_steps:
            rationale_parts.append("Provides next steps")
        elif review.sentiment and review.sentiment.label == "negative":
            score -= 0.1
            rationale_parts.append("Missing actionable next steps")

        score = min(1.0, max(0.0, score))

        rationale = "; ".join(rationale_parts) if rationale_parts else "Completeness check done"

        return CriteriaScore(
            criterion=VerificationCriteria.COMPLETENESS,
            score=score,
            weight=self.weights[VerificationCriteria.COMPLETENESS],
            rationale=rationale
        )

    def grade_actionability(self, review: Review, response: Response) -> CriteriaScore:
        """
        Grade actionability: Does the response provide clear next steps?
        """
        score = 0.0
        rationale_parts = []

        response_lower = response.text.lower()

        # Check for contact information
        has_email = "@" in response.text or "email" in response_lower
        has_phone = bool(re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', response.text)) or "phone" in response_lower or "call" in response_lower
        has_website = "website" in response_lower or "http" in response_lower or ".com" in response_lower

        if has_email:
            score += 0.3
            rationale_parts.append("Email contact provided")
        if has_phone:
            score += 0.3
            rationale_parts.append("Phone contact provided")
        if has_website:
            score += 0.1
            rationale_parts.append("Website reference provided")

        # Check for action words
        action_words = ["contact", "reach", "call", "email", "visit", "click", "follow", "check"]
        action_count = sum(1 for word in action_words if word in response_lower)

        if action_count >= 2:
            score += 0.3
            rationale_parts.append(f"Clear action items ({action_count} action words)")
        elif action_count == 1:
            score += 0.15
            rationale_parts.append("Some action guidance")

        # For positive reviews, actionability might be lower priority
        if review.sentiment and review.sentiment.label == "positive":
            if score < 0.5:
                score = max(score, 0.6)  # Boost score for positive reviews
                rationale_parts.append("Limited action needed for positive review")

        if not rationale_parts:
            rationale_parts.append("No clear next steps provided")

        score = min(1.0, max(0.0, score))

        rationale = "; ".join(rationale_parts)

        return CriteriaScore(
            criterion=VerificationCriteria.ACTIONABILITY,
            score=score,
            weight=self.weights[VerificationCriteria.ACTIONABILITY],
            rationale=rationale
        )

    def grade_accuracy(self, review: Review, response: Response) -> CriteriaScore:
        """
        Grade accuracy: No hallucinated or false information.

        This is a simplified version. In production, you would:
        - Check against a fact database
        - Verify product information
        - Ensure consistency with company policies
        """
        score = 0.8  # Default: assume mostly accurate
        rationale_parts = []

        response_lower = response.text.lower()

        # Check for overly specific claims that might be hallucinated
        suspicious_patterns = [
            r'\d+%',  # Specific percentages
            r'\$\d+\.\d{2}',  # Specific prices
            r'within \d+ (hours|days|weeks)',  # Specific timeframes
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, response.text):
                score -= 0.1
                rationale_parts.append(f"Contains specific claim: {pattern}")

        # Check for contradictions with review
        if "excellent" in response_lower and review.rating < 3.0:
            score -= 0.2
            rationale_parts.append("Response tone contradicts low rating")

        # Ensure no obviously false statements
        false_indicators = ["guarantee", "promise", "definitely", "certainly will"]
        false_count = sum(1 for word in false_indicators if word in response_lower)
        if false_count > 0:
            score -= 0.05 * false_count
            rationale_parts.append(f"Contains {false_count} absolute statements")

        if not rationale_parts:
            rationale_parts.append("No obvious accuracy issues detected")

        score = min(1.0, max(0.5, score))  # Minimum 0.5 unless major issues

        rationale = "; ".join(rationale_parts)

        return CriteriaScore(
            criterion=VerificationCriteria.ACCURACY,
            score=score,
            weight=self.weights[VerificationCriteria.ACCURACY],
            rationale=rationale
        )
