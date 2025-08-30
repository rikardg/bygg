from dataclasses import dataclass
from pathlib import Path
import subprocess

import pytest


@dataclass
class TestcaseParameters:
    __test__ = False
    name: str
    actions: list[str]


testcases_dir = Path("testcases")

testcases: list[TestcaseParameters] = [
    TestcaseParameters("restart_build", ["restart_once"]),
    TestcaseParameters("trim", ["trim"]),
]


filetree_ignore = (
    "__pycache__",
    ".bygg",
    ".venv",
)


def filetree(path: str):
    return sorted(
        [
            str(p.relative_to(path))
            for p in Path(path).rglob("**/*")
            if not any(sub in str(p) for sub in filetree_ignore)
        ]
    )


@pytest.mark.parametrize("testcase", testcases, ids=lambda x: x.name)
def test_list(snapshot, clean_bygg_tree, testcase):
    example_path = clean_bygg_tree / testcases_dir / testcase.name

    process = subprocess.run(
        ["bygg", "--list"],
        cwd=clean_bygg_tree / testcases_dir / testcase.name,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert process.stdout == snapshot
    assert filetree(example_path) == snapshot

    for action in testcase.actions:
        process = subprocess.run(
            ["bygg", action],
            cwd=clean_bygg_tree / testcases_dir / testcase.name,
            capture_output=True,
            encoding="utf-8",
        )
        assert process.returncode == 0
        assert filetree(example_path) == snapshot

        process = subprocess.run(
            ["bygg", action, "--clean"],
            cwd=clean_bygg_tree / testcases_dir / testcase.name,
            capture_output=True,
            encoding="utf-8",
        )
        assert process.returncode == 0
        assert filetree(example_path) == snapshot


def test_trim(snapshot, clean_bygg_tree):
    example_path = clean_bygg_tree / testcases_dir / "trim"

    process = subprocess.run(
        ["bygg", "create_trimmable"],
        cwd=example_path,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert filetree(example_path) == snapshot

    process = subprocess.run(
        ["bygg", "trim"],
        cwd=example_path,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert filetree(example_path) == snapshot

    # Run a second time to check that it works when the "actual" target has been run

    process = subprocess.run(
        ["bygg", "create_trimmable"],
        cwd=example_path,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert filetree(example_path) == snapshot

    process = subprocess.run(
        ["bygg", "trim"],
        cwd=example_path,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert filetree(example_path) == snapshot
