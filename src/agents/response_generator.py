"""Response generator using HuggingFace T5 model."""
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from typing import List, Dict, Optional
import structlog
from uuid import uuid4

from src.config import settings, prompt_manager
from src.models.review import Review, Issue
from src.models.response import Response

logger = structlog.get_logger()


class ResponseGenerator:
    """Generates responses to reviews using HuggingFace T5 model."""

    def __init__(self):
        """Initialize response generator."""
        self.model_name = settings.generation_model
        self.device = settings.device
        self.tokenizer = None
        self.model = None
        self._initialized = False

    def _initialize(self):
        """Lazy initialization of model and tokenizer."""
        if self._initialized:
            return

        logger.info("Loading response generation model", model=self.model_name)
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            self._initialized = True
            logger.info("Response generation model loaded successfully")
        except Exception as e:
            logger.error("Failed to load generation model", error=str(e))
            raise

    def generate(
        self,
        review: Review,
        sentiment: str,
        issues: Optional[List[Issue]] = None,
        context: Optional[List[Dict]] = None,
        feedback: Optional[str] = None,
        original_response: Optional[str] = None,
        version: int = 1
    ) -> Response:
        """
        Generate response to a review.

        Args:
            review: The review to respond to
            sentiment: Sentiment classification
            issues: Extracted issues
            context: Knowledge base context (similar successful responses)
            feedback: Feedback for retry (optional)
            original_response: Original response for retry (optional)
            version: Response version number

        Returns:
            Generated Response object
        """
        self._initialize()

        try:
            # Build prompt
            if feedback and original_response:
                # Retry with feedback
                prompt = prompt_manager.get_prompt(
                    review=review,
                    sentiment=sentiment,
                    issues=issues,
                    feedback=feedback,
                    original_response=original_response
                )
            else:
                # Initial generation
                prompt = prompt_manager.get_prompt(
                    review=review,
                    sentiment=sentiment,
                    issues=issues
                )

            # Add context from knowledge base if available
            if context:
                context_text = "\n\nSimilar successful responses:\n"
                for idx, ctx in enumerate(context[:2], 1):  # Use top 2
                    context_text += f"{idx}. {ctx['response_text'][:150]}...\n"
                prompt = prompt + context_text

            # Generate response
            response_text = self._generate_text(prompt)

            # Determine strategy based on sentiment
            strategy = self._determine_strategy(sentiment, issues)

            # Extract tone and key points
            tone = self._analyze_tone(response_text, sentiment)
            key_points = self._extract_key_points(response_text, issues)

            # Get references from context
            references = [f"kb_entry_{i}" for i in range(len(context))] if context else []

            response = Response(
                id=str(uuid4()),
                review_id=review.id,
                text=response_text,
                strategy=strategy,
                version=version,
                tone=tone,
                key_points=key_points,
                references=references
            )

            logger.info(
                "Response generated",
                review_id=review.id,
                version=version,
                strategy=strategy,
                length=len(response_text)
            )

            return response

        except Exception as e:
            logger.error("Response generation failed", error=str(e))
            # Return fallback response
            return self._create_fallback_response(review, sentiment, version)

    def _generate_text(self, prompt: str, max_length: int = 256) -> str:
        """Generate text using the model."""
        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(self.device)

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                num_beams=4,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.2
            )

        # Decode
        response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        return response_text.strip()

    def _determine_strategy(self, sentiment: str, issues: Optional[List[Issue]]) -> str:
        """Determine response strategy based on sentiment and issues."""
        if sentiment == "positive":
            return "gratitude_and_encouragement"
        elif sentiment == "negative":
            if issues and len(issues) > 0:
                return "apology_and_solution"
            else:
                return "apology_and_support"
        else:  # neutral
            return "balanced_acknowledgment"

    def _analyze_tone(self, response_text: str, sentiment: str) -> str:
        """Analyze tone of generated response."""
        # Simple keyword-based tone detection
        empathy_keywords = ["sorry", "apologize", "understand", "regret", "unfortunate"]
        professional_keywords = ["contact", "assist", "resolve", "support", "team"]
        grateful_keywords = ["thank", "appreciate", "grateful", "pleased"]

        text_lower = response_text.lower()

        if any(word in text_lower for word in empathy_keywords):
            return "empathetic"
        elif any(word in text_lower for word in grateful_keywords):
            return "grateful"
        elif any(word in text_lower for word in professional_keywords):
            return "professional"
        else:
            return "neutral"

    def _extract_key_points(self, response_text: str, issues: Optional[List[Issue]]) -> List[str]:
        """Extract key points from response."""
        key_points = []

        # Check for common elements
        if "apolog" in response_text.lower():
            key_points.append("Apology")

        if "contact" in response_text.lower() or "support" in response_text.lower():
            key_points.append("Contact information provided")

        if "refund" in response_text.lower() or "replacement" in response_text.lower():
            key_points.append("Resolution offered")

        if issues:
            key_points.append(f"Addressed {len(issues)} issue(s)")

        if "thank" in response_text.lower():
            key_points.append("Gratitude expressed")

        return key_points if key_points else ["General response"]

    def _create_fallback_response(self, review: Review, sentiment: str, version: int) -> Response:
        """Create a simple fallback response."""
        if sentiment == "negative":
            text = (
                "We sincerely apologize for your experience. "
                "Please contact our customer support team so we can make this right. "
                "You can reach us at support@example.com or call 1-800-123-4567."
            )
            strategy = "apology_and_support"
            tone = "empathetic"
        elif sentiment == "positive":
            text = (
                "Thank you so much for your wonderful feedback! "
                "We're thrilled to hear you're enjoying our product. "
                "We look forward to serving you again!"
            )
            strategy = "gratitude_and_encouragement"
            tone = "grateful"
        else:  # neutral
            text = (
                "Thank you for taking the time to share your feedback. "
                "If you have any questions or concerns, please don't hesitate to contact us."
            )
            strategy = "balanced_acknowledgment"
            tone = "professional"

        return Response(
            id=str(uuid4()),
            review_id=review.id,
            text=text,
            strategy=strategy,
            version=version,
            tone=tone,
            key_points=["Fallback response"],
            references=[]
        )
