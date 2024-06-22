from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

import pytest


@dataclass
class ExampleParameters:
    name: str
    list_rc: int = 0
    tree_rc: int = 0


examples = [
    ExampleParameters("checks"),
    ExampleParameters("environments"),
    ExampleParameters("failing_jobs"),
    ExampleParameters("only_python", tree_rc=1),
    ExampleParameters("parametric"),
    ExampleParameters("taskrunner"),
    ExampleParameters("trivial"),
]

examples_dir = Path("examples")


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_list(snapshot, clean_bygg_tree, example):
    process = subprocess.run(
        ["bygg", "--list"],
        cwd=clean_bygg_tree / examples_dir / example.name,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == example.list_rc
    assert process.stdout == snapshot


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_list_directory(snapshot, clean_bygg_tree, example):
    process = subprocess.run(
        ["bygg", "--list", "-C", examples_dir / example.name],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == example.list_rc
    assert process.stdout == snapshot


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_tree(snapshot, clean_bygg_tree, example):
    process = subprocess.run(
        ["bygg", "--tree"],
        cwd=clean_bygg_tree / examples_dir / example.name,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == example.tree_rc
    assert process.stdout == snapshot


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_tree_directory(snapshot, clean_bygg_tree, example):
    process = subprocess.run(
        ["bygg", "--tree", "-C", examples_dir / example.name],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == example.tree_rc
    assert process.stdout == snapshot


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_tree_non_existing_action(snapshot, clean_bygg_tree, example):
    process = subprocess.run(
        ["bygg", "--tree", "no_such_action"],
        cwd=clean_bygg_tree / examples_dir / example.name,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 1
    assert process.stdout == snapshot


# TODO more tests:
# --tree ACTION (one and several existing )


def test_dump_schema(snapshot):
    process = subprocess.run(
        ["bygg", "--dump-schema"],
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert process.stdout == snapshot


def test_version():
    process = subprocess.run(
        ["bygg", "--version"],
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert process.stdout[1:7] == " bygg "
    # Version string looks something like this when developing:
    # 🛈 bygg 0.3.3.dev5+g900af94
    # Clean it and check if it seems valid. However, it will vary depending on what tags
    # are set etc, so only do a rudimentary check for numbers in a major-minor pattern.
    cleaned_version = process.stdout[7:].strip()
    assert re.match(r"\d+\.\d+", cleaned_version)


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_non_existing_action(snapshot, clean_bygg_tree, example):
    process = subprocess.run(
        ["bygg", "no_such_action", "-C", examples_dir / example.name],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 1
    assert process.stdout == snapshot
