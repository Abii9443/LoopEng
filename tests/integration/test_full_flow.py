"""Integration tests for full review processing flow."""
import pytest
import asyncio
from datetime import datetime

from src.orchestration.coordinator import LoopCoordinator
from src.models.review import Review


@pytest.mark.asyncio
async def test_single_review_processing():
    """Test processing a single review through all loops."""
    coordinator = LoopCoordinator()

    review = Review(
        id="test_review_001",
        product_id="test_product_001",
        text="The product arrived damaged. Very disappointed with the quality.",
        rating=2.0,
        timestamp=datetime.now()
    )

    # Process through Loop 1 and Loop 2
    trace = await coordinator.process_review(review, with_verification=True, with_retry=True)

    # Verify trace was created
    assert trace is not None
    assert trace.review_id == review.id
    assert trace.response is not None
    assert len(trace.steps) > 0

    # Verify response was generated
    assert len(trace.response.text) > 0
    assert trace.response.strategy in ["apology_and_solution", "apology_and_support"]

    # Verify verification was performed
    assert trace.verification is not None
    assert isinstance(trace.verification.overall_score, float)
    assert 0 <= trace.verification.overall_score <= 1

    # Verify criteria scores
    assert len(trace.verification.criteria_scores) == 5
    for criterion, score_obj in trace.verification.criteria_scores.items():
        assert 0 <= score_obj.score <= 1
        assert len(score_obj.rationale) > 0


@pytest.mark.asyncio
async def test_positive_review_processing():
    """Test processing a positive review."""
    coordinator = LoopCoordinator()

    review = Review(
        id="test_review_002",
        product_id="test_product_002",
        text="Excellent product! Exceeded my expectations. Highly recommend!",
        rating=5.0,
        timestamp=datetime.now()
    )

    trace = await coordinator.process_review(review)

    # Verify positive sentiment handling
    assert trace.response.strategy in ["gratitude_and_encouragement", "gratitude"]
    assert trace.response.tone in ["grateful", "professional"]


@pytest.mark.asyncio
async def test_batch_processing():
    """Test batch processing of multiple reviews."""
    coordinator = LoopCoordinator()

    reviews = [
        Review(
            id=f"batch_test_{i}",
            product_id=f"product_{i}",
            text="Test review text" if i % 2 == 0 else "Great product!",
            rating=2.0 if i % 2 == 0 else 5.0,
            timestamp=datetime.now()
        )
        for i in range(5)
    ]

    traces = await coordinator.process_batch(reviews, parallel=False)

    # Verify all reviews were processed
    assert len(traces) == len(reviews)

    # Verify all have responses and verifications
    for trace in traces:
        assert trace.response is not None
        if trace.verification:  # May not all have verification in test
            assert trace.verification.overall_score >= 0


def test_coordinator_status():
    """Test coordinator status reporting."""
    coordinator = LoopCoordinator()

    status = coordinator.get_status()

    assert "reviews_processed" in status
    assert "next_hill_climbing_at" in status
    assert isinstance(status["reviews_processed"], int)
