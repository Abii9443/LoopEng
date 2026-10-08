"""Dataset loader for Amazon reviews from HuggingFace."""
from typing import List, Optional
from datetime import datetime
from datasets import load_dataset
import structlog

from src.config import settings
from src.models.review import Review

logger = structlog.get_logger()


class DatasetLoader:
    """Loads and converts reviews from HuggingFace datasets."""

    def __init__(self):
        """Initialize dataset loader."""
        self.dataset_name = settings.dataset_name
        self.dataset_split = settings.dataset_split

    def load_reviews(
        self,
        count: Optional[int] = None,
        shuffle: bool = True
    ) -> List[Review]:
        """
        Load reviews from HuggingFace dataset.

        Args:
            count: Number of reviews to load (None = all from split)
            shuffle: Whether to shuffle reviews

        Returns:
            List of Review objects
        """
        logger.info(
            "Loading reviews from HuggingFace",
            dataset=self.dataset_name,
            split=self.dataset_split
        )

        try:
            # Load dataset
            dataset = load_dataset(self.dataset_name, split=self.dataset_split)

            if shuffle:
                dataset = dataset.shuffle(seed=42)

            # Convert to Review objects
            reviews = []
            limit = count if count else len(dataset)

            for idx, item in enumerate(dataset):
                if idx >= limit:
                    break

                review = self._convert_to_review(item, idx)
                if review:
                    reviews.append(review)

            logger.info(f"Loaded {len(reviews)} reviews")

            return reviews

        except Exception as e:
            logger.error("Failed to load dataset", error=str(e))
            # Return synthetic fallback reviews
            return self._create_fallback_reviews(count or 100)

    def _convert_to_review(self, item: dict, idx: int) -> Optional[Review]:
        """Convert dataset item to Review object."""
        try:
            # Amazon polarity dataset format
            if "content" in item and "label" in item:
                # Label: 0 = negative (1-2 stars), 1 = positive (4-5 stars)
                label = item["label"]
                rating = 2.0 if label == 0 else 4.5

                return Review(
                    id=f"review_{idx:06d}",
                    product_id=f"product_{idx % 1000:04d}",
                    text=item["content"],
                    rating=rating,
                    timestamp=datetime.now()
                )

            # Generic format
            elif "text" in item:
                rating = item.get("rating", 3.0)

                return Review(
                    id=f"review_{idx:06d}",
                    product_id=f"product_{idx % 1000:04d}",
                    text=item["text"],
                    rating=float(rating),
                    timestamp=datetime.now()
                )

            return None

        except Exception as e:
            logger.warning(f"Failed to convert item {idx}", error=str(e))
            return None

    def _create_fallback_reviews(self, count: int) -> List[Review]:
        """Create synthetic reviews as fallback."""
        logger.warning("Creating synthetic fallback reviews")

        templates = [
            # Negative reviews
            ("The product arrived damaged and doesn't work properly. Very disappointed with the quality.", 1.5),
            ("Terrible experience. The item broke after just one use. Would not recommend.", 1.0),
            ("Not as described. The product is much smaller than expected and feels cheap.", 2.0),
            ("Arrived late and in poor condition. Customer service was unhelpful.", 2.0),
            ("The quality is terrible for the price. I've seen better at dollar stores.", 1.5),

            # Positive reviews
            ("Excellent product! Exceeded my expectations. Would definitely buy again.", 5.0),
            ("Great quality and fast shipping. Very satisfied with this purchase!", 4.5),
            ("Amazing! Works perfectly and looks even better than the pictures.", 5.0),
            ("Best purchase I've made in a long time. Highly recommend to everyone.", 5.0),
            ("Love it! The quality is outstanding and it arrived quickly.", 4.5),

            # Neutral reviews
            ("The product is okay. Does what it's supposed to do but nothing special.", 3.0),
            ("Average quality. Works fine but I expected more for the price.", 3.0),
            ("It's fine. Not great, not terrible. Just average.", 3.0),
            ("Decent product. Has some pros and cons. Overall acceptable.", 3.5),
            ("Works as advertised. Nothing to complain about but nothing exciting either.", 3.0),
        ]

        reviews = []
        for idx in range(count):
            text, rating = templates[idx % len(templates)]

            review = Review(
                id=f"synthetic_{idx:06d}",
                product_id=f"product_{idx % 100:04d}",
                text=text,
                rating=rating,
                timestamp=datetime.now()
            )
            reviews.append(review)

        return reviews

    def create_sample_reviews(self, count: int = 10) -> List[Review]:
        """Create a small sample of diverse reviews for testing."""
        return self._create_fallback_reviews(count)


# Global dataset loader instance
dataset_loader = DatasetLoader()
