"""Quick start script to demonstrate Loop Engineering POC."""
import asyncio
from rich.console import Console
from rich.panel import Panel

from src.orchestration.coordinator import LoopCoordinator
from src.models.review import Review
from src.utils.dataset_loader import dataset_loader

console = Console()


async def main():
    """Run a quick demonstration of the system."""

    console.print(Panel.fit(
        "[bold cyan]🔄 Loop Engineering POC - Quick Start[/bold cyan]\n"
        "Processing a sample review through all loops",
        border_style="cyan"
    ))

    # Initialize coordinator
    console.print("\n[yellow]Initializing system...[/yellow]")
    coordinator = LoopCoordinator()

    # Create a test review
    review = Review(
        id="quickstart_001",
        product_id="product_demo",
        text="The product arrived damaged and the packaging was terrible. "
             "Customer service was unhelpful when I tried to get a refund. "
             "Very disappointed with this experience.",
        rating=1.5
    )

    console.print("\n[cyan]📝 Review:[/cyan]")
    console.print(f"  Rating: {review.rating}/5.0")
    console.print(f"  Text: {review.text}\n")

    # Process through all loops
    console.print("[yellow]Processing through Loop 1 (Agent) + Loop 2 (Verification)...[/yellow]\n")

    trace = await coordinator.process_review(review, with_verification=True, with_retry=True)

    # Display results
    console.print("[bold green]✅ Processing Complete![/bold green]\n")

    console.print("[cyan]🤖 Agent Loop (Loop 1) - Analysis:[/cyan]")
    console.print(f"  • Sentiment: {trace.steps[0].output.get('sentiment', 'N/A')}")
    console.print(f"  • Duration: {trace.duration_ms}ms")
    console.print(f"  • Steps executed: {len(trace.steps)}")

    console.print(f"\n[cyan]💬 Generated Response:[/cyan]")
    console.print(f"  Strategy: {trace.response.strategy}")
    console.print(f"  Tone: {trace.response.tone}")
    console.print(f"  Version: {trace.response.version} (retries: {trace.response.version - 1})")
    console.print(f"\n  Text:\n  {trace.response.text}\n")

    if trace.verification:
        console.print(f"[cyan]✓ Verification Loop (Loop 2) - Quality Check:[/cyan]")
        console.print(f"  Overall Score: {trace.verification.overall_score:.2f}")
        console.print(f"  Passed: {'✅ Yes' if trace.verification.passed else '❌ No'}")

        console.print(f"\n  Criteria Scores:")
        for criterion, score_obj in trace.verification.criteria_scores.items():
            emoji = "✓" if score_obj.score >= 0.7 else "✗"
            console.print(f"    {emoji} {criterion:15s}: {score_obj.score:.2f} - {score_obj.rationale}")

    console.print(f"\n[cyan]📊 System Status:[/cyan]")
    status = coordinator.get_status()
    console.print(f"  Reviews processed: {status['reviews_processed']}")
    console.print(f"  Next hill climbing: {status['next_hill_climbing_at']} reviews away")

    console.print("\n[bold green]✨ Success![/bold green]")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("  • Run full demo: [cyan]python -m cli.main demo[/cyan]")
    console.print("  • Process more reviews: [cyan]python -m cli.main process --count 10[/cyan]")
    console.print("  • View metrics: [cyan]python -m cli.main metrics[/cyan]")
    console.print("  • Trigger improvement: [cyan]python -m cli.main improve[/cyan]\n")


if __name__ == "__main__":
    asyncio.run(main())
