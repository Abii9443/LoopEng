"""Loop 3: Event-Driven Loop - Orchestrates reviews and triggers improvement."""
import time
from typing import Optional

from src.config import settings
from src.models.review_models import Trace
from src.loops.verification_loop import VerificationLoop
from src.storage.trace_store import TraceStore
from src.utils.display import RichDisplay
from src.tools.git_tools import get_git_diff


class EventLoop:
    """Loop 3: Orchestrates the review process and manages events."""

    def __init__(self, prompt_version: str = "base"):
        """
        Initialize the event loop.

        Args:
            prompt_version: Version of prompt to use
        """
        self.verification_loop = VerificationLoop(prompt_version=prompt_version)
        self.trace_store = TraceStore()
        self.display = RichDisplay()
        self.improvement_frequency = settings.improvement_frequency

    def handle_event(self, event_type: str, payload: dict = None) -> Optional[Trace]:
        """
        Handle a review event.

        Args:
            event_type: Type of event (manual_review, pre_commit, etc.)
            payload: Optional event payload

        Returns:
            Trace object or None if no changes detected
        """
        self.display.show_header()
        print(f"\n[Loop 3] 🎯 Event: {event_type} triggered")

        start_time = time.time()

        # Extract git diff
        print("[Loop 3] 📝 Extracting git diff...")
        git_diff_result = get_git_diff()

        if "No changes detected" in git_diff_result:
            print("[Loop 3] ℹ️  No changes detected in git working tree")
            print("\n[dim]💡 Tip: Make some code changes and try again[/dim]")
            return None

        print(f"[Loop 3] Found changes to review")

        # Run verified review (which calls Loop 2, which calls Loop 1)
        self.display.show_progress("Running code review with verification...")
        verified_review = self.verification_loop.verified_review(git_diff=git_diff_result)

        # Calculate total duration
        duration = time.time() - start_time

        # Create trace
        trace = Trace(
            event_type=event_type,
            git_diff=git_diff_result[:5000],  # Truncate for storage
            verified_review=verified_review,
            metrics={
                'quality_score': verified_review.quality_score,
                'retry_count': verified_review.retry_count,
                'passed': verified_review.passed,
                'issues_found': len(verified_review.review.issues),
                'files_reviewed': len(verified_review.review.files_reviewed),
                'tools_used': verified_review.review.tools_used,
            },
            duration=duration,
            prompt_version=self.verification_loop.agent_loop.prompt_version,
        )

        # Store trace
        print(f"\n[Loop 3] 💾 Storing trace...")
        filepath = self.trace_store.save(trace)
        trace_count = self.trace_store.count()
        print(f"[Loop 3] Trace saved: {filepath.name}")

        # Display results
        print("\n" + "=" * 60)
        self.display.show_review(verified_review)
        print()
        self.display.show_metrics(trace)
        print("=" * 60 + "\n")

        # Check if we should trigger improvement loop
        print(f"[Loop 3] 📊 Total reviews completed: {trace_count}")

        if trace_count % self.improvement_frequency == 0 and trace_count > 0:
            print(f"\n[Loop 3] 🔄 Triggering self-improvement analysis...")
            print("[Loop 3] (Run 'python -m src.main improve' to analyze and optimize)")

        print(f"\n[Loop 3] ✅ Review complete! (Total time: {duration:.2f}s)\n")

        return trace
