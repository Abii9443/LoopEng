"""Main CLI for Loop Engineering POC."""
import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import structlog

from src.orchestration.coordinator import LoopCoordinator
from src.loops.hill_climbing_loop import HillClimbingLoop
from src.models.review import Review
from src.utils.dataset_loader import dataset_loader
from src.storage.trace_store import TraceStore

console = Console()
logger = structlog.get_logger()


@click.group()
def cli():
    """Loop Engineering POC - Smart Product Review Analysis Agent."""
    pass


@cli.command()
@click.option('--count', '-c', default=10, help='Number of reviews to process')
@click.option('--with-retry', is_flag=True, default=True, help='Enable verification retry')
def process(count, with_retry):
    """Process reviews through the agent pipeline."""
    console.print(Panel.fit(
        "🤖 Processing Reviews",
        style="bold blue"
    ))

    async def _process():
        coordinator = LoopCoordinator()
        reviews = dataset_loader.create_sample_reviews(count)

        console.print(f"\n📥 Processing {len(reviews)} reviews...\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing...", total=len(reviews))

            results = []
            for review in reviews:
                trace = await coordinator.process_review(review, with_retry=with_retry)
                results.append(trace)
                progress.advance(task)

        # Display results
        _display_results(results)

    asyncio.run(_process())


@cli.command()
@click.option('--reviews', '-r', default=300, help='Number of reviews to process')
@click.option('--cycles', '-c', default=3, help='Number of improvement cycles')
def demo(reviews, cycles):
    """Run full demo with visualization of improvements."""
    from cli.demo import run_demo
    asyncio.run(run_demo(reviews, cycles))


@cli.command()
@click.option('--batch-size', '-b', default=100, help='Number of traces to analyze')
def improve(batch_size):
    """Manually trigger hill climbing improvement cycle."""
    console.print(Panel.fit(
        "🧠 Hill Climbing Analysis",
        style="bold magenta"
    ))

    async def _improve():
        coordinator = LoopCoordinator()
        hill_climbing = HillClimbingLoop()

        console.print(f"\n🔍 Analyzing last {batch_size} traces...\n")

        improvements = await hill_climbing.analyze_and_improve(coordinator)

        if improvements:
            console.print(f"\n✅ Applied {len(improvements)} improvement(s):\n")

            for imp in improvements:
                console.print(f"  • {imp.pattern}")
                console.print(f"    Expected: {imp.expected_improvement:.1%} improvement")
                console.print(f"    Confidence: {imp.confidence:.1%}\n")
        else:
            console.print("\n📊 No improvements needed - system performing well!\n")

        # Show statistics
        stats = hill_climbing.get_statistics()
        _display_hill_climbing_stats(stats)

    asyncio.run(_improve())


@cli.command()
@click.option('--window', '-w', default='1h', help='Time window (e.g., 1h, 24h, 7d)')
def metrics(window):
    """Display metrics dashboard."""
    console.print(Panel.fit(
        "📊 Metrics Dashboard",
        style="bold green"
    ))

    coordinator = LoopCoordinator()
    metrics_data = coordinator.get_metrics()

    # System metrics
    sys_metrics = metrics_data['system_metrics']

    table = Table(title="\n📈 System Performance", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Reviews Processed", str(sys_metrics['total_reviews_processed']))
    table.add_row("Pass Rate", f"{sys_metrics['verification_pass_rate']:.1%}")
    table.add_row("Avg Score", f"{sys_metrics['avg_verification_score']:.2f}")
    table.add_row("Avg Response Time", f"{sys_metrics['avg_response_time_ms']:.0f}ms")

    console.print(table)

    # Criteria breakdown
    if sys_metrics.get('criteria_breakdown'):
        table2 = Table(title="\n📋 Criteria Scores", show_header=True)
        table2.add_column("Criterion", style="cyan")
        table2.add_column("Score", style="yellow")

        for criterion, score in sys_metrics['criteria_breakdown'].items():
            table2.add_row(criterion.capitalize(), f"{score:.2f}")

        console.print(table2)

    # Failure patterns
    failures = metrics_data.get('failure_patterns', {})
    if failures.get('common_issues'):
        console.print("\n⚠️  Common Issues:\n")
        for issue in failures['common_issues'][:3]:
            console.print(
                f"  • {issue['criterion']}: "
                f"{issue['count']} occurrences (avg score: {issue['avg_score']:.2f})"
            )

    console.print()


@cli.command()
@click.argument('trace_id')
def trace(trace_id):
    """Show details of a specific trace."""
    trace_store = TraceStore()
    trace_obj = trace_store.get(trace_id)

    if not trace_obj:
        console.print(f"❌ Trace {trace_id} not found", style="bold red")
        return

    console.print(Panel.fit(
        f"📋 Trace Details: {trace_id}",
        style="bold cyan"
    ))

    console.print(f"\n⏱️  Duration: {trace_obj.duration_ms}ms")
    console.print(f"✅ Success: {trace_obj.success}")
    console.print(f"🔧 Prompt Version: {trace_obj.prompt_version}")

    # Steps
    console.print(f"\n📝 Steps ({len(trace_obj.steps)}):\n")
    for step in trace_obj.steps:
        console.print(f"  {step.step_id}: {step.action} ({step.duration_ms}ms)")

    # Response
    console.print(f"\n💬 Response:\n")
    console.print(f"  {trace_obj.response.text[:200]}...")

    # Verification
    if trace_obj.verification:
        console.print(f"\n📊 Verification:\n")
        console.print(f"  Overall Score: {trace_obj.verification.overall_score:.2f}")
        console.print(f"  Passed: {trace_obj.verification.passed}")

        for criterion, score_obj in trace_obj.verification.criteria_scores.items():
            console.print(f"  • {criterion}: {score_obj.score:.2f}")

    console.print()


@cli.command()
def init():
    """Initialize the system (create directories, etc.)."""
    from pathlib import Path

    console.print("🔧 Initializing Loop Engineering POC...\n")

    # Create directories
    dirs = [
        "data/traces",
        "data/embeddings",
        "data/reviews"
    ]

    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        console.print(f"✓ Created {dir_path}")

    console.print("\n✅ Initialization complete!")
    console.print("\nNext steps:")
    console.print("  1. Run demo: python -m cli.main demo")
    console.print("  2. Or process reviews: python -m cli.main process --count 10")
    console.print()


@cli.command()
def stats():
    """Show overall statistics."""
    trace_store = TraceStore()
    stats = trace_store.get_stats()

    console.print(Panel.fit(
        "📊 Storage Statistics",
        style="bold blue"
    ))

    table = Table(show_header=True)
    table.add_column("Table", style="cyan")
    table.add_column("Count", style="green")

    for table_name, count in stats.items():
        table.add_row(table_name.replace("total_", "").capitalize(), str(count))

    console.print(table)
    console.print()


def _display_results(traces):
    """Display processing results."""
    successful = [t for t in traces if t.success]
    verified = [t for t in traces if t.verification and t.verification.passed]

    console.print(f"\n✅ Results:\n")
    console.print(f"  Processed: {len(traces)}")
    console.print(f"  Successful: {len(successful)}")
    console.print(f"  Verified Passed: {len(verified)}")

    if verified:
        avg_score = sum(t.verification.overall_score for t in verified) / len(verified)
        console.print(f"  Avg Score: {avg_score:.2f}")

        # Retry statistics
        retries = [t.response.version - 1 for t in traces]
        avg_retries = sum(retries) / len(retries)
        console.print(f"  Avg Retries: {avg_retries:.2f}")

    console.print()


def _display_hill_climbing_stats(stats):
    """Display hill climbing statistics."""
    table = Table(title="\n🎯 Hill Climbing Statistics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Total Hypotheses", str(stats['total_hypotheses']))
    table.add_row("Applied", str(stats['applied']))
    table.add_row("Rejected", str(stats['rejected']))
    table.add_row("Pending", str(stats['pending']))
    table.add_row("Avg Improvement", f"{stats['avg_improvement']:.1%}")
    table.add_row("Prompt Version", stats['current_prompt_version'])

    console.print(table)
    console.print()


if __name__ == '__main__':
    cli()
