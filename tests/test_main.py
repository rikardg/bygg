from dataclasses import dataclass, field
from pathlib import Path
import re
import subprocess
import sys

import pytest

from bygg.core.cache import DEFAULT_DB_FILE


@pytest.mark.help
@pytest.mark.parametrize(
    "python_version", [f"{sys.version_info.major}.{sys.version_info.minor}"]
)
def test_help(snapshot, clean_bygg_tree, python_version):
    process = subprocess.run(
        ["bygg", "--help"],
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert process.stdout == snapshot


@dataclass
class ExampleParameters:
    name: str
    list_rc: int = 0
    tree_rc: int = 0
    build_rc: int = 0
    environments: list[str] = field(default_factory=list)
    build_yields_cache: bool = True


examples = [
    ExampleParameters("checks"),
    ExampleParameters(
        "environments",
        environments=[".venv", ".venv1", ".venv2"],
    ),
    ExampleParameters("failing_jobs", build_rc=1),
    ExampleParameters("only_python", tree_rc=1, build_rc=1, build_yields_cache=False),
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


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_reset_remove_environments(
    snapshot, clean_bygg_tree, example: ExampleParameters
):
    process = subprocess.run(
        ["bygg", "-C", examples_dir / example.name],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == example.build_rc

    for environment in example.environments:
        assert Path(
            clean_bygg_tree / examples_dir / example.name / environment
        ).exists()

    process = subprocess.run(
        ["bygg", "-C", examples_dir / example.name, "--remove-environments"],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert process.stdout == snapshot

    for environment in example.environments:
        assert not Path(
            clean_bygg_tree / examples_dir / example.name / environment
        ).exists()


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_reset_remove_cache(snapshot, clean_bygg_tree, example: ExampleParameters):
    process = subprocess.run(
        ["bygg", "-C", examples_dir / example.name],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == example.build_rc

    assert (
        Path(clean_bygg_tree / examples_dir / example.name / DEFAULT_DB_FILE).exists()
        == example.build_yields_cache
    )

    process = subprocess.run(
        ["bygg", "-C", examples_dir / example.name, "--remove-cache"],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert process.stdout == snapshot

    assert not Path(
        clean_bygg_tree / examples_dir / example.name / DEFAULT_DB_FILE
    ).exists()


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_reset_reset(snapshot, clean_bygg_tree, example: ExampleParameters):
    process = subprocess.run(
        ["bygg", "-C", examples_dir / example.name],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == example.build_rc

    for environment in example.environments:
        assert Path(
            clean_bygg_tree / examples_dir / example.name / environment
        ).exists()

    assert (
        Path(clean_bygg_tree / examples_dir / example.name / DEFAULT_DB_FILE).exists()
        == example.build_yields_cache
    )

    process = subprocess.run(
        ["bygg", "-C", examples_dir / example.name, "--reset"],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert process.stdout == snapshot

    for environment in example.environments:
        assert not Path(
            clean_bygg_tree / examples_dir / example.name / environment
        ).exists()

    assert not Path(
        clean_bygg_tree / examples_dir / example.name / DEFAULT_DB_FILE
    ).exists()
