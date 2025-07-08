from dataclasses import dataclass, field
from pathlib import Path
import re
import subprocess
import sys

import pytest

from bygg.cmd.argument_parsing import fill_help_text
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
class HelpText:
    name: str
    text: str


help_texts = [
    HelpText(
        "basic",
        "This is a basic help text.",
    ),
    HelpText(
        "multiline",
        """
This is a multiline help text.

Line 2. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

Line 3. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
""",
    ),
    HelpText(
        "lists",
        """
This is a multiline help text with lists.

- Line 2. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
- Line 3. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
""",
    ),
]


@pytest.mark.parametrize("help_text", help_texts, ids=lambda x: x.name)
def test_help_formatting(snapshot, help_text):
    assert fill_help_text(help_text.text, 80, "") == snapshot
    assert fill_help_text(help_text.text, 80, "  ") == snapshot


@dataclass
class ExampleParameters:
    name: str
    list_rc: int = 0
    tree_rc: int = 0
    build_rc: int = 0
    environments: list[str] = field(default_factory=list)
    build_yields_cache: bool = True
    actions_for_all_environments: list[str] = field(default_factory=list)


examples = [
    ExampleParameters("checks"),
    ExampleParameters(
        "environments",
        environments=[".venv", ".venv1", ".venv2"],
        actions_for_all_environments=["default_action", "action1", "action2"],
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


def test_schema_dump_is_uptodate():
    process = subprocess.run(
        ["bygg", "--dump-schema"],
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0

    with open("schemas/Byggfile_yml_schema.json", "r", encoding="utf-8") as f:
        schema = f.read()

    assert process.stdout == schema


def test_version():
    process = subprocess.run(
        ["bygg", "--version"],
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert process.stdout[8:14] == " bygg "
    # Version output looks something like this when developing:
    # bygg >>> bygg 0.8.5.dev6+g48b4c41.d20250504
    # Clean it and check if it seems valid. However, it will vary depending on what tags
    # are set etc, so only do a rudimentary check for numbers in a major-minor pattern.
    cleaned_version = process.stdout[14:].strip()
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


def test_build_multiple_actions(snapshot, clean_bygg_tree):
    process = subprocess.run(
        [
            "bygg",
            "-C",
            examples_dir / "taskrunner",
            "shorthand_action_yaml",
            "touch a file",
            "shorthand action yaml, with spaces",
        ],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    cleaned_result = [
        line
        for line in process.stdout.split("\n")
        if "Starting process" not in line and "completed in" not in line
    ]
    assert "\n".join(sorted(cleaned_result)) == snapshot


def test_build_verbose(snapshot, clean_bygg_tree):
    process = subprocess.run(
        [
            "bygg",
            "-C",
            examples_dir / "taskrunner",
            "hhgttg",
            "--verbose",
        ],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    cleaned_result = [
        line for line in process.stdout.split("\n") if not line.startswith("bygg >>>")
    ]
    assert "\n".join(cleaned_result) == snapshot


def test_check(clean_bygg_tree):
    process = subprocess.run(
        [
            "bygg",
            "-C",
            examples_dir / "checks",
        ],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )

    assert process.returncode == 0

    process = subprocess.run(
        [
            "bygg",
            "-C",
            examples_dir / "checks",
            "--check",
        ],
        cwd=clean_bygg_tree,
        capture_output=True,
        encoding="utf-8",
    )
    assert process.returncode == 0
    assert "The following checks reported issues:" in process.stdout


@pytest.mark.parametrize("example", examples, ids=lambda x: x.name)
def test_reset_remove_environments(
    snapshot, clean_bygg_tree, example: ExampleParameters
):
    process = subprocess.run(
        [
            "bygg",
            "-C",
            examples_dir / example.name,
            *example.actions_for_all_environments,
        ],
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
        [
            "bygg",
            "-C",
            examples_dir / example.name,
            *example.actions_for_all_environments,
        ],
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


# Rudimentary test to at least run the watch code
def test_watch():
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run(
            ["bygg", "-C", examples_dir / "taskrunner", "succeed", "--watch"],
            capture_output=True,
            encoding="utf-8",
            timeout=2,
        )
