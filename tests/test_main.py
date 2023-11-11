from dataclasses import dataclass
from pathlib import Path
import subprocess

import pytest


@dataclass
class ExampleParameters:
    name: str
    list_rc: int = 0


# TODO exceptions below indicate missing functionality
examples = [
    ExampleParameters("checks"),
    ExampleParameters("environments"),
    ExampleParameters("failing_jobs"),
    ExampleParameters("only_python"),  # TODO: should have list_rc=1
    ExampleParameters("parametric"),
    ExampleParameters("taskrunner"),
    ExampleParameters("trivial", list_rc=1),  # TODO: should have list_rc=0
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
    assert process.returncode == 0
    assert process.stdout == snapshot


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_tree_directory(snapshot, clean_bygg_tree, example):
    process = subprocess.run(
        ["bygg", "--tree", "-C", examples_dir / example.name],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert process.stdout == snapshot


def test_dump_schema(snapshot):
    process = subprocess.run(
        ["bygg", "--dump-schema"],
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert process.stdout == snapshot
