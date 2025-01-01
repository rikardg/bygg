import argparse
from collections.abc import Callable
import contextlib
import os
import pickle
import subprocess
import sys
import tempfile

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
from bygg.cmd.datastructures import ByggContext, SubProcessIpcData, get_entrypoints
from bygg.cmd.environments import (
    load_environment,
    setup_environment,
    should_restart_with,
)
from bygg.cmd.list_actions import list_collect_for_environment, print_actions
from bygg.cmd.maintenance import perform_maintenance
from bygg.cmd.tree import print_tree, tree_collect_for_environment
from bygg.core.runner import ProcessRunner
from bygg.core.scheduler import Scheduler
from bygg.logging import logger
from bygg.output.output import TerminalStyle as TS
from bygg.output.output import output_error, output_info, output_warning
from bygg.output.status_display import on_job_status, on_runner_status


def init_bygg_context(
    configuration: Byggfile, parser: argparse.ArgumentParser, args: argparse.Namespace
) -> ByggContext:
    scheduler = Scheduler()
    runner = ProcessRunner(scheduler)

    # Set up status listeners
    runner.job_status_listener = on_job_status
    runner.runner_status_listener = on_runner_status

    return ByggContext(
        runner,
        scheduler,
        configuration,
        parser,
        args,
        ByggNamespace(**vars(args)),
        SubProcessIpcData(),
    )


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
    if not args.is_restarted_with_env:
        do_completion(parser)
        parent_dispatcher(parser, args)
    else:
        subprocess_dispatcher(parser, args)
    return True


def parent_dispatcher(
    parser: argparse.ArgumentParser,
    args_namespace: argparse.Namespace,
) -> dict[str, SubProcessIpcData] | None:
    """
    Takes both argparse.ArgumentParser and argparse.Namespace arguments since it can be
    called also from completers. However, it is not used by subprocesses.
    """

    args = ByggNamespace(**vars(args_namespace))
    assert not args.is_restarted_with_env

    # Generate completions, dump schema or print the version
    generate_shell_completions(args.completions)

    if args.dump_schema:
        dump_schema()
        sys.exit(0)

    if args.version:
        print_version()
        sys.exit(0)

    # Change directory if needed
    directory = args.directory[0] if args.directory else None

    if directory:
        directory_arg = args.directory[0]
        output_info(f"Entering directory '{directory_arg}'")
        os.chdir(directory_arg)

    # No byggfiles
    if not has_byggfile():
        output_error("No build files found.")
        sys.exit(1)

    # Read static configuration
    configuration = read_config_files()

    # Perform maintenance commands
    if args.maintenance_commands:
        perform_maintenance(configuration, args.maintenance_commands)
        sys.exit(0)

    # Create runner and scheduler and such
    ctx = init_bygg_context(configuration, parser, args_namespace)

    actions_to_build = [*args.actions]
    if not args.actions and ctx.configuration.settings.default_action is not None:
        actions_to_build.append(ctx.configuration.settings.default_action)

    logger.info("Actions to be built: %s", actions_to_build)

    only_collect = (
        not actions_to_build
        or args.list_actions
        or args.check
        or args.tree
        or is_completing()
    )

    # We have nothing to build, but other things to do
    if only_collect:
        environment_data = do_in_all_environments(ctx, collect_environment_data)

        if is_completing():
            return environment_data

        if args.list_actions:
            print_actions(ctx, environment_data)
            sys.exit(0)

        if args.tree:
            if not actions_to_build:
                output_error(
                    "The --tree command requires at least one action to be specified."
                )
                output_error(
                    "No actions were specified and no default action is defined."
                )
                print_actions(ctx, environment_data)
                sys.exit(1)
            tree_actions = set(actions_to_build)
            for v in environment_data.values():
                if v.tree:
                    tree_actions = tree_actions - v.found_actions
                    print_tree(v.tree, list(actions_to_build))
            if tree_actions:
                not_found_actions = [
                    f"'{a}'"
                    for a in (filter(lambda x: x in tree_actions, actions_to_build))
                ]
                output_error(
                    f"Error: The following action{'s' if len(not_found_actions) > 1 else ''} could not be found: {TS.BOLD}{', '.join(not_found_actions)}{TS.NOBOLD}."
                )
                sys.exit(1)
            sys.exit(0)

        print_actions(ctx, environment_data)
        sys.exit(1)

    # Here we have something to build
    for action in actions_to_build:
        environment_data = do_in_all_environments(
            ctx,
            lambda ctx, environment_name: run_action_in_environment(
                ctx, environment_name, action=action
            ),
        )
        all_found_actions = set().union(
            *(env.found_actions for env in environment_data.values())
        )

        if action not in all_found_actions:
            output_error(
                f"Error: The following action could not be found: {TS.BOLD}'{action}'{TS.NOBOLD}."
            )
            sys.exit(1)
        sys.exit(0)

    assert not "this point should not be reached"
    sys.exit(1)


def do_in_all_environments(
    ctx: ByggContext, doer: Callable[[ByggContext, str], SubProcessIpcData]
) -> dict[str, SubProcessIpcData]:
    """
    Runs doer for all environments and returns the environment data.
    """
    environment_data: dict[str, SubProcessIpcData] = {}
    environment_names = [DEFAULT_ENVIRONMENT_NAME, *ctx.configuration.environments]
    for environment_name in environment_names:
        environment_data[environment_name] = doer(ctx, environment_name)
    return environment_data


def collect_environment_data(
    ctx: ByggContext, environment_name: str
) -> SubProcessIpcData:
    """
    Collects data about the given environment.
    """
    subprocess_data = SubProcessIpcData()
    if environment_name == DEFAULT_ENVIRONMENT_NAME:
        # collect data
        load_environment(ctx, environment_name)
        subprocess_data.found_actions = {e.name for e in get_entrypoints(ctx)}
        subprocess_data.list = list_collect_for_environment(ctx)
        if is_completing():
            # Early-out if completing; the completion tester in pytest messes with code
            # that is loaded dynamically in examples/trivial so that tree doesn't work.
            # Might be fixable, but that's for future Homer. Completion code works fine
            # when called interactively and not from pytest.
            return subprocess_data
        subprocess_data.tree = tree_collect_for_environment(ctx)
    else:
        environment = ctx.configuration.environments.get(environment_name, None)
        assert environment
        setup_environment(environment)
        subprocess_bygg_path = should_restart_with(environment)

        if not subprocess_bygg_path:
            output_error(
                f"Environment '{environment_name}' is not configured properly."
            )
            sys.exit(1)

        subprocess_data = spawn_subprocess(
            ctx,
            environment_name=environment_name,
            subprocess_bygg_path=subprocess_bygg_path,
        )

    # All critical errors will already have done sys.exit
    return subprocess_data


def run_action_in_environment(
    ctx: ByggContext,
    environment_name: str,
    *,
    action: str,
) -> SubProcessIpcData:
    """
    Runs the given action in the given environment.
    """
    subprocess_data = SubProcessIpcData()
    if environment_name == DEFAULT_ENVIRONMENT_NAME:
        load_environment(ctx, environment_name)
        subprocess_data.found_actions = {e.name for e in get_entrypoints(ctx)}
        subprocess_data.list = list_collect_for_environment(ctx)
        subprocess_data.tree = tree_collect_for_environment(ctx)

        if action not in subprocess_data.found_actions:
            return subprocess_data

        status = False
        if ctx.bygg_namespace.clean:
            status = clean(ctx, [action])
        else:
            status = build(
                ctx,
                [action],
                ctx.bygg_namespace.jobs,
                ctx.bygg_namespace.always_make,
                ctx.bygg_namespace.check,
            )
        if not status:
            sys.exit(1)
    else:
        environment = ctx.configuration.environments.get(environment_name, None)
        assert environment
        setup_environment(environment)
        subprocess_bygg_path = should_restart_with(environment)

        if not subprocess_bygg_path:
            output_error(
                f"Environment '{environment_name}' is not configured properly."
            )
            sys.exit(1)

        subprocess_data = spawn_subprocess(
            ctx,
            environment_name=environment_name,
            subprocess_bygg_path=subprocess_bygg_path,
            action=action,
        )

    # All critical errors will already have done sys.exit
    return subprocess_data


@contextlib.contextmanager
def auto_tmpfile():
    ipc_filename: str | None = None
    try:
        # Create IPC file
        fd, ipc_filename = tempfile.mkstemp()
        os.close(fd)
        yield ipc_filename
    finally:
        if ipc_filename:
            os.remove(ipc_filename)


def spawn_subprocess(
    ctx: ByggContext,
    *,
    environment_name: str,
    subprocess_bygg_path: str,
    action: str | None = None,
) -> SubProcessIpcData:
    # Create IPC file

    with auto_tmpfile() as ipc_filename:
        exec_list = []
        exec_list += [subprocess_bygg_path]
        if action:
            exec_list += [action]
        exec_list += unparse_args(
            ctx.parser,
            ctx.args_namespace,
            drop=["actions", "maintenance_commands"],
        )
        exec_list += ["--is_restarted_with_env", environment_name]
        exec_list += ["--ipc_filename", ipc_filename]

        logger.debug("Restarting with: %s", exec_list)
        return_code = 0
        try:
            subprocess.run(exec_list, encoding="utf-8", check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            match e:
                case subprocess.CalledProcessError() if e.returncode == DISPATCHER_IS_COMPLETING_EXIT_CODE or e.returncode == DISPATCHER_ACTION_NOT_FOUND_EXIT_CODE:
                    # NOP
                    logger.info("Subprocess returned with code %s", e.returncode)
                    return_code = e.returncode
                    pass
                case subprocess.CalledProcessError():
                    output_error(
                        f"Action {TS.BOLD}{action}{TS.NOBOLD}: status {e.returncode}"
                    )
                    sys.exit(e.returncode)
                case FileNotFoundError():
                    output_error(
                        f"Error: Could not restart with '{subprocess_bygg_path}'."
                    )
                    output_warning(
                        "Make sure that bygg is in your pip requirements list for this environment."
                    )
                    sys.exit(1)

        try:
            logger.info("Reading IPC file '%s'", ipc_filename)
            with open(ipc_filename, "rb") as f:
                subprocess_data: SubProcessIpcData = pickle.load(f)
                subprocess_data.return_code = return_code
                return subprocess_data
        except (FileNotFoundError, pickle.PickleError) as e:
            logger.error("Error: %s, %s", e.__class__, e)
            match e:
                case FileNotFoundError():
                    output_error(f"Error: Could not open IPC file '{ipc_filename}'.")
                    sys.exit(1)
                case pickle.PickleError():
                    output_error(f"Error: Invalid IPC file '{ipc_filename}'.")
                    sys.exit(1)

    assert not "this point should not be reached"
    sys.exit(1)


def subprocess_dispatcher(parser, args_namespace):
    # We're in subprocess

    # Always called with at most one action at a time; it is up to the caller to loop
    # over the action list.

    args = ByggNamespace(**vars(args_namespace))
    assert args.is_restarted_with_env
    logger.info(
        "Running action '%s' in environment '%s'.",
        args.actions,
        args.is_restarted_with_env,
    )

    # Read static configuration
    configuration = read_config_files()

    # Create runner and scheduler and such
    ctx = init_bygg_context(configuration, parser, args_namespace)

    ctx.ipc_data = SubProcessIpcData()
    load_environment(ctx, args.is_restarted_with_env)

    ctx.ipc_data.found_actions = {e.name for e in get_entrypoints(ctx)}
    action = args.actions[0] if args.actions else None

    ctx.ipc_data.list = list_collect_for_environment(ctx)
    ctx.ipc_data.tree = tree_collect_for_environment(ctx)

    ipc_filename = args.ipc_filename[0] if args.ipc_filename else None
    if ipc_filename:
        logger.debug("Writing IPC data to %s", args.ipc_filename)
        with open(ipc_filename, "wb") as f:
            pickle.dump(ctx.ipc_data, f)

    if is_completing():
        sys.exit(DISPATCHER_IS_COMPLETING_EXIT_CODE)

    if action and action not in ctx.scheduler.build_actions or not action:
        sys.exit(DISPATCHER_ACTION_NOT_FOUND_EXIT_CODE)

    if args.clean:
        status = clean(ctx, [action])
    else:
        status = build(ctx, [action], args.jobs, args.always_make, args.check)

    if not status:
        sys.exit(1)
    sys.exit(0)
