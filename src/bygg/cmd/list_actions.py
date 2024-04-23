import os
import shutil
import sys
import textwrap

from bygg.cmd.datastructures import ByggContext, get_entrypoints
from bygg.output.output import (
    TerminalStyle as TS,
)
from bygg.output.output import output_error

list_actions_style = "B"


def list_actions(ctx: ByggContext) -> bool:
    entrypoints = get_entrypoints(ctx)

    if not entrypoints:
        program_name = os.path.basename(sys.argv[0])
        output_error("Loaded build files but no entrypoints were found.")
        output_error(f"Type `{program_name} --help` for help.")
        return False

    terminal_cols, terminal_rows = shutil.get_terminal_size()
    output = [f"{TS.BOLD}Available actions:{TS.RESET}"]

    sorted_actions = sorted(entrypoints, key=lambda x: x.name)
    default_action_name = ctx.configuration.settings.default_action

    if default_action_name:
        default_action_list = [
            x for x in sorted_actions if x.name == default_action_name
        ]

        if default_action_list:
            default_action = default_action_list[0]
            default_action_name = default_action.name
            sorted_actions.remove(default_action)
            sorted_actions.insert(0, default_action)

    if list_actions_style == "A":
        output.append("")
        section_indent = 0
        separator = " : "
        max_name_width = max([len(x.name) for x in entrypoints])
        width = min(terminal_cols, 80)
        subsequent_indent = " " * (section_indent + max_name_width + len(separator))
        for action in sorted_actions:
            description = f"{TS.BOLD}{action.name: <{max_name_width}}{TS.RESET}{separator}{action.description}"
            output.extend(
                textwrap.wrap(
                    description,
                    width=width,
                    initial_indent=" " * section_indent,
                    subsequent_indent=subsequent_indent,
                )
            )
            output.append("")

    if list_actions_style == "B":
        output.append("")
        for action in sorted_actions:
            default_action_suffix = (
                " (default)" if action.name == default_action_name else ""
            )
            output.append(f"{TS.BOLD}{action.name}{default_action_suffix}{TS.RESET}")
            output.append(
                textwrap.fill(
                    action.description,
                    initial_indent="    ",
                    subsequent_indent="    ",
                )
            )
            output.append("")

    print("\n".join(output))

    return True
