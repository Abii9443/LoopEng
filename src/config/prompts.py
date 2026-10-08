"""Prompt templates for response generation."""
from typing import Dict, List
from src.models.review import Review, Issue


class PromptManager:
    """Manages prompt templates and versions."""

    def __init__(self):
        """Initialize with base prompts."""
        self.version = "v1.0"
        self.base_prompts = self._load_base_prompts()

    def _load_base_prompts(self) -> Dict[str, str]:
        """Load base prompt templates."""
        return {
            "system": """You are a professional customer service AI assistant. Your goal is to provide helpful, empathetic, and actionable responses to customer reviews.""",

            "positive_review": """Generate a professional and grateful response to the following positive customer review.

Review Text: {review_text}
Rating: {rating}/5.0

Key Points to Address:
{key_points}

Guidelines:
- Express sincere gratitude
- Acknowledge specific positive aspects mentioned
- Encourage continued engagement
- Keep tone warm and professional

Response:""",

            "negative_review": """Generate an empathetic and solution-oriented response to the following negative customer review.

Review Text: {review_text}
Rating: {rating}/5.0

Identified Issues:
{issues}

Guidelines:
- Start with a sincere apology
- Address each issue specifically
- Provide clear next steps or solutions
- Offer contact information for further assistance
- Show understanding and empathy
- Keep tone professional yet caring

Response:""",

            "neutral_review": """Generate a balanced and helpful response to the following customer review.

Review Text: {review_text}
Rating: {rating}/5.0

Key Points:
{key_points}

Guidelines:
- Thank the customer for feedback
- Address any specific points mentioned
- Offer to assist with any concerns
- Keep tone professional and helpful

Response:""",

            "retry_with_feedback": """Revise your previous response based on this feedback.

Original Response:
{original_response}

Feedback:
{feedback}

Specific Issues to Address:
{issues_to_address}

Generate an improved response that addresses the feedback:""",
        }

    def get_prompt(
        self,
        review: Review,
        sentiment: str,
        issues: List[Issue] = None,
        feedback: str = None,
        original_response: str = None
    ) -> str:
        """
        Get the appropriate prompt for response generation.

        Args:
            review: The review to respond to
            sentiment: Sentiment classification (positive, negative, neutral)
            issues: List of identified issues (for negative reviews)
            feedback: Feedback for retry (optional)
            original_response: Original response for retry (optional)

        Returns:
            Formatted prompt string
        """
        if feedback and original_response:
            # Retry with feedback
            issues_text = "\n".join(f"- {issue}" for issue in issues) if issues else "None specified"
            return self.base_prompts["retry_with_feedback"].format(
                original_response=original_response,
                feedback=feedback,
                issues_to_address=issues_text
            )

        # Select template based on sentiment
        if sentiment == "positive":
            template = self.base_prompts["positive_review"]
            key_points = "Positive aspects mentioned in the review"
            return template.format(
                review_text=review.text,
                rating=review.rating,
                key_points=key_points
            )
        elif sentiment == "negative":
            template = self.base_prompts["negative_review"]
            issues_text = "\n".join(
                f"- {issue.category.upper()}: {issue.description}"
                for issue in (issues or [])
            )
            return template.format(
                review_text=review.text,
                rating=review.rating,
                issues=issues_text if issues_text else "General dissatisfaction"
            )
        else:  # neutral
            template = self.base_prompts["neutral_review"]
            key_points = "Mixed feedback with both positive and negative aspects"
            return template.format(
                review_text=review.text,
                rating=review.rating,
                key_points=key_points
            )

    def update_prompt(self, prompt_key: str, new_template: str):
        """
        Update a specific prompt template (used by hill climbing).

        Args:
            prompt_key: Key of the prompt to update
            new_template: New template string
        """
        if prompt_key in self.base_prompts:
            self.base_prompts[prompt_key] = new_template
            # Increment version
            version_num = float(self.version.replace("v", ""))
            self.version = f"v{version_num + 0.1:.1f}"

    def get_version(self) -> str:
        """Get current prompt version."""
        return self.version


# Global prompt manager instance
prompt_manager = PromptManager()
