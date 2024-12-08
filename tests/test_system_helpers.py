import os

import pytest

from bygg.system_helpers import (
    ExitCode,
    call,
    change_dir,
    subprocess_tty,
    subprocess_tty_print,
)


def test_ExitCode():
    # Behaviour as a bool (inverted):
    assert ExitCode(0)
    assert not ExitCode(1)
    assert bool(ExitCode(0)) is True
    assert bool(ExitCode(1)) is False
    # Behaviour as an int:
    assert ExitCode(0) == 0
    assert ExitCode(0) != 1
    assert ExitCode(1) == 1
    assert ExitCode(1) != 0
    assert ExitCode(0) + 3 == 3
    assert ExitCode(1) + 3 == 4
    assert 3 + ExitCode(0) == 3
    assert 3 + ExitCode(1) == 4
    assert ExitCode(0) + ExitCode(0) == 0
    assert ExitCode(3) + ExitCode(2) == 5
    assert ExitCode(0) - ExitCode(0) == 0
    assert ExitCode(3) - ExitCode(2) == 1
    assert ExitCode(0) * ExitCode(0) == 0
    assert ExitCode(3) * ExitCode(2) == 6
    assert ExitCode(3) / ExitCode(2) == 1.5
    assert ExitCode(8) / ExitCode(-4) == -2

    with pytest.raises(ZeroDivisionError):
        assert ExitCode(0) / ExitCode(0) == 0


shell_command = "echo 'foo\nbar\nbaz'"


def test_call(capsys, snapshot):
    call(shell_command)
    captured = capsys.readouterr()
    assert captured.out == snapshot


def test_subprocess_tty_print(capsys, snapshot):
    subprocess_tty_print(shell_command.split(" "))
    captured = capsys.readouterr()
    assert captured.out == snapshot


def test_subprocess_tty():
    words = shell_command.split(" ")[-1].split("\n")
    for line, word in zip(subprocess_tty(shell_command.split(" ")), words):
        assert line.rstrip() == word


def test_change_dir():
    start_dir = os.getcwd()
    with change_dir("/"):
        assert os.getcwd() == "/"
    assert os.getcwd() == start_dir

    with change_dir("examples"):
        assert os.getcwd() == os.path.join(start_dir, "examples")
        with change_dir("checks"):
            assert os.getcwd() == os.path.join(start_dir, "examples/checks")
        assert os.getcwd() == os.path.join(start_dir, "examples")
    assert os.getcwd() == start_dir

    with change_dir("examples/checks"):
        assert os.getcwd() == os.path.join(start_dir, "examples/checks")
    assert os.getcwd() == start_dir

    with change_dir("examples/trivial"):
        assert os.getcwd() == os.path.join(start_dir, "examples/trivial")
    assert os.getcwd() == start_dir

    with change_dir(None):
        assert os.getcwd() == start_dir
    assert os.getcwd() == start_dir
