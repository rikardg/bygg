from pathlib import Path

import pytest

from bygg.cmd.completions import ByggCompletionFinder
from bygg.cmd.dispatcher import EntrypointCompleter, create_argument_parser
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
        # Patch os.fdopen to raise NotImplementedError; this causes argcomplete to use
        # stderr for debug output instead of opening file descriptor 9, which causes pytest
        # to get its knickers in a twist.
        monkeypatch.setattr("os.fdopen", open_raise)

        parser = create_argument_parser(EntrypointCompleter())
        completer = ByggCompletionFinder()

        with open(outfile, "w", encoding="utf-8"):
            completer(parser, exit_method=dummy_exit_method)

        with open(outfile, "r", encoding="utf-8") as f:
            return f.read()

    return tester


args = [
    # Complete simple arguments:
    ("--ver", "--version "),
    ("--cl", "--clean "),
    ("--h", "--help "),
    # No completions after these arguments:
    ("-h ", ""),
    ("--help ", ""),
    ("-v ", ""),
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


@pytest.mark.parametrize("arg", actions_completions, ids=lambda x: str(x.name))
def test_actions_completions(completion_tester, arg, snapshot, clean_bygg_tree):
    dir = str(arg)
    with change_dir(clean_bygg_tree):
        testcase = f"-C {dir} "
        testresult = completion_tester(testcase)
        assert sorted(testresult.split("\x0b")) == snapshot

    with change_dir(clean_bygg_tree):
        testcase = f"--directory {dir} "
        testresult = completion_tester(testcase)
        assert sorted(testresult.split("\x0b")) == snapshot

    with change_dir(clean_bygg_tree):
        with change_dir(dir):
            testresult = completion_tester("")
            assert sorted(testresult.split("\x0b")) == snapshot
