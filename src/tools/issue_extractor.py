"""Issue extraction tool using zero-shot classification."""
from transformers import pipeline
from typing import List
import structlog

from src.config import settings
from src.models.review import Issue

logger = structlog.get_logger()


class IssueExtractor:
    """Extracts issues from reviews using zero-shot classification."""

    # Predefined issue categories
    ISSUE_CATEGORIES = [
        "product quality",
        "shipping and delivery",
        "customer service",
        "pricing and value",
        "product features",
        "packaging",
        "return and refund",
    ]

    def __init__(self):
        """Initialize the issue extractor."""
        self.model_name = settings.issue_classifier_model
        self.classifier = None
        self._initialized = False

    def _initialize(self):
        """Lazy initialization of classifier."""
        if self._initialized:
            return

        logger.info("Loading zero-shot classifier", model=self.model_name)
        try:
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=0 if settings.device == "cuda" else -1
            )
            self._initialized = True
            logger.info("Zero-shot classifier loaded successfully")
        except Exception as e:
            logger.error("Failed to load classifier", error=str(e))
            raise

    def extract(self, text: str, sentiment: str, threshold: float = 0.5) -> List[Issue]:
        """
        Extract issues from review text.

        Args:
            text: Review text
            sentiment: Sentiment of the review (positive, negative, neutral)
            threshold: Minimum confidence threshold for issue detection

        Returns:
            List of extracted issues
        """
        self._initialize()

        # Only extract issues for negative or neutral reviews
        if sentiment == "positive":
            return []

        try:
            # Classify text against issue categories
            result = self.classifier(
                text,
                self.ISSUE_CATEGORIES,
                multi_label=True
            )

            # Extract issues above threshold
            issues = []
            for label, score in zip(result["labels"], result["scores"]):
                if score >= threshold:
                    # Determine severity based on score and sentiment
                    if sentiment == "negative":
                        if score >= 0.8:
                            severity = "high"
                        elif score >= 0.6:
                            severity = "medium"
                        else:
                            severity = "low"
                    else:  # neutral
                        severity = "medium" if score >= 0.7 else "low"

                    # Extract category name (remove "and" words for cleaner category)
                    category = label.replace("product ", "").replace(" and ", "_").replace(" ", "_")

                    issues.append(
                        Issue(
                            category=category,
                            description=f"Issue related to {label}",
                            severity=severity,
                            confidence=score
                        )
                    )

            logger.debug(
                "Issue extraction complete",
                text_length=len(text),
                num_issues=len(issues)
            )

            return issues

        except Exception as e:
            logger.error("Issue extraction failed", error=str(e))
            # Return empty list as fallback
            return []

    def extract_detailed(self, text: str, sentiment: str) -> List[Issue]:
        """
        Extract issues with detailed descriptions from text.

        This is a simplified version. In production, you might use:
        - Named entity recognition to extract specific product mentions
        - Aspect-based sentiment analysis
        - More sophisticated NLP pipelines

        Args:
            text: Review text
            sentiment: Sentiment classification

        Returns:
            List of issues with detailed descriptions
        """
        # Get base issues
        issues = self.extract(text, sentiment)

        # Enhance descriptions with text analysis
        for issue in issues:
            # Find relevant sentences mentioning the issue category
            sentences = text.split('.')
            relevant_sentences = [
                s.strip() for s in sentences
                if any(word in s.lower() for word in issue.category.split('_'))
            ]

            if relevant_sentences:
                issue.description = relevant_sentences[0][:200]  # Limit length

        return issues
