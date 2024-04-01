"""
Functions for setting up the file structure.
"""

from pathlib import Path

STATUS_DIR = Path(".bygg")


def make_sure_status_dir_exists():
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
