"""Main CLI interface for the code review assistant."""
import click
from pathlib import Path

from src.loops.event_loop import EventLoop
from src.loops.hill_climbing_loop import HillClimbingLoop
from src.storage.trace_store import TraceStore
from src.utils.display import RichDisplay


@click.group()
def cli():
    """🔄 Automated Code Review Assistant - Loop Engineering POC"""
    pass


@cli.command()
def review():
    """
    Run a code review on current git changes.

    This triggers all loops:
    - Loop 1: Agent analyzes code with tools
    - Loop 2: Quality verification with retry
    - Loop 3: Event orchestration and storage
    - Loop 4: Triggered every 5th review
    """
    try:
        # Determine which prompt version to use
        from src.config import settings
        optimized_prompts = settings.prompts_dir / "optimized_prompts.json"
        prompt_version = "optimized" if optimized_prompts.exists() else "base"

        if prompt_version == "optimized":
            click.echo("[info] Using optimized prompt from Loop 4 improvements")

        # Create event loop and handle review event
        event_loop = EventLoop(prompt_version=prompt_version)
        trace = event_loop.handle_event("manual_review", {})

        if trace is None:
            click.echo("\n💡 Tip: Make some code changes (e.g., create a Python file with issues) and try again")
            return

    except KeyboardInterrupt:
        click.echo("\n\nReview cancelled by user.")
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--num-traces', '-n', default=10, help='Number of traces to analyze')
def improve(num_traces):
    """
    Manually trigger Loop 4 self-improvement analysis.

    Analyzes recent traces and generates improved prompts.
    """
    try:
        hill_climbing = HillClimbingLoop()
        improvements = hill_climbing.analyze_and_improve(num_traces=num_traces)

        if improvements:
            click.echo(f"\n✅ Generated {len(improvements)} improvement(s)")
        else:
            click.echo("\n✅ Analysis complete")

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        import traceback
        traceback.print_exc()


@cli.command()
def stats():
    """
    Show statistics dashboard from all reviews.

    Displays aggregate metrics across all stored traces.
    """
    try:
        trace_store = TraceStore()
        traces = trace_store.get_all()

        display = RichDisplay()
        display.show_stats_dashboard(traces)

        if traces:
            click.echo(f"\nTotal traces analyzed: {len(traces)}")
            click.echo(f"Stored in: {trace_store.storage_dir}")

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)


@cli.command()
@click.argument('trace_id')
def show_trace(trace_id):
    """
    Show details of a specific trace.

    TRACE_ID: The ID of the trace to display
    """
    try:
        trace_store = TraceStore()
        trace = trace_store.load(trace_id)

        if trace is None:
            click.echo(f"❌ Trace not found: {trace_id}")
            return

        display = RichDisplay()
        display.show_header()
        click.echo(f"\nTrace ID: {trace.id}")
        click.echo(f"Event: {trace.event_type}")
        click.echo(f"Timestamp: {trace.timestamp}")
        click.echo()

        display.show_review(trace.verified_review)
        display.show_metrics(trace)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)


@cli.command()
def init():
    """
    Initialize the project (create directories, check dependencies).
    """
    from src.config import settings
    import sys

    click.echo("🔧 Initializing Code Review Assistant...")

    # Check if .env exists
    env_file = Path(".env")
    if not env_file.exists():
        click.echo("\n⚠️  .env file not found!")
        click.echo("Creating .env from .env.example...")

        env_example = Path(".env.example")
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            click.echo("✅ .env file created. Please add your OPENAI_API_KEY.")
            click.echo("\nEdit .env and set:")
            click.echo("  OPENAI_API_KEY=your_key_here")
            return
        else:
            click.echo("❌ .env.example not found!")
            return

    # Check OpenAI API key
    if not settings.openai_api_key or settings.openai_api_key == "your_key_here":
        click.echo("\n⚠️  OPENAI_API_KEY not set in .env file!")
        click.echo("Please edit .env and add your OpenAI API key.")
        return

    # Ensure directories exist
    settings.traces_dir.mkdir(parents=True, exist_ok=True)
    settings.improvements_dir.mkdir(parents=True, exist_ok=True)
    settings.prompts_dir.mkdir(parents=True, exist_ok=True)

    click.echo("✅ Directories created")

    # Check if prompts exist
    base_prompts = settings.prompts_dir / "base_prompts.json"
    if not base_prompts.exists():
        click.echo("⚠️  base_prompts.json not found!")
        return

    click.echo("✅ Prompts loaded")
    click.echo("\n🎉 Initialization complete!")
    click.echo("\nNext steps:")
    click.echo("  1. Make some code changes in a git repository")
    click.echo("  2. Run: python -m src.main review")
    click.echo("  3. After 5 reviews, Loop 4 will trigger automatically")


@cli.command()
def demo():
    """
    Run a quick demo with a sample file.

    Creates a sample Python file with issues and reviews it.
    """
    import tempfile
    import os

    click.echo("🎬 Running demo...")

    # Create a sample file with issues
    sample_code = '''
import os

# Potential SQL injection
def unsafe_query(user_input):
    return f"SELECT * FROM users WHERE name={user_input}"

# Missing error handling
def risky_division(a, b):
    return a / b

# Hardcoded password
password = "secretpass123"

# Using weak hash
import hashlib
def weak_hash(data):
    return hashlib.md5(data.encode()).hexdigest()
'''

    click.echo("\n📝 Creating sample file with security issues...")

    # Write sample file
    sample_file = Path("demo_sample.py")
    sample_file.write_text(sample_code)

    click.echo("✅ Created demo_sample.py")

    # Initialize git if needed
    if not Path(".git").exists():
        click.echo("\n⚠️  Not a git repository. Initializing...")
        os.system("git init")
        os.system("git config user.email 'demo@example.com'")
        os.system("git config user.name 'Demo User'")

    # Add file to git
    os.system("git add demo_sample.py")

    click.echo("\n🔍 Running review...\n")

    # Run review
    from src.loops.event_loop import EventLoop
    event_loop = EventLoop()
    event_loop.handle_event("demo", {})

    click.echo("\n✨ Demo complete!")
    click.echo(f"\nYou can now:")
    click.echo(f"  - View the demo file: cat demo_sample.py")
    click.echo(f"  - Run more reviews: python -m src.main review")
    click.echo(f"  - Check stats: python -m src.main stats")


if __name__ == "__main__":
    cli()
