import argparse
from dataclasses import dataclass, field
import shutil
import textwrap
from typing import Any, Literal, TypeAlias

from argcomplete.completers import BaseCompleter

from bygg.cmd.completions import ByggfileDirectoriesCompleter
from bygg.logging import logger

MaintenanceCommand: TypeAlias = Literal["remove_cache", "remove_environments"]


@dataclass
class ByggNamespace:
    """Wrapper for the arguments parsed by argparse. Improves ergonimics when working
    with the arguments."""

    actions: list[str]
    version: bool
    is_restarted_with_env: str | None
    ipc_filename: list[str] | None
    clean: bool
    list_actions: bool
    tree: bool
    jobs: int | None
    always_make: bool
    check: bool
    maintenance_commands: list[MaintenanceCommand]
    completions: bool
    dump_schema: bool
    directory: list[str] = field(default_factory=list)


class ByggHelpFormatter(argparse.RawDescriptionHelpFormatter):
    formatting_width = 80

    def __init__(self, prog):
        terminal_cols, terminal_rows = shutil.get_terminal_size()
        self.formatting_width = min(terminal_cols, self.formatting_width)

        indent_increment = 2
        max_help_position = 24

        super().__init__(
            prog, indent_increment, max_help_position, self.formatting_width
        )

    def _fill_text(self, text, width, indent):
        # Assuming main description starts with a newline
        if text.startswith("\n"):
            return "\n".join(
                [
                    "\n".join(textwrap.wrap(line, width=width))
                    for line in text.splitlines(keepends=True)
                ]
            )
        # Group descriptions
        return argparse.HelpFormatter._fill_text(self, text, width, indent)


def create_argument_parser(entrypoint_completions: BaseCompleter):
    logger.info("Creating argument parser")

    parser = argparse.ArgumentParser(
        formatter_class=ByggHelpFormatter,
        description="""
A build tool written in Python, where all actions can be written in Python.

Build the default action:
 %(prog)s

Build ACTION:
 %(prog)s ACTION

Clean ACTION:
 %(prog)s ACTION --clean

List available actions:
 %(prog)s --list
""",
    )

    parser._positionals.title = "POSITIONAL ARGUMENTS"
    parser._optionals.title = "OPTIONS"

    # Use Any to get around type checking for argcomplete:

    arg: Any = parser.add_argument(
        "actions",
        nargs="*",
        default=None,
        help="Entrypoint actions to operate on.",
    )
    arg.completer = entrypoint_completions

    parser.add_argument(
        "-v", "--version", action="store_true", help="Show version string and exit."
    )

    parser.add_argument(
        "--is_restarted_with_env",
        nargs="?",
        type=str,
        help=argparse.SUPPRESS,
    )
    # Used internally for communicating the IPC filename to the subprocess.
    parser.add_argument(
        "--ipc_filename",
        nargs=1,
        type=str,
        default=None,
        help=argparse.SUPPRESS,
    )
    # Commands that operate on the build setup:
    build_setup_wrapper_group = parser.add_argument_group(
        "Commands that operate on the build setup"
    )  # add_mutually_exclusive_group doesn't accept a title, so wrap it in a regular group.
    build_setup_group = build_setup_wrapper_group.add_mutually_exclusive_group()
    build_setup_group.add_argument(
        "--clean",
        action="store_true",
        help="Clean the outputs of the specified actions.",
    )
    build_setup_group.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="list_actions",
        help="List available actions.",
    )
    build_setup_group.add_argument(
        "--tree",
        action="store_true",
        help="Display the dependency tree starting from the specified action(s).",
    )
    # Some arguments inspired by Make:
    make_group = parser.add_argument_group("Make-like arguments")
    arg = make_group.add_argument(
        "-C",
        "--directory",
        nargs=1,
        type=str,
        default=None,
        help="Change to the specified directory.",
    )
    arg.completer = ByggfileDirectoriesCompleter()

    make_group.add_argument(
        "-j",
        "--jobs",
        nargs="?",
        type=int,
        default=None,
        help="Specify the number of jobs to run simultaneously. None means to use the number of available cores.",
    )
    make_group.add_argument(
        "-B",
        "--always-make",
        action="store_true",
        help="Always build all actions.",
    )

    # Analyse and verify:
    analyse_group = parser.add_argument_group(
        "Analyse and verify",
        "Arguments in this group will add more analysis to the build process. Actions will be built and the analysis result will be reported.",
    )
    analyse_group.add_argument(
        "--check",
        action="store_true",
        help="Perform various checks on the action tree. Implies -B",
    )

    # Maintenance arguments:
    maintenance_group = parser.add_argument_group(
        "Maintenance",
        "These commands operate on Bygg's build state. When given a maintenance command, Bygg will just perform the maintenance and exit; it will neither build anything nor perform any other actions.",
    )
    maintenance_group.add_argument(
        "--reset",
        action=AppendConstList,
        const=["remove_cache", "remove_environments"],
        nargs=0,
        dest="maintenance_commands",
        help="Remove the cache and the Python environments. Same as giving --remove-cache and --remove-environments.",
    )
    maintenance_group.add_argument(
        "--remove-cache",
        action="append_const",
        const="remove_cache",
        dest="maintenance_commands",
        help="Remove the build cache.",
    )
    maintenance_group.add_argument(
        "--remove-environments",
        action="append_const",
        const="remove_environments",
        dest="maintenance_commands",
        help="Remove the Python environments.",
    )

    # Meta arguments:
    meta_group = parser.add_argument_group("Meta arguments")
    meta_group.add_argument(
        "--dump-schema",
        action="store_true",
        help="Generate a JSON Schema for the Byggfile.yml files. The schema will be printed to stdout.",
    )
    meta_group.add_argument(
        "--completions",
        action="store_true",
        help="Output instructions for how to set up shell completions via the shell's startup script.",
    )

    return parser


class AppendConstList(argparse.Action):
    """Custom action to append the elements from a list to dest."""

    def __call__(self, parser, namespace, values, option_string=None):
        const_list = getattr(namespace, self.dest) or list()
        const_list.extend(self.const)
        setattr(namespace, self.dest, const_list)
