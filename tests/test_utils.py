from bygg.action import Action
from bygg.util import create_shell_command, filenames_from_pattern


def test_filenames_from_pattern_1():
    input_files = ["/foo/bar/baz.txt.j2"]
    in_pattern = "%.j2"
    out_pattern = "out_%"
    output_files = [("/foo/bar/baz.txt.j2", "/foo/bar/out_baz.txt")]
    assert filenames_from_pattern(input_files, in_pattern, out_pattern) == output_files


def test_filenames_from_pattern_2():
    input_files = ["/foo/bar/baz.txt.j2"]
    in_pattern = "%.txt.j2"
    out_pattern = "out_%.txt"
    output_files = [("/foo/bar/baz.txt.j2", "/foo/bar/out_baz.txt")]
    assert filenames_from_pattern(input_files, in_pattern, out_pattern) == output_files


def test_filenames_from_pattern_3():
    input_files = ["foo.c", "bar.c"]
    in_pattern = "%.c"
    out_pattern = "%.o"
    output_files = [("foo.c", "foo.o"), ("bar.c", "bar.o")]
    assert filenames_from_pattern(input_files, in_pattern, out_pattern) == output_files


def test_filenames_from_pattern_4():
    input_files = ["foo.txt", "bar.txt"]
    in_pattern = "%"
    out_pattern = "out_%"
    output_files = [("foo.txt", "out_foo.txt"), ("bar.txt", "out_bar.txt")]
    assert filenames_from_pattern(input_files, in_pattern, out_pattern) == output_files


def test_shell_command():
    shell_command = create_shell_command("echo 'shell action output'")

    status = shell_command(Action("test context", inputs=set(), outputs=set()))
    assert status.rc == 0
    assert status.output == "shell action output\n"
