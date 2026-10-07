"""Prompt optimization for Loop 4."""
import json
from typing import List
from langchain_openai import ChatOpenAI

from src.config import settings
from src.models.review_models import Trace, Opportunity, Improvement


class PromptOptimizer:
    """Optimizes prompts based on trace analysis."""

    def __init__(self, llm: ChatOpenAI = None):
        """
        Initialize prompt optimizer.

        Args:
            llm: Optional LangChain LLM instance
        """
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0.3,  # Slightly higher for creative optimization
            api_key=settings.openai_api_key,
        )

    def generate_improvement(
        self,
        opportunity: Opportunity,
        current_prompt: str,
        traces: List[Trace],
    ) -> Improvement:
        """
        Generate an improved prompt based on an opportunity.

        Args:
            opportunity: The improvement opportunity
            current_prompt: Current prompt text
            traces: Evidence traces showing the issue

        Returns:
            Improvement object with new prompt
        """
        print(f"[Loop 4]   Optimizing for: {opportunity.category}")

        # Load the optimization prompt
        optimization_prompt = self._load_optimization_prompt()

        # Build context from traces
        trace_context = self._build_trace_context(traces, opportunity)

        # Create optimization request
        request = f"""{optimization_prompt}

CURRENT PROMPT:
{current_prompt}

IDENTIFIED ISSUE:
Category: {opportunity.category}
Description: {opportunity.description}
Priority: {opportunity.priority}/5
Metric Value: {opportunity.metric_value}

EVIDENCE FROM TRACES:
{trace_context}

Generate an improved prompt that addresses this issue while maintaining clarity and structure.
Return ONLY the improved prompt text, no explanations.
"""

        try:
            response = self.llm.invoke(request)
            improved_prompt = response.content.strip()

            # Create improvement record
            improvement = Improvement(
                opportunity=opportunity,
                prompt_version=f"optimized_{opportunity.category}",
                prompt_changes=f"Addressed {opportunity.category}: {opportunity.description[:100]}",
                test_score=0.0,  # Will be set after A/B testing
                baseline_score=opportunity.metric_value or 0.0,
            )

            return improvement, improved_prompt

        except Exception as e:
            print(f"[Loop 4]   Error generating improvement: {e}")
            return None, current_prompt

    def _load_optimization_prompt(self) -> str:
        """Load the prompt optimization instructions."""
        prompt_file = settings.prompts_dir / "base_prompts.json"
        try:
            with open(prompt_file, 'r') as f:
                prompts = json.load(f)
                return prompts.get("prompt_optimization_prompt", self._default_optimization_prompt())
        except Exception:
            return self._default_optimization_prompt()

    def _default_optimization_prompt(self) -> str:
        """Default optimization prompt if file not found."""
        return """You are an expert at improving AI prompts for code review.
Analyze the identified issue and improve the prompt to address it.
Maintain the original structure but add specific guidance for the problem area."""

    def _build_trace_context(self, traces: List[Trace], opportunity: Opportunity) -> str:
        """Build context string from relevant traces."""
        context_parts = []

        # Get traces mentioned in evidence
        evidence_ids = opportunity.evidence[:3]  # Limit to first 3

        for trace_id in evidence_ids:
            matching_traces = [t for t in traces if t.id.startswith(trace_id[:8])]
            if matching_traces:
                trace = matching_traces[0]
                context_parts.append(f"Trace {trace.id[:12]}:")
                context_parts.append(f"  Quality Score: {trace.verified_review.quality_score:.1f}")
                context_parts.append(f"  Retry Count: {trace.verified_review.retry_count}")
                context_parts.append(f"  Issues Found: {len(trace.verified_review.review.issues)}")
                context_parts.append(f"  Feedback: {trace.verified_review.quality_feedback[:200]}...")
                context_parts.append("")

        return "\n".join(context_parts)
