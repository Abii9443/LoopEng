"""Git-related tools for extracting diffs and file information."""
import subprocess
from langchain.tools import tool


@tool
def get_git_diff() -> str:
    """
    Get the current git diff showing staged and unstaged changes.
    Returns the diff as a string, or an error message if no changes found.
    """
    try:
        # Get both staged and unstaged changes
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            return "No changes detected in the git working tree."

        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error getting git diff: {e.stderr}"
    except FileNotFoundError:
        return "Error: git command not found. Is git installed?"


@tool
def get_changed_files() -> str:
    """
    Get a list of files that have been changed (staged and unstaged).
    Returns a newline-separated list of file paths.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            return "No changed files detected."

        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error getting changed files: {e.stderr}"
    except FileNotFoundError:
        return "Error: git command not found."


@tool
def get_file_content(file_path: str) -> str:
    """
    Get the content of a specific file.

    Args:
        file_path: Path to the file to read

    Returns:
        File content or error message
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found."
    except Exception as e:
        return f"Error reading file: {str(e)}"
