"""Urgency classification for reviews."""
import re
from typing import List
import structlog

from src.models.review import Review, Issue, UrgencyLevel

logger = structlog.get_logger()


class UrgencyClassifier:
    """Classifies urgency level of reviews."""

    # Keywords indicating different urgency levels
    CRITICAL_KEYWORDS = [
        "dangerous", "unsafe", "injured", "hurt", "hospital", "emergency",
        "poisoned", "allergic reaction", "broke immediately", "fire", "smoke"
    ]

    HIGH_URGENCY_KEYWORDS = [
        "broken", "damaged", "defective", "not working", "stopped working",
        "disappointed", "terrible", "worst", "never again", "scam", "fraud",
        "refund immediately", "replacement asap"
    ]

    MEDIUM_URGENCY_KEYWORDS = [
        "issue", "problem", "concern", "unhappy", "dissatisfied",
        "expected better", "not as described", "missing", "incomplete"
    ]

    def __init__(self):
        """Initialize urgency classifier."""
        pass

    def classify(
        self,
        review: Review,
        sentiment: str,
        issues: List[Issue]
    ) -> UrgencyLevel:
        """
        Classify urgency level of a review.

        Uses a rule-based approach considering:
        - Sentiment
        - Rating
        - Keywords
        - Number and severity of issues

        Args:
            review: The review to classify
            sentiment: Sentiment analysis result
            issues: List of extracted issues

        Returns:
            UrgencyLevel enum value
        """
        text_lower = review.text.lower()
        score = 0

        # Factor 1: Rating (30% weight)
        if review.rating <= 1.5:
            score += 30
        elif review.rating <= 2.5:
            score += 20
        elif review.rating <= 3.5:
            score += 10
        else:
            score += 0

        # Factor 2: Sentiment (20% weight)
        if sentiment == "negative":
            score += 20
        elif sentiment == "neutral":
            score += 10

        # Factor 3: Keywords (30% weight)
        if any(keyword in text_lower for keyword in self.CRITICAL_KEYWORDS):
            score += 30
            logger.info("Critical keywords detected", review_id=review.id)
        elif any(keyword in text_lower for keyword in self.HIGH_URGENCY_KEYWORDS):
            score += 20
        elif any(keyword in text_lower for keyword in self.MEDIUM_URGENCY_KEYWORDS):
            score += 10

        # Factor 4: Issue severity (20% weight)
        if issues:
            high_severity_count = sum(1 for issue in issues if issue.severity == "high")
            medium_severity_count = sum(1 for issue in issues if issue.severity == "medium")

            if high_severity_count >= 2:
                score += 20
            elif high_severity_count >= 1:
                score += 15
            elif medium_severity_count >= 2:
                score += 10
            elif medium_severity_count >= 1:
                score += 5

        # Determine urgency level based on total score
        if score >= 70:
            urgency = UrgencyLevel.CRITICAL
        elif score >= 50:
            urgency = UrgencyLevel.HIGH
        elif score >= 30:
            urgency = UrgencyLevel.MEDIUM
        else:
            urgency = UrgencyLevel.LOW

        logger.debug(
            "Urgency classified",
            review_id=review.id,
            urgency=urgency.value,
            score=score
        )

        return urgency

    def get_response_priority(self, urgency: UrgencyLevel) -> int:
        """
        Get numeric priority for response ordering.

        Args:
            urgency: Urgency level

        Returns:
            Priority value (higher = more urgent)
        """
        priority_map = {
            UrgencyLevel.CRITICAL: 4,
            UrgencyLevel.HIGH: 3,
            UrgencyLevel.MEDIUM: 2,
            UrgencyLevel.LOW: 1
        }
        return priority_map.get(urgency, 1)

    def should_escalate(self, urgency: UrgencyLevel) -> bool:
        """
        Determine if review should be escalated to human.

        Args:
            urgency: Urgency level

        Returns:
            True if should escalate
        """
        return urgency in [UrgencyLevel.CRITICAL, UrgencyLevel.HIGH]
