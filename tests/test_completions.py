from pathlib import Path
import shlex
import subprocess

import pytest

from bygg.system_helpers import change_dir


def dummy_exit_method(status):
    pass


def open_raise(*args, **kwargs):
    raise NotImplementedError


@pytest.fixture
def completion_tester(monkeypatch, tmp_path):
    def tester(testcase):
        prefix = "bygg"
        prefixed_testcase = f"{prefix} {testcase}"
        outfile = tmp_path / "completion.out"

        # Simulate being run from the completion script:
        monkeypatch.setenv("_ARGCOMPLETE", "1")
        monkeypatch.setenv("COMP_LINE", prefixed_testcase)
        monkeypatch.setenv("COMP_POINT", str(len(prefixed_testcase)))
        monkeypatch.setenv("_ARGCOMPLETE_STDOUT_FILENAME", str(outfile))

        subprocess.run(
            shlex.split(prefixed_testcase),
            capture_output=True,
            encoding="utf-8",
        )

        if not outfile.exists():
            return ""

        with open(outfile, "r", encoding="utf-8") as f:
            return f.read()

    return tester


args = [
    # Complete simple arguments:
    ("--vers", "--version "),
    ("--verb", "--verbose "),
    ("--cl", "--clean "),
    ("--h", "--help "),
    # No completions after these arguments:
    ("-h ", ""),
    ("--help ", ""),
    ("-V ", ""),
    ("--version ", ""),
    ("--dump-schema ", ""),
    ("--completions ", ""),
]


@pytest.mark.parametrize("arg", args, ids=lambda x: x[0])
def test_completions(completion_tester, arg):
    testcase, correct_result = arg
    testresult = completion_tester(testcase)
    assert correct_result == testresult


# Directories:
directories_completions = [
    "-C ",
    "--directory ",
]


@pytest.mark.parametrize("arg", directories_completions, ids=lambda x: x)
def test_directory_completions(completion_tester, arg, snapshot, monkeypatch):
    monkeypatch.chdir("examples")
    testcase = arg
    testresult = completion_tester(testcase)
    assert sorted(testresult.split("\x0b")) == snapshot


actions_completions = [p for p in Path("examples").iterdir() if p.is_dir()]


@pytest.mark.parametrize(
    "bygg_dev", [False, True], ids=["BYGG_DEV_unset", "BYGG_DEV_set"]
)
@pytest.mark.parametrize("example_dir", actions_completions, ids=lambda x: str(x.name))
@pytest.mark.parametrize(
    "testcase_template",
    ["-C {dir} ", "--directory {dir} ", ""],
    ids=["-C", "--directory", "cwd"],
)
def test_actions_completions(
    completion_tester,
    example_dir,
    snapshot,
    clean_bygg_tree,
    monkeypatch,
    bygg_dev,
    testcase_template,
):
    if bygg_dev:
        monkeypatch.setenv("BYGG_DEV", "1")

    # Empty template means no -C or --directory argument
    should_chdir = len(testcase_template) == 0
    testcase = (
        testcase_template
        if should_chdir
        else testcase_template.format(dir=str(example_dir))
    )

    with change_dir(
        (clean_bygg_tree / example_dir) if should_chdir else clean_bygg_tree
    ):
        testresult = completion_tester(testcase)
        assert sorted(testresult.split("\x0b")) == snapshot
