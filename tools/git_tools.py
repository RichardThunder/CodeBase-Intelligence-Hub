"""Git-related tools for agents."""

import subprocess
from pathlib import Path
from typing import Optional
from langchain_core.tools import Tool


def run_git_command(cmd: list[str], repo_path: str = ".") -> str:
    """Execute a git command safely.

    Args:
        cmd: Command list (e.g., ["git", "blame", "file.py"])
        repo_path: Repository path

    Returns:
        Command output or error message
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return f"Git error: {result.stderr}"
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Git command timed out"
    except Exception as e:
        return f"Error running git command: {str(e)}"


def git_blame(file_path: str, line_num: Optional[int] = None, repo_path: str = ".") -> str:
    """Show who last modified each line of a file.

    Args:
        file_path: Path to file (relative to repo)
        line_num: Specific line number (optional)
        repo_path: Repository path

    Returns:
        Git blame output
    """
    if line_num:
        cmd = ["git", "blame", "-L", f"{line_num},{line_num}", file_path]
    else:
        cmd = ["git", "blame", file_path]

    return run_git_command(cmd, repo_path)


def git_log_for_file(
    file_path: str,
    n: int = 5,
    repo_path: str = ".",
) -> str:
    """Show recent commits affecting a file.

    Args:
        file_path: Path to file (relative to repo)
        n: Number of commits to show
        repo_path: Repository path

    Returns:
        Git log output
    """
    cmd = ["git", "log", "-n", str(n), "--oneline", file_path]
    return run_git_command(cmd, repo_path)


def git_show_commit(commit_hash: str, repo_path: str = ".") -> str:
    """Show details of a specific commit.

    Args:
        commit_hash: Commit SHA or ref
        repo_path: Repository path

    Returns:
        Commit details
    """
    cmd = ["git", "show", "--stat", commit_hash]
    return run_git_command(cmd, repo_path)


def get_git_tools(repo_path: str = ".") -> list:
    """Create and return all git tools.

    Args:
        repo_path: Path to repository (passed to tool closures)

    Returns:
        List of Tool objects ready for use in agents
    """
    tools = []

    # Create closures that bind repo_path
    tools.append(
        Tool(
            name="git_blame",
            description="Show who last modified each line of a file (git blame)",
            func=lambda file_path: git_blame(file_path, repo_path=repo_path),
        )
    )

    tools.append(
        Tool(
            name="git_log_for_file",
            description="Show recent commits affecting a file",
            func=lambda file_path: git_log_for_file(file_path, n=5, repo_path=repo_path),
        )
    )

    tools.append(
        Tool(
            name="git_show_commit",
            description="Show details of a specific commit",
            func=lambda commit_hash: git_show_commit(commit_hash, repo_path=repo_path),
        )
    )

    return tools
