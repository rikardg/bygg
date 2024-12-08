import pytest

from bygg.core.action import Action
from bygg.util import create_shell_command, filenames_from_pattern

test_cases_filenames_from_pattern = [
    (
        (
            ["/foo/bar/baz.txt.j2"],
            "%.j2",
            "out_%",
            [("/foo/bar/baz.txt.j2", "/foo/bar/out_baz.txt")],
        )
    ),
    (
        (
            ["/foo/bar/baz.txt.j2"],
            "%.txt.j2",
            "out_%.txt",
            [("/foo/bar/baz.txt.j2", "/foo/bar/out_baz.txt")],
        )
    ),
    (
        (
            ["foo.c", "bar.c"],
            "%.c",
            "%.o",
            [("foo.c", "foo.o"), ("bar.c", "bar.o")],
        )
    ),
    (
        (
            ["foo.txt", "bar.txt"],
            "%",
            "out_%",
            [("foo.txt", "out_foo.txt"), ("bar.txt", "out_bar.txt")],
        )
    ),
]


def construct_test_case_name(x: tuple):
    a, b, c, d = x
    return f"{b} | {c}"


@pytest.mark.parametrize(
    "test_case", test_cases_filenames_from_pattern, ids=construct_test_case_name
)
def test_filenames_from_pattern(test_case):
    input_files, in_pattern, out_pattern, output_files = test_case
    assert filenames_from_pattern(input_files, in_pattern, out_pattern) == output_files


def test_shell_command():
    shell_command = create_shell_command("echo 'shell action output'")

    status = shell_command(Action("test context", inputs=set(), outputs=set()))
    assert status.rc == 0
    assert status.output == "shell action output\n"
