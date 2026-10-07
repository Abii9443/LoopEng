"""Loop 4: Hill Climbing Loop - Self-improvement through analysis."""
import json
from pathlib import Path
from typing import List

from src.config import settings
from src.models.review_models import Improvement
from src.storage.trace_store import TraceStore
from src.agents.prompt_optimizer import PromptOptimizer
from src.utils.metrics import MetricsAnalyzer


class HillClimbingLoop:
    """Loop 4: Analyzes past reviews and improves prompts/graders."""

    def __init__(self):
        """Initialize the hill climbing loop."""
        self.trace_store = TraceStore()
        self.optimizer = PromptOptimizer()
        self.metrics_analyzer = MetricsAnalyzer()

    def analyze_and_improve(self, num_traces: int = 10) -> List[Improvement]:
        """
        Analyze past reviews and generate improvements.

        Args:
            num_traces: Number of recent traces to analyze

        Returns:
            List of Improvement objects
        """
        print(f"\n[Loop 4] 🧠 Hill Climbing Loop - Analyzing last {num_traces} reviews")
        print("=" * 60)

        # Load recent traces
        traces = self.trace_store.get_recent(num_traces)

        if not traces:
            print("[Loop 4] ⚠️  No traces found. Run some reviews first!")
            return []

        print(f"[Loop 4] 📊 Loaded {len(traces)} traces")

        # Calculate aggregate metrics
        metrics = self.metrics_analyzer.aggregate(traces)

        print(f"\n[Loop 4] 📈 Current Metrics:")
        print(f"  • Avg Quality Score: {metrics.avg_quality_score:.1f}/100")
        print(f"  • Avg Retry Count: {metrics.avg_retry_count:.2f}")
        print(f"  • Avg Issues Found: {metrics.avg_issues_found:.1f}")
        print(f"  • Avg Duration: {metrics.avg_duration:.2f}s")

        if metrics.top_issue_types:
            print(f"\n[Loop 4] 🔍 Top Issue Categories:")
            for category, count in metrics.top_issue_types[:5]:
                print(f"  • {category}: {count}")

        # Find improvement opportunities
        print(f"\n[Loop 4] 🎯 Identifying improvement opportunities...")
        opportunities = self.metrics_analyzer.find_opportunities(traces, metrics)

        if not opportunities:
            print("[Loop 4] ✅ No significant improvement opportunities found!")
            print("[Loop 4] System is performing well.")
            return []

        print(f"[Loop 4] Found {len(opportunities)} opportunity(ies):")
        for opp in opportunities:
            print(f"  • [{opp.priority}/5] {opp.category}: {opp.description[:80]}...")

        # Generate improvements for top opportunities
        improvements = []
        top_opportunities = opportunities[:2]  # Focus on top 2

        print(f"\n[Loop 4] 🔧 Generating improvements...")

        for opp in top_opportunities:
            # Load current prompt
            current_prompt = self._load_current_prompt()

            # Generate improvement
            improvement, improved_prompt = self.optimizer.generate_improvement(
                opportunity=opp,
                current_prompt=current_prompt,
                traces=traces,
            )

            if improvement:
                # For POC, we'll simulate A/B testing with a simple heuristic
                improvement.test_score = self._simulate_ab_test(improvement, metrics)

                improvements.append((improvement, improved_prompt))

                print(f"[Loop 4]   Generated improvement for {opp.category}")
                print(f"[Loop 4]   Simulated test score: {improvement.test_score:.1f} vs baseline {improvement.baseline_score:.1f}")

        # Determine if we should promote
        if improvements:
            best_improvement, best_prompt = max(improvements, key=lambda x: x[0].test_score)

            print(f"\n[Loop 4] 🏆 Best Improvement:")
            print(f"  Category: {best_improvement.opportunity.category}")
            print(f"  Test Score: {best_improvement.test_score:.1f}")
            print(f"  Baseline: {best_improvement.baseline_score:.1f}")

            # Promote if better (or if score is significantly low)
            should_promote = (
                best_improvement.test_score > best_improvement.baseline_score or
                metrics.avg_quality_score < 70
            )

            if should_promote:
                print(f"\n[Loop 4] 🚀 Promoting new prompt!")
                self._promote_prompt(best_prompt, best_improvement)
                best_improvement.promoted = True

                # Save improvement record
                self._save_improvement(best_improvement)

                print(f"[Loop 4] 💾 Improvement saved to {settings.improvements_dir}")
                print(f"[Loop 4] ✅ New prompt will be used in future reviews")
            else:
                print(f"\n[Loop 4] ⏸️  Keeping current prompt (test score not better)")

        else:
            print(f"\n[Loop 4] ⚠️  Could not generate improvements")

        print("=" * 60)
        print(f"[Loop 4] Analysis complete!\n")

        return [imp for imp, _ in improvements]

    def _load_current_prompt(self) -> str:
        """Load the current active prompt."""
        # Check for optimized prompt first
        optimized_file = settings.prompts_dir / "optimized_prompts.json"
        base_file = settings.prompts_dir / "base_prompts.json"

        if optimized_file.exists():
            try:
                with open(optimized_file, 'r') as f:
                    prompts = json.load(f)
                    return prompts.get("code_review_prompt", self._load_base_prompt())
            except Exception:
                pass

        return self._load_base_prompt()

    def _load_base_prompt(self) -> str:
        """Load base prompt."""
        base_file = settings.prompts_dir / "base_prompts.json"
        with open(base_file, 'r') as f:
            prompts = json.load(f)
            return prompts["code_review_prompt"]

    def _simulate_ab_test(self, improvement: Improvement, metrics) -> float:
        """
        Simulate A/B test score.
        In production, this would run actual reviews with the new prompt.
        """
        # Simple heuristic: give a boost based on the issue being addressed
        baseline = metrics.avg_quality_score

        # Estimate improvement based on priority
        priority_boost = improvement.opportunity.priority * 2

        # Add some variance based on category
        category_boost = {
            'review_depth': 8,
            'first_pass_accuracy': 6,
            'detection_sensitivity': 5,
            'tool_utilization': 3,
        }.get(improvement.opportunity.category, 4)

        estimated_score = min(100, baseline + priority_boost + category_boost)

        return estimated_score

    def _promote_prompt(self, prompt_text: str, improvement: Improvement):
        """Promote a new prompt to production."""
        optimized_file = settings.prompts_dir / "optimized_prompts.json"

        # Create or update optimized prompts file
        optimized_prompts = {
            "version": improvement.prompt_version,
            "code_review_prompt": prompt_text,
            "promoted_at": improvement.timestamp.isoformat(),
            "improvement_id": improvement.id,
            "changes": improvement.prompt_changes,
        }

        with open(optimized_file, 'w') as f:
            json.dump(optimized_prompts, f, indent=2)

    def _save_improvement(self, improvement: Improvement):
        """Save improvement record."""
        filename = f"improvement_{improvement.timestamp.strftime('%Y%m%d_%H%M%S')}_{improvement.id[:8]}.json"
        filepath = settings.improvements_dir / filename

        with open(filepath, 'w') as f:
            improvement_dict = improvement.model_dump()
            improvement_dict['timestamp'] = improvement.timestamp.isoformat()
            json.dump(improvement_dict, f, indent=2, default=str)
