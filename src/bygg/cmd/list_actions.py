import shutil
import textwrap

from bygg.cmd.configuration import DEFAULT_ENVIRONMENT_NAME
from bygg.cmd.datastructures import (
    ByggContext,
    EntryPoint,
    SubProcessIpcData,
    SubProcessIpcDataList,
    get_entrypoints,
)
from bygg.output.output import (
    TerminalStyle as TS,
)

list_actions_style = "B"

HEADER = f"{TS.BOLD}Available actions:{TS.RESET}"


def list_collect_for_environment(
    ctx: ByggContext, environment_name: str
) -> SubProcessIpcDataList:
    """Collects the currently loaded entrypoints"""
    entrypoints = get_entrypoints(ctx, environment_name)
    sorted_actions = sorted(entrypoints, key=lambda x: x.name)
    default_action_name = ctx.configuration.settings.default_action

    return SubProcessIpcDataList(
        actions={x.name: x.description for x in sorted_actions},
        default_action=default_action_name,
    )


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


def print_actions(ctx: ByggContext, environment_data: dict[str, SubProcessIpcData]):
    """Prints a list of actions from different environments."""
    display_environment_names = (
        len(
            [
                len(v.list.actions)
                for k, v in environment_data.items()
                if v.list and len(v.list.actions) > 0
            ]
        )
        > 1
    )

    output = [HEADER]

    if display_environment_names:
        output.append("")

    for env, data in sorted(
        environment_data.items(),
        key=lambda x: (0, x[0]) if x[0] == DEFAULT_ENVIRONMENT_NAME else (1, x[0]),
    ):
        if not data.list:
            continue

        if display_environment_names:
            # Get the human-friendly name or fall back to the environment key:
            environment = ctx.configuration.environments.get(env)
            if env == DEFAULT_ENVIRONMENT_NAME:
                environment_name = "No environment"
            elif environment and environment.name:
                environment_name = environment.name
            else:
                environment_name = env

            output.append(f"~~ {environment_name} ~~")

        output += list_actions_B(
            [EntryPoint(name, descr) for name, descr in data.list.actions.items()],
            data.list.default_action,
        )
    print("\n".join(output))
