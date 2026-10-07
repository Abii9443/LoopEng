"""Pydantic models for code review data structures."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class Issue(BaseModel):
    """Represents a single code issue found during review."""

    file: str = Field(description="Path to the file containing the issue")
    line: int = Field(description="Line number where the issue occurs")
    severity: str = Field(description="Severity level: critical, major, minor, info")
    category: str = Field(description="Category: bug, style, security, performance, complexity")
    description: str = Field(description="Description of the issue")
    suggestion: str = Field(description="Suggested fix or improvement")
    tool_source: Optional[str] = Field(default=None, description="Which tool found this issue")


class ReviewResult(BaseModel):
    """Result of a code review from Loop 1 (Agent Loop)."""

    issues: List[Issue] = Field(default_factory=list, description="List of issues found")
    summary: str = Field(description="Overall summary of the review")
    files_reviewed: List[str] = Field(default_factory=list, description="List of files reviewed")
    tools_used: List[str] = Field(default_factory=list, description="List of tools called by agent")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the review was performed")
    token_count: Optional[int] = Field(default=None, description="Total tokens used")
    duration: Optional[float] = Field(default=None, description="Time taken in seconds")


class VerifiedReview(BaseModel):
    """Result of a verified review from Loop 2 (Verification Loop)."""

    review: ReviewResult = Field(description="The underlying review result")
    quality_score: float = Field(description="Quality score from 0-100")
    quality_feedback: str = Field(description="Feedback on review quality")
    retry_count: int = Field(default=0, description="Number of retries needed")
    passed: bool = Field(description="Whether the review passed quality threshold")
    verification_time: float = Field(description="Time taken for verification in seconds")


class Trace(BaseModel):
    """Complete trace of a review session for analysis and improvement."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique trace ID")
    event_type: str = Field(description="Type of event that triggered review")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the review occurred")
    git_diff: str = Field(description="The git diff that was reviewed")
    verified_review: VerifiedReview = Field(description="The verified review result")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Additional metrics")
    duration: float = Field(description="Total duration of the review in seconds")
    prompt_version: str = Field(default="base", description="Version of prompt used")


class TraceMetrics(BaseModel):
    """Aggregate metrics calculated from multiple traces."""

    num_traces: int = Field(description="Number of traces analyzed")
    avg_quality_score: float = Field(description="Average quality score")
    avg_retry_count: float = Field(description="Average number of retries")
    avg_issues_found: float = Field(description="Average number of issues per review")
    top_issue_types: List[tuple] = Field(default_factory=list, description="Most common issue types with counts")
    avg_duration: float = Field(description="Average review duration")
    false_positive_rate: Optional[float] = Field(default=None, description="Estimated false positive rate")


class Opportunity(BaseModel):
    """Improvement opportunity identified by Loop 4."""

    category: str = Field(description="Category of improvement needed")
    description: str = Field(description="Description of the opportunity")
    evidence: List[str] = Field(default_factory=list, description="Trace IDs showing this pattern")
    priority: int = Field(default=1, description="Priority level 1-5")
    metric_value: Optional[float] = Field(default=None, description="Associated metric value")


class Improvement(BaseModel):
    """Record of an improvement made by Loop 4."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique improvement ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="When improvement was made")
    opportunity: Opportunity = Field(description="The opportunity this addresses")
    prompt_version: str = Field(description="New prompt version identifier")
    prompt_changes: str = Field(description="Description of changes made to prompt")
    test_score: float = Field(description="Score achieved with this improvement")
    baseline_score: float = Field(description="Baseline score before improvement")
    promoted: bool = Field(default=False, description="Whether this improvement was promoted to production")
