"""Loop 1: Agent Loop - Main review processing pipeline."""
import time
from datetime import datetime
from typing import Optional
from uuid import uuid4
import structlog

from src.config import settings, prompt_manager
from src.models.review import Review
from src.models.trace import ExecutionTrace, AgentStep, ToolCall
from src.tools import SentimentAnalyzer, IssueExtractor, UrgencyClassifier, knowledge_base
from src.agents.response_generator import ResponseGenerator
from src.storage.trace_store import TraceStore

logger = structlog.get_logger()


class AgentLoop:
    """
    Loop 1: Agent Loop.

    Processes reviews through the full pipeline:
    1. Sentiment analysis
    2. Issue extraction
    3. Urgency classification
    4. Knowledge base query
    5. Response generation
    6. Trace logging
    """

    def __init__(self):
        """Initialize agent loop with all tools."""
        self.sentiment_analyzer = SentimentAnalyzer()
        self.issue_extractor = IssueExtractor()
        self.urgency_classifier = UrgencyClassifier()
        self.response_generator = ResponseGenerator()
        self.trace_store = TraceStore()

        logger.info("Agent Loop initialized")

    async def process_review(
        self,
        review: Review,
        feedback: Optional[str] = None,
        original_response: Optional[str] = None,
        version: int = 1
    ) -> ExecutionTrace:
        """
        Process a review through the agent pipeline.

        Args:
            review: The review to process
            feedback: Feedback for retry (optional)
            original_response: Original response for retry (optional)
            version: Response version number (for retries)

        Returns:
            ExecutionTrace with complete execution record
        """
        start_time = time.time()
        trace_id = str(uuid4())

        logger.info(
            "Starting review processing",
            trace_id=trace_id,
            review_id=review.id,
            version=version
        )

        # Initialize trace
        trace = ExecutionTrace(
            id=trace_id,
            review_id=review.id,
            timestamp=datetime.now(),
            steps=[],
            tools_used=[],
            duration_ms=0,
            response=None,  # Will be set later
            verification=None,
            prompt_version=prompt_manager.get_version(),
            model_config={"generation_model": settings.generation_model},
            success=False
        )

        try:
            # Step 1: Sentiment Analysis
            step1_start = time.time()
            sentiment_result = self.sentiment_analyzer.analyze(review.text)
            review.sentiment = sentiment_result
            sentiment_label = sentiment_result.label

            trace.steps.append(AgentStep(
                step_id=f"{trace_id}_step1",
                action="sentiment_analysis",
                input={"text": review.text},
                output={
                    "sentiment": sentiment_label,
                    "score": sentiment_result.score,
                    "confidence": sentiment_result.confidence
                },
                duration_ms=int((time.time() - step1_start) * 1000),
                tool_calls=[ToolCall(
                    tool_name="SentimentAnalyzer",
                    arguments={"text": review.text},
                    result=sentiment_result.model_dump(),
                    duration_ms=int((time.time() - step1_start) * 1000)
                )]
            ))
            trace.tools_used.append("SentimentAnalyzer")

            logger.debug(
                "Sentiment analysis complete",
                trace_id=trace_id,
                sentiment=sentiment_label
            )

            # Step 2: Issue Extraction
            step2_start = time.time()
            issues = self.issue_extractor.extract(review.text, sentiment_label)
            review.issues = issues

            trace.steps.append(AgentStep(
                step_id=f"{trace_id}_step2",
                action="issue_extraction",
                input={"text": review.text, "sentiment": sentiment_label},
                output={
                    "num_issues": len(issues),
                    "issues": [issue.model_dump() for issue in issues]
                },
                duration_ms=int((time.time() - step2_start) * 1000),
                tool_calls=[ToolCall(
                    tool_name="IssueExtractor",
                    arguments={"text": review.text, "sentiment": sentiment_label},
                    result=[issue.model_dump() for issue in issues],
                    duration_ms=int((time.time() - step2_start) * 1000)
                )]
            ))
            trace.tools_used.append("IssueExtractor")

            logger.debug(
                "Issue extraction complete",
                trace_id=trace_id,
                num_issues=len(issues)
            )

            # Step 3: Urgency Classification
            step3_start = time.time()
            urgency = self.urgency_classifier.classify(review, sentiment_label, issues)
            review.urgency = urgency

            trace.steps.append(AgentStep(
                step_id=f"{trace_id}_step3",
                action="urgency_classification",
                input={
                    "rating": review.rating,
                    "sentiment": sentiment_label,
                    "num_issues": len(issues)
                },
                output={"urgency": urgency.value},
                duration_ms=int((time.time() - step3_start) * 1000),
                tool_calls=[]  # Rule-based, no external tool
            ))

            logger.debug(
                "Urgency classification complete",
                trace_id=trace_id,
                urgency=urgency.value
            )

            # Step 4: Knowledge Base Query
            step4_start = time.time()
            similar_cases = knowledge_base.search(
                query_text=review.text,
                top_k=3,
                sentiment_filter=sentiment_label,
                min_score=0.7
            )

            trace.steps.append(AgentStep(
                step_id=f"{trace_id}_step4",
                action="knowledge_base_search",
                input={"query": review.text, "sentiment": sentiment_label},
                output={
                    "num_results": len(similar_cases),
                    "results": [{"distance": r["distance"]} for r in similar_cases]
                },
                duration_ms=int((time.time() - step4_start) * 1000),
                tool_calls=[ToolCall(
                    tool_name="KnowledgeBase",
                    arguments={"query": review.text, "top_k": 3},
                    result={"num_results": len(similar_cases)},
                    duration_ms=int((time.time() - step4_start) * 1000)
                )]
            ))
            trace.tools_used.append("KnowledgeBase")

            logger.debug(
                "Knowledge base search complete",
                trace_id=trace_id,
                num_results=len(similar_cases)
            )

            # Step 5: Response Generation
            step5_start = time.time()
            response = self.response_generator.generate(
                review=review,
                sentiment=sentiment_label,
                issues=issues,
                context=similar_cases,
                feedback=feedback,
                original_response=original_response,
                version=version
            )

            trace.steps.append(AgentStep(
                step_id=f"{trace_id}_step5",
                action="response_generation",
                input={
                    "sentiment": sentiment_label,
                    "num_issues": len(issues),
                    "context_size": len(similar_cases),
                    "version": version
                },
                output={
                    "response_id": response.id,
                    "strategy": response.strategy,
                    "length": len(response.text)
                },
                duration_ms=int((time.time() - step5_start) * 1000),
                tool_calls=[ToolCall(
                    tool_name="ResponseGenerator",
                    arguments={"review_id": review.id, "sentiment": sentiment_label},
                    result={"response_id": response.id},
                    duration_ms=int((time.time() - step5_start) * 1000)
                )]
            ))
            trace.tools_used.append("ResponseGenerator")

            logger.info(
                "Response generation complete",
                trace_id=trace_id,
                response_id=response.id,
                strategy=response.strategy
            )

            # Finalize trace
            trace.response = response
            trace.duration_ms = int((time.time() - start_time) * 1000)
            trace.success = True

            # Step 6: Save trace
            self.trace_store.save(trace)

            logger.info(
                "Review processing complete",
                trace_id=trace_id,
                review_id=review.id,
                duration_ms=trace.duration_ms,
                success=True
            )

            return trace

        except Exception as e:
            logger.error(
                "Review processing failed",
                trace_id=trace_id,
                review_id=review.id,
                error=str(e)
            )

            # Mark trace as failed
            trace.duration_ms = int((time.time() - start_time) * 1000)
            trace.success = False

            # Create fallback response if not already set
            if not trace.response:
                trace.response = self.response_generator._create_fallback_response(
                    review,
                    sentiment_label if review.sentiment else "neutral",
                    version
                )

            # Still save the trace for learning
            try:
                self.trace_store.save(trace)
            except:
                pass  # Don't fail on trace save failure

            return trace

    def get_stats(self) -> dict:
        """Get agent loop statistics."""
        return self.trace_store.get_stats()
