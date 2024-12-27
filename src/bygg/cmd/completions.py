import argparse
import os
from pathlib import Path
import shutil
import sys
import textwrap
from typing import Any, Generator

from argcomplete.completers import BaseCompleter, DirectoriesCompleter
from argcomplete.finders import CompletionFinder

from bygg.output.output import output_plain


class ByggfileDirectoriesCompleter(DirectoriesCompleter):
    """
    A completer for directories that contain Bygg files.
    """

    # TODO: error in typing in argcomplete, see https://github.com/rikardg/bygg/issues/192.
    def __call__(self, prefix, **kwargs) -> Generator[str, Any, None]:  # type: ignore
        directories = super().__call__(prefix, **kwargs)
        byggfile_dirs = set()
        for dir in directories:
            byggfile_dirs |= {
                str(b.parent)
                for b in Path(dir).rglob("Byggfile.*")
                if b.suffix in {".py", ".yml"}
            }
        for f in sorted(list(byggfile_dirs)):
            yield f


def construct_already_there(
    parser: argparse.ArgumentParser | Any, options: set[str]
) -> set[str]:
    """
    Construct a set of options that are already present among the command line
    arguments. Adds both the short and long versions if they exist.
    """
    already_there_set: set[str] = set()
    for action in parser._get_optional_actions():
        option_strings = set(action.option_strings)
        if option_strings & options:
            already_there_set.update(option_strings)
    return already_there_set


singular_options = {
    "--completions",
    "--dump-schema",
    "--help",
    "--version",
    "-h",
    "-v",
}

directory_option = {"-C", "--directory"}


class ByggCompletionFinder(CompletionFinder):
    """
    Override _get_completions because we want custom completion patterns that are not
    expressed in argparse.
    """

    def _get_completions(
        self, comp_words, cword_prefix, cword_prequote, last_wordbreak_pos
    ) -> list[str]:
        comp_words_set = set(comp_words)

        # Stop completions if we already have a "singular" option, i.e. an option that
        # should not be followed by anything else.
        if comp_words_set & singular_options:
            return []

        # Get completions from argparse.
        completions = set(
            super()._get_completions(
                comp_words, cword_prefix, cword_prequote, last_wordbreak_pos
            )
        )

        # If the last word is a directory, the default completions will be from the
        # directories completer, so return these.
        if comp_words[-1] in directory_option:
            return list(completions)

        action_completions = list(filter(lambda x: not x.startswith("-"), completions))
        already_there = construct_already_there(self._parser, comp_words_set)

        if comp_words_set & {"--tree", "--clean"}:
            # Actions if we have them.
            if action_completions and not cword_prefix.startswith("-"):
                return action_completions
            return list(completions & directory_option - already_there)

        if comp_words_set & {"--list"}:
            # Only complete directories.
            return list(completions & directory_option - already_there)

        # Return action completions if they exist and user has not entered a '-'.
        if action_completions and not cword_prefix.startswith("-"):
            return action_completions

        return list(completions - already_there)


def do_completion(parser: argparse.ArgumentParser):
    completer = ByggCompletionFinder()
    completer(parser)


def is_completing():
    return os.environ.get("_ARGCOMPLETE") == "1"


def generate_shell_completions(print_and_exit: bool):
    bygg_bin = Path(sys.argv[0])
    bygg_completions = bygg_bin.resolve().parent / "_bygg_completions.sh"
    if not bygg_completions.exists():
        import argcomplete.shell_integration

        with open(bygg_completions, "w") as f:
            f.write(argcomplete.shell_integration.shellcode([str(bygg_bin.name)]))

    if print_and_exit:
        terminal_cols, _ = shutil.get_terminal_size()
        indent_string = "# "
        width = min(terminal_cols, 80) - len(indent_string)
        description = f"""\
            A shell completions script has been generated in {bygg_completions}. It will
            pick up the bygg that is in PATH. Add the following line to your shell's
            startup script to load completions:
        """
        output_plain(
            textwrap.indent(
                textwrap.fill(
                    textwrap.dedent(description),
                    width=width,
                    break_long_words=False,
                    break_on_hyphens=False,
                ),
                indent_string,
            )
        )
        output_plain(f"\nsource {bygg_completions}")

        sys.exit(0)


# TODO: error in typing in argcomplete, see https://github.com/rikardg/bygg/issues/192.
# pyright: reportIncompatibleMethodOverride=warning
class EntrypointCompleter(BaseCompleter):
    def __call__(
        self,
        *,
        prefix,
        action: argparse.Action,
        parser: argparse.ArgumentParser,
        parsed_args: argparse.Namespace,
        **kwargs,
    ):
        import textwrap

        from bygg.cmd.dispatcher import dispatcher

        subprocess_data = dispatcher(parser, parsed_args)
        if not subprocess_data:
            return {}

        # There can technically only be one default_action, but easy way to consolidate:
        default_actions = {
            ipc_data.list.default_action
            for env, ipc_data in subprocess_data.items()
            if ipc_data.list is not None
        }

        env_actions = [
            ipc_data.list.actions
            for env, ipc_data in subprocess_data.items()
            if ipc_data.list is not None
        ]

        actions = {
            name: textwrap.fill(
                f"{'(default) ' if name in default_actions else ''}{description}", 7000
            )
            for action_set in env_actions
            for name, description in action_set.items()
            if name not in parsed_args.actions
        }

        return actions
