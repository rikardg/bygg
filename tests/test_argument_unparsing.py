import pytest

from bygg.cmd.argument_unparsing import unparse_args
from bygg.cmd.dispatcher import EntrypointCompleter, create_argument_parser

args = [
    (["-v"], ["--version"]),
    (["--version"], ["--version"]),
    (["--clean"], ["--clean"]),
    (["-l"], ["--list"]),
    (["--list"], ["--list"]),
    (["--tree"], ["--tree"]),
    (["-B"], ["--always-make"]),
    (["--always-make"], ["--always-make"]),
    (["-C", "foo/bar"], ["--directory=foo/bar"]),
    # more complex
    (["-C", "foo/bar", "-l"], ["--directory=foo/bar", "--list"]),
    (
        ["-C", "foo/bar", "action1", "-B"],
        ["--directory=foo/bar", "action1", "--always-make"],
    ),
]


@pytest.mark.parametrize("arg", args, ids=lambda x: " ".join(x[0]))
def test_unparse_args(arg):
    in_arg, out_arg = arg
    parser = create_argument_parser(EntrypointCompleter())
    parsed_args = parser.parse_args(in_arg)
    assert sorted(unparse_args(parser, parsed_args)) == sorted(out_arg)


def test_unparse_args_drop():
    parser = create_argument_parser(EntrypointCompleter())
    parsed_args = parser.parse_args(["-C", "foo/bar", "action1", "-B"])
    assert sorted(unparse_args(parser, parsed_args, drop=["directory"])) == sorted(
        ["action1", "--always-make"]
    )
    assert sorted(unparse_args(parser, parsed_args, drop=["always_make"])) == sorted(
        ["--directory=foo/bar", "action1"]
    )
    assert sorted(unparse_args(parser, parsed_args, drop=["actions"])) == sorted(
        ["--directory=foo/bar", "--always-make"]
    )
    assert sorted(
        unparse_args(parser, parsed_args, drop=["actions", "always_make", "directory"])
    ) == sorted([])
