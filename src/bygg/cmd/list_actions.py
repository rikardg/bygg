import os
import shutil
import sys
import textwrap

from bygg.cmd.argument_parsing import ByggNamespace
from bygg.cmd.configuration import DEFAULT_ENVIRONMENT_NAME
from bygg.cmd.datastructures import (
    ByggContext,
    EntryPoint,
    SubProcessIpcData,
    SubProcessIpcDataList,
    get_entrypoints,
)
from bygg.logging import logger
from bygg.output.output import (
    TerminalStyle as TS,
)
from bygg.output.output import output_error

list_actions_style = "B"

HEADER = f"{TS.BOLD}Available actions:{TS.RESET}"


def list_collect_subprocess(
    ctx: ByggContext,
    args: ByggNamespace,
) -> bool:
    entrypoints = get_entrypoints(ctx, args)

    if args.is_restarted_with_env and not entrypoints:
        return False

    sorted_actions = sorted(entrypoints, key=lambda x: x.name)
    default_action_name = ctx.configuration.settings.default_action

    if ctx.ipc_data:
        logger.debug("Sorted actions: %s", sorted_actions)
        ctx.ipc_data.list = SubProcessIpcDataList(
            actions={x.name: x.description for x in sorted_actions},
            default_action=default_action_name,
        )
        return True

    return False


def list_actions(ctx: ByggContext, args: ByggNamespace) -> bool:
    # TODO consider consolidating this function with print_actions

    entrypoints = get_entrypoints(ctx, args)

    if args.is_restarted_with_env and not entrypoints:
        return False

    if not entrypoints:
        program_name = os.path.basename(sys.argv[0])
        output_error("Loaded build files but no entrypoints were found.")
        output_error(f"Type `{program_name} --help` for help.")
        return False

    output = [HEADER]

    sorted_actions = sorted(entrypoints, key=lambda x: x.name)
    default_action_name = ctx.configuration.settings.default_action

    if ctx.ipc_data:
        logger.debug("Sorted actions: %s", sorted_actions)
        ctx.ipc_data.list = SubProcessIpcDataList(
            actions={x.name: x.description for x in sorted_actions},
            default_action=default_action_name,
        )
        return True

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
        output += list_actions_A(sorted_actions)

    if list_actions_style == "B":
        output += list_actions_B(sorted_actions, default_action_name)

    print("\n".join(output))

    return True


def list_actions_A(actions: list[EntryPoint]) -> list[str]:
    terminal_cols, terminal_rows = shutil.get_terminal_size()

    output: list[str] = []
    output.append("")
    section_indent = 0
    separator = " : "
    max_name_width = max([len(x.name) for x in actions])
    width = min(terminal_cols, 80)
    subsequent_indent = " " * (section_indent + max_name_width + len(separator))
    for action in actions:
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
    return output


def list_actions_B(
    actions: list[EntryPoint], default_action_name: str | None
) -> list[str]:
    output: list[str] = []
    output.append("")
    for action in actions:
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
    return output


def print_actions(ctx: ByggContext, subprocess_output: dict[str, SubProcessIpcData]):
    """Prints a list of actions from different environments."""
    display_environment_names = (
        len(
            [
                len(v.list.actions)
                for k, v in subprocess_output.items()
                if v.list and len(v.list.actions) > 0
            ]
        )
        > 1
    )

    output = [HEADER]

    if display_environment_names:
        output.append("")

    for env, data in sorted(
        subprocess_output.items(),
        key=lambda x: (0, x[0]) if x[0] == DEFAULT_ENVIRONMENT_NAME else (1, x[0]),
    ):
        if not data.list:
            continue

        if display_environment_names:
            # Get the human-friendly name or fall back to the environment key:
            environment = ctx.configuration.environments.get(env)
            environment_name = (
                environment.name if environment and environment.name else env
            )
            output.append(f"~~ {environment_name} ~~")

        output += list_actions_B(
            [EntryPoint(name, descr) for name, descr in data.list.actions.items()],
            data.list.default_action,
        )
    print("\n".join(output))
