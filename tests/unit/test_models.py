"""Unit tests for data models."""
import pytest
from datetime import datetime

from src.models.review import Review, SentimentAnalysis, Issue, UrgencyLevel
from src.models.response import Response
from src.models.verification import VerificationResult, CriteriaScore, VerificationCriteria


def test_review_creation():
    """Test Review model creation."""
    review = Review(
        id="test_001",
        product_id="prod_001",
        text="Great product!",
        rating=5.0
    )

    assert review.id == "test_001"
    assert review.rating == 5.0
    assert review.sentiment is None  # Not yet analyzed


def test_sentiment_analysis():
    """Test SentimentAnalysis model."""
    sentiment = SentimentAnalysis(
        label="positive",
        score=0.95,
        confidence=0.98
    )

    assert sentiment.label == "positive"
    assert 0 <= sentiment.score <= 1
    assert 0 <= sentiment.confidence <= 1


def test_issue_creation():
    """Test Issue model."""
    issue = Issue(
        category="quality",
        description="Product arrived damaged",
        severity="high",
        confidence=0.9
    )

    assert issue.category == "quality"
    assert issue.severity == "high"


def test_response_creation():
    """Test Response model."""
    response = Response(
        id="resp_001",
        review_id="review_001",
        text="Thank you for your feedback!",
        strategy="gratitude",
        version=1
    )

    assert response.version == 1
    assert response.review_id == "review_001"


def test_criteria_score():
    """Test CriteriaScore model."""
    score = CriteriaScore(
        criterion=VerificationCriteria.RELEVANCE,
        score=0.85,
        weight=0.25,
        rationale="Good relevance"
    )

    assert score.score == 0.85
    assert score.weight == 0.25


def test_verification_result():
    """Test VerificationResult model."""
    criteria_scores = {
        VerificationCriteria.RELEVANCE: CriteriaScore(
            criterion=VerificationCriteria.RELEVANCE,
            score=0.85,
            weight=0.25,
            rationale="Good"
        )
    }

    result = VerificationResult(
        trace_id="trace_001",
        criteria_scores=criteria_scores,
        overall_score=0.85,
        passed=True,
        feedback="Good response"
    )

    assert result.passed
    assert result.overall_score == 0.85
