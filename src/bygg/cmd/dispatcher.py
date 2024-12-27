import argparse
import os
import pickle
import subprocess
import sys
import tempfile

from bygg.cmd.apply_configuration import apply_configuration
from bygg.cmd.argument_parsing import ByggNamespace, create_argument_parser
from bygg.cmd.argument_unparsing import unparse_args
from bygg.cmd.build_clean import build, clean
from bygg.cmd.completions import (
    EntrypointCompleter,
    do_completion,
    generate_shell_completions,
    is_completing,
)
from bygg.cmd.configuration import (
    DEFAULT_ENVIRONMENT_NAME,
    Byggfile,
    dump_schema,
    has_byggfile,
    read_config_files,
)
from bygg.cmd.datastructures import ByggContext, SubProcessIpcData
from bygg.cmd.list_actions import list_actions, list_collect_subprocess, print_actions
from bygg.cmd.maintenance import perform_maintenance
from bygg.cmd.tree import display_tree, print_tree
from bygg.core.runner import ProcessRunner
from bygg.core.scheduler import Scheduler
from bygg.logging import logger
from bygg.output.output import (
    output_error,
    output_info,
    output_warning,
)
from bygg.output.status_display import (
    on_job_status,
    on_runner_status,
)


def init_bygg_context(configuration: Byggfile):
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

DISPATCHER_IS_COMPLETING_EXIT_CODE = 126
"""Exit code returned by a subprocess when completing."""

DISPATCHER_ACTION_NOT_FOUND_EXIT_CODE = 127
"""Exit code returned by a subprocess when an action is not found."""


def bygg():
    """Entry point for the Bygg command line interface."""
    parser = create_argument_parser(EntrypointCompleter())
    args = parser.parse_args()
    if args.is_restarted_with_env is None:
        do_completion(parser)
    return dispatcher(parser, args)


def dispatcher(
    parser: argparse.ArgumentParser, args_namespace: argparse.Namespace
) -> dict[str, SubProcessIpcData] | None:
    """
    Takes both argparse.ArgumentParser and argparse.Namespace arguments since it can be
    called also from completers.
    """

    args = ByggNamespace(**vars(args_namespace))

    generate_shell_completions(args.completions)

    if args.dump_schema:
        dump_schema()
        sys.exit(0)

    if args.version:
        print_version()
        sys.exit(0)

    directory = args.directory[0] if args.directory else None

    if directory and not args.is_restarted_with_env:
        directory_arg = args.directory[0]
        output_info(f"Entering directory '{directory_arg}'")
        os.chdir(directory_arg)

    if not has_byggfile():
        output_error("No build files found.")
        sys.exit(1)

    configuration = read_config_files()

    if args.maintenance_commands and not args.is_restarted_with_env:
        perform_maintenance(configuration, args.maintenance_commands)
        sys.exit(0)

    ctx = init_bygg_context(configuration)

    if not configuration.environments:
        if has_byggfile():
            # No environments, so just load the Python build file directly.
            apply_configuration(configuration, None, None)

            # Gather and return actions if completing
            if is_completing():
                ctx.ipc_data = SubProcessIpcData()
                list_collect_subprocess(ctx, args)
                return {DEFAULT_ENVIRONMENT_NAME: ctx.ipc_data}

            status = inner_dispatch(ctx, args)
        else:
            status = list_actions(ctx, args)

        if status:
            sys.exit(0)
        sys.exit(1)

    # Execute each action within the correct environment:

    # Parent process
    if not args.is_restarted_with_env:
        subprocess_output: dict[str, SubProcessIpcData] = {}
        actions: list[str | None] = (
            [*args.actions]
            if len(args.actions) > 0
            else [configuration.settings.default_action]
        )

        for action in actions:
            dispatch_for_toplevel_process(
                ctx, args_namespace, parser, subprocess_output, action
            )

            # Act on results from subprocess execution. Only actions that are to be
            # built or cleaned need to continue the loop beyond the first pass.

            if is_completing():
                return subprocess_output

            if args.list_actions:
                print_actions(ctx, subprocess_output)
                sys.exit(0)

            truthy_actions = set(filter(None, actions))
            found_actions: set[str] = set().union(
                *(i.found_actions for i in subprocess_output.values())
            )

            if action not in found_actions:
                output_error(f"Action '{action}' not found in any environment.")
                sys.exit(1)

            if args.tree:
                # TODO error out if there no actions could be printed
                for k, v in subprocess_output.items():
                    if v.tree:
                        print_tree(v.tree, list(truthy_actions))
                sys.exit(0)

            if not truthy_actions:
                output_error("No actions specified and no default action is defined.\n")
                print_actions(ctx, subprocess_output)
                sys.exit(1)

        sys.exit(0)

    # We're in subprocess

    # Always called with at most one action at a time; it is up to the caller to loop
    # over the action list.
    # The list also always contains at least the null element so that
    # dispatch_for_subprocess will get called.
    assert len(args.actions) <= 1
    subprocess_actions: list[str | None] = (
        [args.actions[0]] if len(args.actions) > 0 else [None]
    )
    for sp_action in subprocess_actions:
        dispatch_for_subprocess(ctx, args, sp_action)


def dispatch_for_toplevel_process(
    ctx: ByggContext,
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    subprocess_output: dict[str, SubProcessIpcData],
    action: str | None,
):
    """Dispatches an action in all environments."""
    logger.info("Dispatch for toplevel process, action: %s", action)
    for environment in ctx.configuration.environments:
        assert environment
        # Check if we should restart with another Python interpreter (e.g. from a
        # virtualenv):
        restart_with = apply_configuration(ctx.configuration, environment, None)
        assert restart_with is not None  # this should not happen

        # Create IPC file
        fd, ipc_filename = tempfile.mkstemp()
        os.close(fd)

        exec_list = []
        exec_list += [restart_with]
        if action:
            exec_list += [action]
        exec_list += unparse_args(
            parser,
            args,
            drop=["actions", "maintenance_commands"],
        )
        exec_list += ["--is_restarted_with_env", environment]
        exec_list += ["--ipc_filename", ipc_filename]

        logger.debug("Restarting with: %s", exec_list)
        try:
            process = subprocess.run(exec_list, encoding="utf-8")
            if (
                process.returncode == DISPATCHER_IS_COMPLETING_EXIT_CODE
                or process.returncode == DISPATCHER_ACTION_NOT_FOUND_EXIT_CODE
            ):
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
                    subprocess_output[environment] = pickle.load(f)
            except (FileNotFoundError, pickle.PickleError) as e:
                print(e)
                pass
            os.remove(ipc_filename)


def dispatch_for_subprocess(ctx: ByggContext, args: ByggNamespace, action: str | None):
    logger.info("Dispatch for subprocess")
    logger.debug("Action: %s", action)
    # We're in subprocess
    ctx.ipc_data = SubProcessIpcData()
    apply_configuration(
        ctx.configuration, args.is_restarted_with_env, args.is_restarted_with_env
    )

    # Always fill the subprocess data
    if ctx.ipc_data:
        list_collect_subprocess(ctx, args)
        entry_points = [
            a.name for k, a in ctx.scheduler.build_actions.items() if a.is_entrypoint
        ]
        display_tree(ctx, entry_points)
        if action and action in ctx.scheduler.build_actions:
            ctx.ipc_data.found_actions.add(action)

    ipc_filename = args.ipc_filename[0] if args.ipc_filename else None
    if ipc_filename:
        logger.debug("Writing IPC data to %s", args.ipc_filename)
        with open(ipc_filename, "wb") as f:
            pickle.dump(ctx.ipc_data, f)

    if is_completing():
        sys.exit(DISPATCHER_IS_COMPLETING_EXIT_CODE)

    if action and action not in ctx.scheduler.build_actions:
        sys.exit(DISPATCHER_ACTION_NOT_FOUND_EXIT_CODE)

    status = inner_dispatch(ctx, args)
    if not status:
        sys.exit(1)


def inner_dispatch(ctx: ByggContext, args: ByggNamespace) -> bool:
    """
    Executes the appropriate bygg commands on the supplied action list. Used both from
    the toplevel in the case where there is no dedicated environment as well as when
    each environment gets loaded in a subprocess.
    """
    logger.info("Doing dispatch")
    # Analysis implies building:
    always_make = args.always_make or args.check

    if args.list_actions:
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

    if args.is_restarted_with_env and not actions:
        assert False, "This should not happen"
        sys.exit(DISPATCHER_ACTION_NOT_FOUND_EXIT_CODE)

    if not actions:
        output_error("No actions specified and no default action is defined.\n")
        list_actions(ctx, args)
        status = False
    elif args.clean:
        status = clean(ctx, actions)
    elif args.tree:
        status = display_tree(ctx, actions)
    else:
        jobs = int(args.jobs) if args.jobs else None
        status = build(ctx, actions, jobs, always_make, args.check)

    return status
