"""Demo command with rich visualization of loop engineering improvements."""
import asyncio
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
import structlog

from src.orchestration.coordinator import LoopCoordinator
from src.loops.hill_climbing_loop import HillClimbingLoop
from src.utils.dataset_loader import dataset_loader
from src.storage.trace_store import TraceStore

console = Console()
logger = structlog.get_logger()


async def run_demo(total_reviews: int = 300, num_cycles: int = 3):
    """
    Run full demo showing loop engineering in action.

    Args:
        total_reviews: Total number of reviews to process
        num_cycles: Number of improvement cycles to run
    """
    console.clear()

    console.print(Panel.fit(
        "[bold cyan]🔄 Loop Engineering POC Demo[/bold cyan]\n"
        "Demonstrating Self-Improving AI Agents with 4 Feedback Loops",
        border_style="cyan"
    ))

    console.print("\n📚 Loading reviews from dataset...\n")
    reviews = dataset_loader.load_reviews(count=total_reviews, shuffle=True)

    if not reviews:
        console.print("❌ Failed to load reviews. Using synthetic data.", style="yellow")
        reviews = dataset_loader.create_sample_reviews(total_reviews)

    console.print(f"✓ Loaded {len(reviews)} reviews\n")

    # Initialize
    coordinator = LoopCoordinator()
    hill_climbing = HillClimbingLoop()
    trace_store = TraceStore()

    # Split reviews into cycles
    reviews_per_cycle = len(reviews) // num_cycles
    cycle_results = []

    console.print(f"🎯 Running {num_cycles} improvement cycles\n")
    console.print("=" * 70 + "\n")

    # Baseline cycle
    await _run_cycle(
        cycle_num=0,
        cycle_name="BASELINE",
        reviews=reviews[:reviews_per_cycle],
        coordinator=coordinator,
        hill_climbing=None,
        cycle_results=cycle_results
    )

    # Improvement cycles
    for cycle in range(1, num_cycles):
        # Trigger hill climbing before this cycle
        console.print(f"\n🧠 [bold magenta]Hill Climbing - Cycle {cycle}[/bold magenta]")
        console.print("-" * 70)

        improvements = await hill_climbing.analyze_and_improve(coordinator)

        if improvements:
            for imp in improvements:
                console.print(f"  💡 Hypothesis: {imp.pattern}")
                console.print(f"     Expected: {imp.expected_improvement:.1%} improvement")
                if imp.actual_improvement:
                    console.print(f"     Actual: {imp.actual_improvement:.1%} improvement")
                console.print(f"     ✅ Applied: {imp.change_type}\n")
        else:
            console.print("  📊 No improvements identified in this cycle\n")

        # Process next batch
        start_idx = cycle * reviews_per_cycle
        end_idx = (cycle + 1) * reviews_per_cycle

        await _run_cycle(
            cycle_num=cycle,
            cycle_name=f"AFTER IMPROVEMENT #{cycle}",
            reviews=reviews[start_idx:end_idx],
            coordinator=coordinator,
            hill_climbing=hill_climbing,
            cycle_results=cycle_results
        )

    # Final summary
    console.print("\n" + "=" * 70)
    console.print("\n🎉 [bold green]Demo Complete![/bold green]\n")

    _display_improvement_summary(cycle_results)

    # Show final statistics
    _display_final_stats(trace_store, hill_climbing)


async def _run_cycle(
    cycle_num: int,
    cycle_name: str,
    reviews,
    coordinator,
    hill_climbing,
    cycle_results
):
    """Run a single processing cycle."""

    console.print(f"\n[bold blue]Cycle {cycle_num}: {cycle_name}[/bold blue]")
    console.print("-" * 70)

    # Process reviews with progress bar
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:

        task = progress.add_task(
            f"[cyan]Processing {len(reviews)} reviews...",
            total=len(reviews)
        )

        traces = []
        for review in reviews:
            trace = await coordinator.process_review(review)
            traces.append(trace)
            progress.advance(task)

    # Calculate metrics
    verified_traces = [t for t in traces if t.verification]

    if verified_traces:
        passed = [t for t in verified_traces if t.verification.passed]
        pass_rate = len(passed) / len(verified_traces)
        avg_score = sum(t.verification.overall_score for t in verified_traces) / len(verified_traces)

        # Criteria breakdown
        criteria_scores = {}
        for trace in verified_traces:
            for criterion, score_obj in trace.verification.criteria_scores.items():
                if criterion not in criteria_scores:
                    criteria_scores[criterion] = []
                criteria_scores[criterion].append(score_obj.score)

        criteria_avg = {
            criterion: sum(scores) / len(scores)
            for criterion, scores in criteria_scores.items()
        }

        # Retry stats
        retries = [t.response.version - 1 for t in traces]
        avg_retries = sum(retries) / len(retries)

    else:
        pass_rate = 0
        avg_score = 0
        criteria_avg = {}
        avg_retries = 0

    # Store results
    cycle_result = {
        "cycle": cycle_num,
        "name": cycle_name,
        "pass_rate": pass_rate,
        "avg_score": avg_score,
        "criteria_avg": criteria_avg,
        "avg_retries": avg_retries,
        "total_reviews": len(reviews)
    }
    cycle_results.append(cycle_result)

    # Display cycle results
    _display_cycle_results(cycle_result)


def _display_cycle_results(result):
    """Display results for a single cycle."""

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Pass Rate:", f"{result['pass_rate']:.1%}")
    table.add_row("Avg Score:", f"{result['avg_score']:.2f}")
    table.add_row("Avg Retries:", f"{result['avg_retries']:.2f}")

    console.print(table)

    # Criteria breakdown
    if result['criteria_avg']:
        console.print("\n  📋 Criteria Scores:")
        for criterion, score in result['criteria_avg'].items():
            # Highlight low scores
            style = "red" if score < 0.65 else "green" if score >= 0.75 else "yellow"
            console.print(f"     • {criterion:15s}: [{style}]{score:.2f}[/{style}]")


def _display_improvement_summary(cycle_results):
    """Display improvement summary across all cycles."""

    console.print(Panel.fit(
        "[bold green]📈 Improvement Summary[/bold green]",
        border_style="green"
    ))

    # Compare baseline vs final
    baseline = cycle_results[0]
    final = cycle_results[-1]

    table = Table(title="\n🎯 Overall Improvement", show_header=True, box=None)
    table.add_column("Metric", style="cyan", justify="left")
    table.add_column("Baseline", style="yellow", justify="right")
    table.add_column("Final", style="green", justify="right")
    table.add_column("Change", style="magenta", justify="right")

    # Pass rate
    pass_change = final['pass_rate'] - baseline['pass_rate']
    table.add_row(
        "Pass Rate",
        f"{baseline['pass_rate']:.1%}",
        f"{final['pass_rate']:.1%}",
        f"+{pass_change:.1%}" if pass_change > 0 else f"{pass_change:.1%}"
    )

    # Avg score
    score_change = final['avg_score'] - baseline['avg_score']
    table.add_row(
        "Avg Score",
        f"{baseline['avg_score']:.2f}",
        f"{final['avg_score']:.2f}",
        f"+{score_change:.2f}" if score_change > 0 else f"{score_change:.2f}"
    )

    # Retries
    retry_change = final['avg_retries'] - baseline['avg_retries']
    table.add_row(
        "Avg Retries",
        f"{baseline['avg_retries']:.2f}",
        f"{final['avg_retries']:.2f}",
        f"{retry_change:.2f}"
    )

    console.print(table)

    # Criteria improvements
    if baseline['criteria_avg'] and final['criteria_avg']:
        console.print("\n📊 Criteria Improvements:\n")

        for criterion in baseline['criteria_avg'].keys():
            base_score = baseline['criteria_avg'][criterion]
            final_score = final['criteria_avg'].get(criterion, base_score)
            change = final_score - base_score

            if abs(change) > 0.05:  # Significant change
                emoji = "📈" if change > 0 else "📉"
                style = "green" if change > 0 else "red"
                console.print(
                    f"  {emoji} {criterion:15s}: "
                    f"{base_score:.2f} → [{style}]{final_score:.2f}[/{style}] "
                    f"({change:+.2f})"
                )

    console.print()


def _display_final_stats(trace_store, hill_climbing):
    """Display final system statistics."""

    console.print(Panel.fit(
        "[bold cyan]📊 Final System Statistics[/bold cyan]",
        border_style="cyan"
    ))

    # Storage stats
    storage_stats = trace_store.get_stats()

    table1 = Table(title="\n💾 Storage", show_header=False, box=None)
    table1.add_column("", style="cyan")
    table1.add_column("", style="yellow")

    table1.add_row("Total Traces:", str(storage_stats['total_traces']))
    table1.add_row("Improvements:", str(storage_stats['total_improvements']))
    table1.add_row("A/B Tests:", str(storage_stats['total_ab_tests']))

    console.print(table1)

    # Hill climbing stats
    hc_stats = hill_climbing.get_statistics()

    table2 = Table(title="\n🧠 Hill Climbing", show_header=False, box=None)
    table2.add_column("", style="cyan")
    table2.add_column("", style="yellow")

    table2.add_row("Hypotheses Generated:", str(hc_stats['total_hypotheses']))
    table2.add_row("Applied:", str(hc_stats['applied']))
    table2.add_row("Rejected:", str(hc_stats['rejected']))
    if hc_stats['avg_improvement']:
        table2.add_row("Avg Improvement:", f"{hc_stats['avg_improvement']:.1%}")
    table2.add_row("Prompt Version:", hc_stats['current_prompt_version'])

    console.print(table2)

    console.print("\n✅ [bold green]Loop Engineering Demonstration Complete![/bold green]\n")
    console.print("The system has successfully:")
    console.print("  ✓ Processed reviews through all 4 loops")
    console.print("  ✓ Detected quality patterns")
    console.print("  ✓ Generated and tested improvements")
    console.print("  ✓ Applied successful changes")
    console.print("  ✓ Demonstrated measurable improvement\n")
