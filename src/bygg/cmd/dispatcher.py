import argparse
from dataclasses import dataclass
import os
import subprocess
import sys
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
from bygg.cmd.datastructures import ByggContext, get_entrypoints
from bygg.cmd.list_actions import list_actions
from bygg.cmd.tree import display_tree
from bygg.core.runner import ProcessRunner
from bygg.core.scheduler import Scheduler
from bygg.output.output import (
    TerminalStyle as TS,
)
from bygg.output.output import (
    output_error,
    output_info,
    output_plain,
    output_warning,
)
from bygg.output.status_display import (
    on_job_status,
    on_runner_status,
)
from bygg.system_helpers import change_dir


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

    try:
        action_partitions = (
            partition_actions(configuration, args.actions) if configuration else None
        )
    except KeyError as e:
        output_plain(
            f"Could not find action {TS.BOLD}{e}{TS.RESET}. List available actions with {TS.BOLD}--list{TS.RESET}."
        )
        sys.exit(1)

    if not action_partitions:
        if os.path.isfile(PYTHON_INPUTFILE):
            # No configuration file, so load the Python build file directly.
            apply_configuration(configuration, None, None)
            default_action = configuration.settings.default_action
            actions = (
                args.actions
                if args.actions
                else [default_action]
                if default_action
                else []
            )
            status = do_dispatch(ctx, args, actions)
        else:
            status = list_actions(ctx)

        if status:
            sys.exit(0)
        sys.exit(1)

    # Special case for --list here, since it shouldn't start loading the environments:
    if args.list:
        status = list_actions(ctx)
        sys.exit(0) if status else sys.exit(1)

    # Execute each action partition within the correct environment:

    for partition in action_partitions:
        env = partition.environment_name
        # Check if we should restart with another Python interpreter (e.g. from a
        # virtualenv):
        restart_with = apply_configuration(configuration, env, is_restarted_with_env)

        if restart_with is not None and not is_restarted_with_env:
            exec_list = [restart_with, *partition.actions] + unparse_args(
                parser, args, drop=["actions"]
            )
            if partition.environment_name:
                exec_list += ["--is_restarted_with_env", partition.environment_name]

            try:
                process = subprocess.run(exec_list, encoding="utf-8")
                if process.returncode != 0:
                    sys.exit(process.returncode)
            except FileNotFoundError:
                output_error(f"Error: Could not restart with '{restart_with}'.")
                output_warning(
                    "Please make sure that bygg is in your pip requirements list for this environment."
                )
                sys.exit(1)
        else:
            status = do_dispatch(ctx, args, partition.actions)
            if not status:
                sys.exit(1)


def do_dispatch(ctx: ByggContext, args: argparse.Namespace, actions: list[str]) -> bool:
    # Analysis implies building:
    always_make = args.always_make or args.check
    if args.clean:
        status = clean(ctx, actions)
    elif args.list:
        list_actions(ctx)
        status = True
    elif not actions:
        output_error("No actions specified and no default action is defined.\n")
        list_actions(ctx)
        status = False
    elif args.tree:
        status = display_tree(ctx.scheduler, actions)
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

        entrypoints = get_entrypoints(ctx)
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
