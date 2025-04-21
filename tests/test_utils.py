import pytest

from bygg.core.action import Action
from bygg.util import create_shell_command, filenames_from_pattern

test_cases_filenames_from_pattern = [
    (
        (
            "%.j2",
            "out_%",
            [("/foo/bar/baz.txt.j2", "/foo/bar/out_baz.txt")],
        )
    ),
    (
        (
            "%.txt.j2",
            "out_%.txt",
            [("/foo/bar/baz.txt.j2", "/foo/bar/out_baz.txt")],
        )
    ),
    (
        (
            "%.c",
            "%.o",
            [("foo.c", "foo.o"), ("bar.c", "bar.o")],
        )
    ),
    (
        (
            "%",
            "out_%",
            [("foo.txt", "out_foo.txt"), ("bar.txt", "out_bar.txt")],
        )
    ),
]


def construct_test_case_name(x: tuple):
    a, b, c = x
    return f"{a} | {b}"


@pytest.mark.parametrize(
    "test_case", test_cases_filenames_from_pattern, ids=construct_test_case_name
)
def test_filenames_from_pattern(test_case):
    in_pattern, out_pattern, input_output_files = test_case
    input_files = [x[0] for x in input_output_files]
    assert (
        filenames_from_pattern(input_files, in_pattern, out_pattern)
        == input_output_files
    )


def test_shell_command():
    Action._current_environment = "test_shell_command"
    shell_command = create_shell_command("echo 'shell action output'")

    status = shell_command(Action("test context", inputs=set(), outputs=set()))
    assert status.rc == 0
    assert status.output == "shell action output\n"
    Action._current_environment = None
