"""Linting tools for static code analysis."""
import subprocess
import json
from pathlib import Path
from langchain.tools import tool


@tool
def run_pylint(file_path: str) -> str:
    """
    Run pylint on a Python file to find code quality issues.

    Args:
        file_path: Path to the Python file to analyze

    Returns:
        Formatted string with pylint findings
    """
    try:
        if not Path(file_path).exists():
            return f"Error: File '{file_path}' not found."

        if not file_path.endswith('.py'):
            return f"Skipping {file_path}: Not a Python file."

        result = subprocess.run(
            ["pylint", "--output-format=json", file_path],
            capture_output=True,
            text=True,
        )

        # Pylint returns non-zero for issues, which is expected
        if result.stdout:
            try:
                issues = json.loads(result.stdout)
                if not issues:
                    return f"No pylint issues found in {file_path}."

                formatted = f"Pylint found {len(issues)} issue(s) in {file_path}:\n"
                for issue in issues[:10]:  # Limit to first 10
                    formatted += f"\n  Line {issue.get('line', '?')}: [{issue.get('type', 'unknown')}] {issue.get('message', 'No message')}"
                    formatted += f"\n  Symbol: {issue.get('symbol', 'unknown')}"

                if len(issues) > 10:
                    formatted += f"\n  ... and {len(issues) - 10} more issues"

                return formatted
            except json.JSONDecodeError:
                return f"Pylint completed but output format was unexpected: {result.stdout[:500]}"
        else:
            return f"No pylint issues found in {file_path}."

    except FileNotFoundError:
        return "Error: pylint not found. Install with: pip install pylint"
    except Exception as e:
        return f"Error running pylint: {str(e)}"


@tool
def run_flake8(file_path: str) -> str:
    """
    Run flake8 on a Python file to find style and formatting issues.

    Args:
        file_path: Path to the Python file to analyze

    Returns:
        Formatted string with flake8 findings
    """
    try:
        if not Path(file_path).exists():
            return f"Error: File '{file_path}' not found."

        if not file_path.endswith('.py'):
            return f"Skipping {file_path}: Not a Python file."

        result = subprocess.run(
            ["flake8", "--format=%(row)d:%(col)d: %(code)s %(text)s", file_path],
            capture_output=True,
            text=True,
        )

        if result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            formatted = f"Flake8 found {len(lines)} issue(s) in {file_path}:\n"
            for line in lines[:10]:  # Limit to first 10
                formatted += f"\n  {line}"

            if len(lines) > 10:
                formatted += f"\n  ... and {len(lines) - 10} more issues"

            return formatted
        else:
            return f"No flake8 issues found in {file_path}."

    except FileNotFoundError:
        return "Error: flake8 not found. Install with: pip install flake8"
    except Exception as e:
        return f"Error running flake8: {str(e)}"
