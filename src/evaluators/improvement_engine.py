"""Improvement engine for generating hypotheses from patterns."""
from typing import List, Tuple, Optional
from datetime import datetime
from uuid import uuid4
import structlog

from src.config import prompt_manager
from src.models.improvement import ImprovementHypothesis, Pattern
from src.models.trace import ExecutionTrace

logger = structlog.get_logger()


class ImprovementEngine:
    """Generates improvement hypotheses from detected patterns."""

    def __init__(self):
        """Initialize improvement engine."""
        pass

    def generate_hypotheses(
        self,
        patterns: List[Pattern],
        traces: List[ExecutionTrace]
    ) -> List[ImprovementHypothesis]:
        """
        Generate improvement hypotheses from patterns.

        Args:
            patterns: Detected patterns
            traces: Supporting traces

        Returns:
            List of improvement hypotheses
        """
        logger.info("Generating improvement hypotheses", num_patterns=len(patterns))

        hypotheses = []

        for pattern in patterns:
            if not pattern.is_actionable:
                continue

            hypothesis = self._generate_hypothesis_for_pattern(pattern, traces)
            if hypothesis:
                hypotheses.append(hypothesis)

        logger.info("Hypotheses generated", count=len(hypotheses))

        return hypotheses

    def _generate_hypothesis_for_pattern(
        self,
        pattern: Pattern,
        traces: List[ExecutionTrace]
    ) -> Optional[ImprovementHypothesis]:
        """Generate a hypothesis for a specific pattern."""

        # Extract pattern details
        description = pattern.description.lower()

        # Determine change type and generate hypothesis based on pattern
        if "tone" in description and "negative" in description:
            return self._generate_tone_improvement(pattern, traces)

        elif "actionability" in description or "actionable" in description:
            return self._generate_actionability_improvement(pattern, traces)

        elif "completeness" in description:
            return self._generate_completeness_improvement(pattern, traces)

        elif "relevance" in description:
            return self._generate_relevance_improvement(pattern, traces)

        elif "retry" in description:
            return self._generate_retry_reduction_improvement(pattern, traces)

        # Generic improvement for other patterns
        return self._generate_generic_improvement(pattern, traces)

    def _generate_tone_improvement(
        self,
        pattern: Pattern,
        traces: List[ExecutionTrace]
    ) -> ImprovementHypothesis:
        """Generate improvement for tone issues."""

        current_prompt = prompt_manager.base_prompts.get("negative_review", "")

        # Propose enhanced empathy
        proposed_prompt = current_prompt.replace(
            "Generate an empathetic and solution-oriented response",
            "Generate a deeply empathetic, understanding, and solution-oriented response. "
            "Show genuine care for the customer's negative experience and validate their feelings"
        )

        # Add more empathy phrases to guidelines
        proposed_prompt = proposed_prompt.replace(
            "- Show understanding and empathy",
            "- Show deep understanding and empathy\n"
            "- Validate the customer's feelings\n"
            "- Use phrases like 'We truly understand your frustration' or "
            "'This is not the experience we want for our valued customers'"
        )

        return ImprovementHypothesis(
            id=f"hyp_{uuid4().hex[:8]}",
            timestamp=datetime.now(),
            pattern=pattern.description,
            supporting_traces=pattern.affected_traces,
            change_type="prompt",
            current_value=current_prompt[:200] + "...",
            proposed_value=proposed_prompt[:200] + "...",
            expected_improvement=0.15,  # Expect 15% improvement
            confidence=0.85
        )

    def _generate_actionability_improvement(
        self,
        pattern: Pattern,
        traces: List[ExecutionTrace]
    ) -> ImprovementHypothesis:
        """Generate improvement for actionability issues."""

        current_prompt = prompt_manager.base_prompts.get("negative_review", "")

        # Add specific action step template
        action_template = """

Action Steps Template:
1. Contact Information: Provide email and phone number
2. Timeline: Set expectation for response time
3. Next Steps: Clear instructions on what customer should do
"""

        proposed_prompt = current_prompt + action_template

        return ImprovementHypothesis(
            id=f"hyp_{uuid4().hex[:8]}",
            timestamp=datetime.now(),
            pattern=pattern.description,
            supporting_traces=pattern.affected_traces,
            change_type="prompt",
            current_value=current_prompt[:200] + "...",
            proposed_value=proposed_prompt[:200] + "...",
            expected_improvement=0.20,  # Expect 20% improvement
            confidence=0.90
        )

    def _generate_completeness_improvement(
        self,
        pattern: Pattern,
        traces: List[ExecutionTrace]
    ) -> ImprovementHypothesis:
        """Generate improvement for completeness issues."""

        current_prompt = prompt_manager.base_prompts.get("negative_review", "")

        proposed_prompt = current_prompt.replace(
            "- Address each issue specifically",
            "- Address EACH AND EVERY issue mentioned specifically\n"
            "- Create a checklist: for each issue in {issues}, provide a response\n"
            "- Ensure no issue is left unaddressed"
        )

        return ImprovementHypothesis(
            id=f"hyp_{uuid4().hex[:8]}",
            timestamp=datetime.now(),
            pattern=pattern.description,
            supporting_traces=pattern.affected_traces,
            change_type="prompt",
            current_value=current_prompt[:200] + "...",
            proposed_value=proposed_prompt[:200] + "...",
            expected_improvement=0.12,
            confidence=0.80
        )

    def _generate_relevance_improvement(
        self,
        pattern: Pattern,
        traces: List[ExecutionTrace]
    ) -> ImprovementHypothesis:
        """Generate improvement for relevance issues."""

        current_prompt = prompt_manager.base_prompts.get("negative_review", "")

        proposed_prompt = current_prompt.replace(
            "Review Text: {review_text}",
            "Review Text: {review_text}\n\n"
            "IMPORTANT: Your response must directly address the specific concerns "
            "mentioned in this review. Reference specific details from the review."
        )

        return ImprovementHypothesis(
            id=f"hyp_{uuid4().hex[:8]}",
            timestamp=datetime.now(),
            pattern=pattern.description,
            supporting_traces=pattern.affected_traces,
            change_type="prompt",
            current_value=current_prompt[:200] + "...",
            proposed_value=proposed_prompt[:200] + "...",
            expected_improvement=0.10,
            confidence=0.75
        )

    def _generate_retry_reduction_improvement(
        self,
        pattern: Pattern,
        traces: List[ExecutionTrace]
    ) -> ImprovementHypothesis:
        """Generate improvement to reduce retry rate."""

        # For high retry rates, we want to improve the initial prompt quality
        current_prompt = prompt_manager.base_prompts.get("system", "")

        proposed_prompt = current_prompt + "\n\nQuality Standards:\n" \
            "- Ensure response is comprehensive and addresses all points\n" \
            "- Use appropriate tone for the sentiment\n" \
            "- Provide clear, actionable next steps\n" \
            "- Be specific and avoid generic responses"

        return ImprovementHypothesis(
            id=f"hyp_{uuid4().hex[:8]}",
            timestamp=datetime.now(),
            pattern=pattern.description,
            supporting_traces=pattern.affected_traces,
            change_type="prompt",
            current_value=current_prompt,
            proposed_value=proposed_prompt,
            expected_improvement=0.18,  # Reduce retries
            confidence=0.85
        )

    def _generate_generic_improvement(
        self,
        pattern: Pattern,
        traces: List[ExecutionTrace]
    ) -> ImprovementHypothesis:
        """Generate generic improvement for unspecified patterns."""

        current_value = "Current configuration"
        proposed_value = f"Improved configuration for: {pattern.description}"

        return ImprovementHypothesis(
            id=f"hyp_{uuid4().hex[:8]}",
            timestamp=datetime.now(),
            pattern=pattern.description,
            supporting_traces=pattern.affected_traces,
            change_type="configuration",
            current_value=current_value,
            proposed_value=proposed_value,
            expected_improvement=0.08,
            confidence=0.60
        )

    def prioritize_hypotheses(
        self,
        hypotheses: List[ImprovementHypothesis]
    ) -> List[ImprovementHypothesis]:
        """
        Prioritize hypotheses by expected impact and confidence.

        Args:
            hypotheses: List of hypotheses

        Returns:
            Sorted list (highest priority first)
        """
        def priority_score(h: ImprovementHypothesis) -> float:
            return h.expected_improvement * h.confidence

        sorted_hypotheses = sorted(
            hypotheses,
            key=priority_score,
            reverse=True
        )

        logger.debug("Hypotheses prioritized", count=len(sorted_hypotheses))

        return sorted_hypotheses
