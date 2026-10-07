"""Quality grader for evaluating code review results."""
import json
import time
from langchain_openai import ChatOpenAI
from src.config import settings
from src.models.review_models import ReviewResult


class QualityGrader:
    """Grades the quality of a code review against a rubric."""

    def __init__(self, llm: ChatOpenAI = None, rubric_prompt: str = None):
        """
        Initialize the quality grader.

        Args:
            llm: Optional LangChain LLM instance
            rubric_prompt: Optional custom rubric prompt
        """
        self.llm = llm or ChatOpenAI(
            model=settings.model_name,
            temperature=0,
            api_key=settings.openai_api_key,
        )

        self.rubric_prompt = rubric_prompt or self._load_rubric_prompt()

    def _load_rubric_prompt(self) -> str:
        """Load the quality grading rubric from prompts file."""
        prompt_file = settings.prompts_dir / "base_prompts.json"
        try:
            with open(prompt_file, 'r') as f:
                prompts = json.load(f)
                return prompts.get("quality_grading_prompt", self._default_rubric())
        except Exception:
            return self._default_rubric()

    def _default_rubric(self) -> str:
        """Default rubric if file not found."""
        return """Evaluate the code review quality on a scale of 0-100.
Consider: completeness, accuracy, actionability, depth, and coverage.
Provide a score and specific feedback."""

    def grade(self, review: ReviewResult, git_diff: str) -> tuple[float, str]:
        """
        Grade the quality of a code review.

        Args:
            review: The review result to grade
            git_diff: The original git diff that was reviewed

        Returns:
            Tuple of (quality_score, feedback)
        """
        print("[Loop 2]   Grading review quality...")
        start_time = time.time()

        try:
            # Build grading prompt
            review_summary = f"""
CODE DIFF:
{git_diff[:2000]}  # Truncate for token limits

REVIEW RESULTS:
- Files reviewed: {', '.join(review.files_reviewed) if review.files_reviewed else 'None'}
- Tools used: {', '.join(review.tools_used) if review.tools_used else 'None'}
- Issues found: {len(review.issues)}
- Summary: {review.summary}

ISSUES DETAILS:
"""
            for issue in review.issues[:10]:  # Limit to first 10
                review_summary += f"\n  - {issue.file}:{issue.line} [{issue.severity}] {issue.description[:100]}"

            if len(review.issues) > 10:
                review_summary += f"\n  ... and {len(review.issues) - 10} more issues"

            # Create grading request
            grading_request = f"""{self.rubric_prompt}

{review_summary}

Respond in JSON format:
{{
    "score": <number 0-100>,
    "feedback": "<specific feedback on what's missing or wrong>",
    "strengths": "<what the review did well>",
    "improvements": "<specific suggestions for improvement>"
}}
"""

            response = self.llm.invoke(grading_request)
            response_text = response.content

            # Parse JSON response
            try:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    score = float(result.get('score', 50))
                    feedback = result.get('feedback', 'No specific feedback provided.')
                    improvements = result.get('improvements', '')

                    full_feedback = f"{feedback}\n\nSuggested improvements: {improvements}"
                else:
                    # Fallback parsing
                    score = self._extract_score_fallback(response_text)
                    full_feedback = response_text

            except json.JSONDecodeError:
                # Fallback: extract score and use full text as feedback
                score = self._extract_score_fallback(response_text)
                full_feedback = response_text

            duration = time.time() - start_time
            print(f"[Loop 2]   Grading complete: {score}/100 ({duration:.2f}s)")

            return score, full_feedback

        except Exception as e:
            print(f"[Loop 2]   Error during grading: {str(e)}")
            # Default score of 50 if grading fails
            return 50.0, f"Grading error: {str(e)}"

    def _extract_score_fallback(self, text: str) -> float:
        """Extract score from text if JSON parsing fails."""
        import re

        # Look for patterns like "score: 75" or "75/100"
        score_patterns = [
            r'score[:\s]+(\d+)',
            r'(\d+)/100',
            r'(\d+)\s*out of 100',
        ]

        for pattern in score_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    if 0 <= score <= 100:
                        return score
                except ValueError:
                    continue

        # Default to 50 if can't extract
        return 50.0
