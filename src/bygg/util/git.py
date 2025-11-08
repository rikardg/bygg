from pathlib import Path
import subprocess
from typing import Optional


def git_is_repo(path: Optional[str] = None) -> bool:
    """Check if the given path is inside a git repository. Path defaults to the current
    working directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def git_get_tracked_files(path: Optional[str] = None) -> set[str]:
    """Get the files tracked by git. Path defaults to the current working directory."""
    if not git_is_repo(path):
        return set()
    result = subprocess.run(
        ["git", "ls-tree", "HEAD", "--name-only", "-r", "-z"],
        cwd=path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode == 0:
        return set(result.stdout.rstrip("\0").split("\0"))
    return set()


def git_glob_files(
    pattern: str | list[str], path: Optional[str] = None, include_untracked: bool = True
) -> set[str]:
    """
    Get files matching glob pattern(s), respecting .gitignore rules. Includes untracked
    files by default. Path defaults to the current working directory.
    """
    if not git_is_repo(path):
        return set()

    patterns = [pattern] if isinstance(pattern, str) else pattern

    all_files = set()

    tracked_result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if tracked_result.returncode == 0 and tracked_result.stdout:
        all_files.update(tracked_result.stdout.rstrip("\0").split("\0"))

    if include_untracked:
        untracked_result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if untracked_result.returncode == 0 and untracked_result.stdout:
            all_files.update(untracked_result.stdout.rstrip("\0").split("\0"))

    return {
        file_path
        for file_path in all_files
        if file_path and any(Path(file_path).match(p) for p in patterns)
    }
