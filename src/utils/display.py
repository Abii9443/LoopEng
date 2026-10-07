"""Rich console display utilities."""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.models.review_models import VerifiedReview, Trace


console = Console()


class RichDisplay:
    """Handles rich formatted console output."""

    def __init__(self):
        self.console = console

    def show_header(self):
        """Display application header."""
        header = Panel(
            "[bold cyan]🔄 Automated Code Review Assistant - Loop Engineering POC[/bold cyan]",
            border_style="cyan",
        )
        self.console.print(header)

    def show_review(self, verified_review: VerifiedReview):
        """
        Display review results in a formatted way.

        Args:
            verified_review: The verified review to display
        """
        review = verified_review.review

        # Create issues table
        if review.issues:
            table = Table(title="📋 Review Results", show_header=True, header_style="bold magenta")
            table.add_column("File", style="cyan", no_wrap=True)
            table.add_column("Line", justify="right", style="yellow")
            table.add_column("Severity", style="red")
            table.add_column("Category", style="blue")
            table.add_column("Description", style="white")

            # Group by severity
            critical_issues = [i for i in review.issues if i.severity == 'critical']
            major_issues = [i for i in review.issues if i.severity == 'major']
            minor_issues = [i for i in review.issues if i.severity == 'minor']
            info_issues = [i for i in review.issues if i.severity == 'info']

            # Add critical first
            for issue in critical_issues[:5]:
                self._add_issue_row(table, issue, "🔴")

            for issue in major_issues[:5]:
                self._add_issue_row(table, issue, "🟠")

            for issue in minor_issues[:3]:
                self._add_issue_row(table, issue, "🟡")

            for issue in info_issues[:2]:
                self._add_issue_row(table, issue, "ℹ️")

            self.console.print(table)

            # Show counts
            total = len(review.issues)
            shown = min(15, total)
            if total > shown:
                self.console.print(f"\n[dim]... and {total - shown} more issues[/dim]\n")
        else:
            self.console.print("[green]✅ No issues found![/green]\n")

        # Summary
        self.console.print(f"[bold]Summary:[/bold] {review.summary}\n")

    def _add_issue_row(self, table: Table, issue, emoji: str):
        """Add an issue row to the table."""
        severity_color = {
            'critical': 'bold red',
            'major': 'bold yellow',
            'minor': 'yellow',
            'info': 'blue',
        }.get(issue.severity, 'white')

        table.add_row(
            issue.file,
            str(issue.line),
            f"{emoji} {issue.severity}",
            issue.category,
            issue.description[:80] + "..." if len(issue.description) > 80 else issue.description,
        )

    def show_metrics(self, trace: Trace):
        """
        Display metrics from a trace.

        Args:
            trace: Trace object with metrics
        """
        verified_review = trace.verified_review

        metrics_table = Table(title="📈 Metrics", show_header=False, border_style="blue")
        metrics_table.add_column("Metric", style="cyan bold")
        metrics_table.add_column("Value", style="green")

        # Quality score with color
        score = verified_review.quality_score
        score_color = "red" if score < 50 else "yellow" if score < 70 else "green"
        score_status = "✅ PASSED" if verified_review.passed else "⚠️  BELOW THRESHOLD"

        metrics_table.add_row("Quality Score", f"[{score_color}]{score:.1f}/100[/{score_color}] {score_status}")
        metrics_table.add_row("Retry Count", str(verified_review.retry_count))

        review = verified_review.review
        metrics_table.add_row("Tools Used", f"{len(review.tools_used)} ({', '.join(review.tools_used[:3])}...)")
        metrics_table.add_row("Issues Found", str(len(review.issues)))
        metrics_table.add_row("Files Reviewed", str(len(review.files_reviewed)))
        metrics_table.add_row("Total Duration", f"{trace.duration:.2f}s")
        metrics_table.add_row("Trace ID", trace.id[:12] + "...")

        self.console.print(metrics_table)

    def show_progress(self, message: str):
        """Show a progress message."""
        self.console.print(f"[cyan]⏳ {message}[/cyan]")

    def show_stats_dashboard(self, traces: list):
        """
        Show statistics dashboard from multiple traces.

        Args:
            traces: List of Trace objects
        """
        if not traces:
            self.console.print("[yellow]No traces found. Run some reviews first![/yellow]")
            return

        from src.utils.metrics import MetricsAnalyzer
        analyzer = MetricsAnalyzer()
        metrics = analyzer.aggregate(traces)

        # Create stats table
        stats_table = Table(title="📊 Statistics Dashboard", show_header=True, header_style="bold cyan")
        stats_table.add_column("Metric", style="cyan bold")
        stats_table.add_column("Value", style="green")

        stats_table.add_row("Total Reviews", str(metrics.num_traces))
        stats_table.add_row("Avg Quality Score", f"{metrics.avg_quality_score:.1f}/100")
        stats_table.add_row("Avg Retry Count", f"{metrics.avg_retry_count:.2f}")
        stats_table.add_row("Avg Issues Found", f"{metrics.avg_issues_found:.1f}")
        stats_table.add_row("Avg Duration", f"{metrics.avg_duration:.2f}s")

        self.console.print(stats_table)

        # Top issue types
        if metrics.top_issue_types:
            self.console.print("\n[bold cyan]Top Issue Categories:[/bold cyan]")
            for category, count in metrics.top_issue_types[:5]:
                self.console.print(f"  • {category}: {count}")

        self.console.print()
