"""Pytest configuration and shared fixtures."""
import pytest
from datetime import datetime
from typing import List

from src.models.review import Review, SentimentAnalysis, Issue, UrgencyLevel
from src.models.response import Response
from src.models.trace import ExecutionTrace, AgentStep
from src.models.verification import VerificationResult, CriteriaScore, VerificationCriteria


@pytest.fixture
def sample_review() -> Review:
    """Create a sample review for testing."""
    return Review(
        id="test_review_001",
        product_id="test_product_001",
        text="The product arrived damaged. Very disappointed with the quality.",
        rating=2.0,
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_positive_review() -> Review:
    """Create a sample positive review for testing."""
    return Review(
        id="test_review_002",
        product_id="test_product_002",
        text="Excellent product! Exceeded my expectations. Fast shipping too!",
        rating=5.0,
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_sentiment() -> SentimentAnalysis:
    """Create sample sentiment analysis."""
    return SentimentAnalysis(
        label="negative",
        score=0.85,
        confidence=0.92
    )


@pytest.fixture
def sample_issues() -> List[Issue]:
    """Create sample issues."""
    return [
        Issue(
            category="quality",
            description="Product arrived damaged",
            severity="high",
            confidence=0.90
        ),
        Issue(
            category="shipping",
            description="Packaging was inadequate",
            severity="medium",
            confidence=0.75
        )
    ]


@pytest.fixture
def sample_response() -> Response:
    """Create a sample response."""
    return Response(
        id="test_response_001",
        review_id="test_review_001",
        text="We sincerely apologize for receiving a damaged product. This is not the experience we want for our customers. Please contact our support team at support@example.com or call 1-800-123-4567 to arrange for a replacement or full refund. We'll also investigate the packaging issue to prevent this in the future.",
        strategy="apology_and_solution",
        timestamp=datetime.now(),
        version=1,
        tone="empathetic",
        key_points=["Apology", "Contact information", "Resolution options"],
        references=[]
    )


@pytest.fixture
def sample_trace(sample_review, sample_response) -> ExecutionTrace:
    """Create a sample execution trace."""
    return ExecutionTrace(
        id="test_trace_001",
        review_id=sample_review.id,
        timestamp=datetime.now(),
        steps=[
            AgentStep(
                step_id="step_001",
                action="sentiment_analysis",
                input={"text": sample_review.text},
                output={"sentiment": "negative", "score": 0.85},
                duration_ms=150,
                tool_calls=[]
            )
        ],
        tools_used=["sentiment_analyzer"],
        duration_ms=1200,
        response=sample_response,
        verification=None,
        prompt_version="v1.0",
        model_config={"model": "google/flan-t5-base"},
        success=True
    )


@pytest.fixture
def sample_verification_result() -> VerificationResult:
    """Create a sample verification result."""
    criteria_scores = {
        VerificationCriteria.RELEVANCE: CriteriaScore(
            criterion=VerificationCriteria.RELEVANCE,
            score=0.85,
            weight=0.25,
            rationale="Response addresses the main issues"
        ),
        VerificationCriteria.TONE: CriteriaScore(
            criterion=VerificationCriteria.TONE,
            score=0.90,
            weight=0.20,
            rationale="Empathetic and professional tone"
        ),
        VerificationCriteria.COMPLETENESS: CriteriaScore(
            criterion=VerificationCriteria.COMPLETENESS,
            score=0.80,
            weight=0.25,
            rationale="Covers most issues mentioned"
        ),
        VerificationCriteria.ACTIONABILITY: CriteriaScore(
            criterion=VerificationCriteria.ACTIONABILITY,
            score=0.85,
            weight=0.20,
            rationale="Clear next steps provided"
        ),
        VerificationCriteria.ACCURACY: CriteriaScore(
            criterion=VerificationCriteria.ACCURACY,
            score=0.95,
            weight=0.10,
            rationale="No factual errors detected"
        )
    }

    overall_score = sum(cs.score * cs.weight for cs.in criteria_scores.values())

    return VerificationResult(
        trace_id="test_trace_001",
        timestamp=datetime.now(),
        criteria_scores=criteria_scores,
        overall_score=overall_score,
        passed=overall_score >= 0.70,
        feedback="Good response overall. Could be slightly more specific about timeline.",
        improvement_suggestions=["Add expected timeline for resolution"]
    )
