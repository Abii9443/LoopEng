"""Sentiment analysis tool using HuggingFace transformers."""
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import Dict
import structlog

from src.config import settings
from src.models.review import SentimentAnalysis

logger = structlog.get_logger()


class SentimentAnalyzer:
    """Analyzes sentiment of review text using HuggingFace model."""

    def __init__(self):
        """Initialize the sentiment analyzer."""
        self.model_name = settings.sentiment_model
        self.device = settings.device
        self.tokenizer = None
        self.model = None
        self._initialized = False

    def _initialize(self):
        """Lazy initialization of model and tokenizer."""
        if self._initialized:
            return

        logger.info("Loading sentiment analysis model", model=self.model_name)
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            self._initialized = True
            logger.info("Sentiment model loaded successfully")
        except Exception as e:
            logger.error("Failed to load sentiment model", error=str(e))
            raise

    def analyze(self, text: str) -> SentimentAnalysis:
        """
        Analyze sentiment of text.

        Args:
            text: Input text to analyze

        Returns:
            SentimentAnalysis object with label, score, and confidence
        """
        self._initialize()

        try:
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)

            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

            # Get label and score
            predicted_class = torch.argmax(probs, dim=1).item()
            confidence = probs[0][predicted_class].item()

            # Map to sentiment labels
            # Model outputs: 0=negative, 1=neutral, 2=positive (for roberta-sentiment)
            label_map = {0: "negative", 1: "neutral", 2: "positive"}
            label = label_map.get(predicted_class, "neutral")

            # Score is the probability of the predicted class
            score = confidence

            logger.debug(
                "Sentiment analysis complete",
                text_length=len(text),
                label=label,
                score=score
            )

            return SentimentAnalysis(
                label=label,
                score=score,
                confidence=confidence
            )

        except Exception as e:
            logger.error("Sentiment analysis failed", error=str(e))
            # Return neutral sentiment as fallback
            return SentimentAnalysis(
                label="neutral",
                score=0.5,
                confidence=0.5
            )

    def batch_analyze(self, texts: list) -> list:
        """
        Analyze sentiment of multiple texts in batch.

        Args:
            texts: List of texts to analyze

        Returns:
            List of SentimentAnalysis objects
        """
        self._initialize()

        results = []
        # Process in batches of 8
        batch_size = 8
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                result = self.analyze(text)
                results.append(result)

        return results
