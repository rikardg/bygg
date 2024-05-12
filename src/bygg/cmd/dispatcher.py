import argparse
from dataclasses import dataclass
import os
import subprocess
import sys
import tempfile
from typing import Any

from bygg.cmd.apply_configuration import (
    apply_configuration,
    register_actions_from_configuration,
)
from bygg.cmd.argument_unparsing import unparse_args
from bygg.cmd.build_clean import build, clean
from bygg.cmd.completions import (
    ByggfileDirectoriesCompleter,
    do_completion,
    generate_shell_completions,
)
from bygg.cmd.configuration import (
    PYTHON_INPUTFILE,
    YAML_INPUTFILE,
    ByggFile,
    dump_schema,
    read_config_file,
)
from bygg.cmd.datastructures import ByggContext, SubProcessIpcData, get_entrypoints
from bygg.cmd.list_actions import list_actions, list_collect_subprocess, print_actions
from bygg.cmd.tree import display_tree, print_tree
from bygg.core.runner import ProcessRunner
from bygg.core.scheduler import Scheduler
from bygg.output.output import TerminalStyle as TS
from bygg.output.output import (
    output_error,
    output_info,
    output_warning,
)
from bygg.output.status_display import (
    on_job_status,
    on_runner_status,
)
from bygg.system_helpers import change_dir
from loguru import logger
import msgspec


def init_bygg_context(configuration: ByggFile):
    scheduler = Scheduler()
    runner = ProcessRunner(scheduler)

    # Set up status listeners
    runner.job_status_listener = on_job_status
    runner.runner_status_listener = on_runner_status

    return ByggContext(runner, scheduler, configuration)


def print_version():
    import importlib.metadata

    output_info(f"bygg {importlib.metadata.version('bygg')}")


MAKE_COMPATIBLE_PANEL = "(Roughly) Make-compatible options"

DISPATCHER_ACTION_NOT_FOUND_EXIT_CODE = 127
"""Exit code returned by a subprocess when an action is not found."""


def dispatcher():
    """
    A build tool written in Python, where all actions can be written in Python.
    """
    parser = create_argument_parser()
    do_completion(parser)

    args = parser.parse_args()

    generate_shell_completions(args.completions)

    if args.dump_schema:
        dump_schema()
        sys.exit(0)

    if args.version:
        print_version()
        sys.exit(0)

    directory = args.directory[0] if args.directory else None
    is_restarted_with_env = (
        args.is_restarted_with_env[0] if args.is_restarted_with_env else None
    )

    if directory and not is_restarted_with_env:
        directory_arg = args.directory[0]
        output_info(f"Entering directory '{directory_arg}'")
        os.chdir(directory_arg)

    if not os.path.isfile(PYTHON_INPUTFILE) and not os.path.isfile(YAML_INPUTFILE):
        output_error("No build files found.")
        sys.exit(1)

    configuration = read_config_file()
    ctx = init_bygg_context(configuration)

    if not configuration.environments:
        if os.path.isfile(PYTHON_INPUTFILE) or os.path.isfile(YAML_INPUTFILE):
            # No environments, so just load the Python build file directly.
            apply_configuration(configuration, None, None)
            status = do_dispatch(ctx, args)
        else:
            status = list_actions(ctx, args)

        if status:
            sys.exit(0)
        sys.exit(1)

    # Execute each action within the correct environment:

    subprocess_output: dict[str, SubProcessIpcData] = {}

    # Parent process
    if not is_restarted_with_env:
        actions: list[str | None] = (
            args.actions
            if len(args.actions) > 0
            else [configuration.settings.default_action]
        )
        for action in actions:
            dispatch_for_toplevel_process(ctx, args, parser, subprocess_output, action)

        # Print results from subprocess execution

        if not actions:
            output_error("No actions specified and no default action is defined.\n")
            print_actions(subprocess_output)
            sys.exit(1)

        if args.list:
            print_actions(subprocess_output)
            sys.exit(0)

        if args.tree:
            truthy_actions = [a for a in actions if a]
            for k, v in subprocess_output.items():
                if v.tree:
                    print_tree(v.tree, truthy_actions)

        sys.exit(0)

    # We're in subprocess
    assert len(args.actions) <= 1
    subprocess_actions: list[str | None] = [args.actions[0]] or [None]
    for action in subprocess_actions:
        dispatch_for_subprocess(ctx, args, action)


def output_environment_list_tree(ctx: ByggContext, args: argparse.Namespace):
    for environment in ctx.configuration.environments:
        output_info(f"{environment}")
        if args.list:
            output_info(f"  {TS.BOLD}Actions:{TS.RESET}")


def dispatch_for_toplevel_process(
    ctx: ByggContext,
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    subprocess_output: dict[str, SubProcessIpcData],
    action: str | None,
):
    """Dispatches an action in all environments."""
    logger.info(f"Dispatch for toplevel process, action: {action}")
    for environment in ctx.configuration.environments:
        assert environment
        # Check if we should restart with another Python interpreter (e.g. from a
        # virtualenv):
        restart_with = apply_configuration(ctx.configuration, environment, None)

        assert restart_with is not None  # this should not happen

        fd, ipc_filename = tempfile.mkstemp()
        os.close(fd)

        exec_list = []
        exec_list += [restart_with]
        if action:
            exec_list += [action]
        exec_list += unparse_args(parser, args, drop=["actions"])
        exec_list += ["--is_restarted_with_env", environment]
        exec_list += ["--ipc_filename", ipc_filename]

        logger.debug(f"Restarting with: {exec_list}")
        try:
            process = subprocess.run(exec_list, encoding="utf-8")
            if process.returncode == DISPATCHER_ACTION_NOT_FOUND_EXIT_CODE:
                continue
            if process.returncode != 0:
                sys.exit(process.returncode)
        except FileNotFoundError:
            output_error(f"Error: Could not restart with '{restart_with}'.")
            output_warning(
                "Please make sure that bygg is in your pip requirements list for this environment."
            )
            sys.exit(1)
        finally:
            try:
                with open(ipc_filename, "rb") as f:
                    subprocess_output[environment] = msgspec.msgpack.decode(
                        f.read(), type=SubProcessIpcData
                    )
            except (FileNotFoundError, msgspec.DecodeError) as e:
                print(e)
                pass
            os.remove(ipc_filename)


def dispatch_for_subprocess(
    ctx: ByggContext, args: argparse.Namespace, action: str | None
):
    logger.info("Dispatch for subprocess")
    logger.debug(f"Action: {action}")
    # We're in subprocess
    ctx.ipc_data = SubProcessIpcData()
    is_restarted_with_env = (
        args.is_restarted_with_env[0] if args.is_restarted_with_env else None
    )
    apply_configuration(ctx.configuration, is_restarted_with_env, is_restarted_with_env)

    # Always fill the subprocess data, but exit if only listing or treeing
    if ctx.ipc_data:
        list_collect_subprocess(ctx, args)
        entry_points = [
            a.name for k, a in ctx.scheduler.build_actions.items() if a.is_entrypoint
        ]
        display_tree(ctx, entry_points)
        # if args.list or args.tree:
        #     return True

    ipc_filename = args.ipc_filename[0] if args.ipc_filename else None
    if ipc_filename:
        logger.debug(f"Writing IPC data to {args.ipc_filename}")
        with open(ipc_filename, "wb") as f:
            f.write(msgspec.msgpack.encode(ctx.ipc_data))

    if action and action not in ctx.scheduler.build_actions:
        sys.exit(DISPATCHER_ACTION_NOT_FOUND_EXIT_CODE)

    status = do_dispatch(ctx, args)
    if not status:
        sys.exit(1)


def do_dispatch(ctx: ByggContext, args: argparse.Namespace) -> bool:
    # Analysis implies building:
    always_make = args.always_make or args.check

    if args.list:
        list_actions(ctx, args)
        return True

    default_action = ctx.configuration.settings.default_action
    actions = (
        args.actions
        if args.actions
        else [default_action]
        if default_action and default_action in ctx.scheduler.build_actions
        else []
    )

    is_restarted_with_env = (
        args.is_restarted_with_env[0] if args.is_restarted_with_env else None
    )
    if is_restarted_with_env and not actions:
        sys.exit(DISPATCHER_ACTION_NOT_FOUND_EXIT_CODE)

    if not actions:
        output_error("No actions specified and no default action is defined.\n")
        list_actions(ctx, args)
        status = False

    if args.clean:
        status = clean(ctx, actions)
    elif args.tree:
        status = display_tree(ctx, actions)
    else:
        jobs = int(args.jobs) if args.jobs else None
        status = build(ctx, actions, jobs, always_make, args.check)

    return status


@dataclass
class ActionPartition:
    """
    environment_name: The name of the environment that the actions should be run in.
    None means the implicit default environment, i.e. typically the base process.

    actions: The actions that should be run in the environment.
    """

    environment_name: str | None
    actions: list[str]


def partition_actions(
    configuration: ByggFile,
    actions: list[str] | None,
) -> list[ActionPartition] | None:
    """
    Partition the actions into groups that should be run in the same environment. Only
    partition the given actions that also exist in the configuration file. This is to
    not have to load the Python build files for all the environments, since installing
    their respective requirements can take a while.

    Parameters
    ----------
    configuration : ByggFile
        The configuration file.
    actions : list[str] | None
        The actions that should be run. If None, a partition will be created, resolved
        to the default action.

    Returns
    -------
    list[ActionPartition] | None
        A list of ActionPartition objects, each representing a group of actions that
        should be run in the same environment. Returns None if there are no actions in
        the configuration.
    """
    if not configuration.actions:
        return None

    resolved_actions = actions if actions else []

    if not resolved_actions and configuration.settings.default_action is not None:
        # Resolve to default action:
        resolved_actions += [configuration.settings.default_action]
        return [ActionPartition("default", resolved_actions)]

    # Put consecutive actions with the same environment in the same partition:
    action_partitions = []
    action_dict = {a.name: a for a in configuration.actions}
    current_partition: ActionPartition | None = None
    for action in [action_dict[a] for a in resolved_actions]:
        if (
            current_partition is None
            or current_partition.environment_name != action.environment
        ):
            current_partition = ActionPartition(action.environment, [action.name])
            action_partitions.append(current_partition)
        else:
            current_partition.actions.append(action.name)

    return action_partitions


def entrypoint_completions(prefix, parsed_args: argparse.Namespace, **kwargs):
    import textwrap

    # Handle -C/--directory:
    new_dir = parsed_args.directory[0] if parsed_args.directory else None

    with change_dir(new_dir):
        configuration = read_config_file()
        ctx = init_bygg_context(configuration)

        if configuration.environments:
            # We don't want to install environments while completing, so only load the
            # actions from the static configuration file:
            register_actions_from_configuration(ctx.configuration, None)
        else:
            apply_configuration(ctx.configuration, None, None)

        entrypoints = get_entrypoints(ctx, parsed_args)
        # Exlude already added entrypoints:
        eligible_entrypoints = [
            x for x in entrypoints if x.name not in parsed_args.actions
        ]
        # Fill the description really wide to get it combined to a single line with
        # spaces dealt with correctly:
        return {
            x.name: textwrap.fill(x.description, 7000) for x in eligible_entrypoints
        }


def create_argument_parser():
    logger.info("Creating argument parser")

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        nargs=1,
        type=str,
        default=None,
        help=argparse.SUPPRESS,
    )
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
