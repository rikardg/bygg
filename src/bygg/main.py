# PYTHON_ARGCOMPLETE_OK

import argparse
from dataclasses import dataclass
import os
import shutil
import stat
import subprocess
import sys
import time
from typing import Any, List

import argcomplete

from bygg.action import Action
from bygg.apply_configuration import apply_configuration
from bygg.configuration import (
    PYTHON_INPUTFILE,
    YAML_INPUTFILE,
    ByggFile,
    dump_schema,
    read_config_file,
)
from bygg.output import output_error, output_info, output_ok, output_warning
from bygg.runner import runner
from bygg.scheduler import scheduler
from bygg.status_display import (
    failed_checks,
    on_job_status,
    on_runner_status,
    output_check_results,
    progress,
)


def get_job_count_limit():
    try:
        # Use os.sched_getaffinity where available (on U**X):
        # https://stackoverflow.com/a/55423170
        return len(os.sched_getaffinity(0))
    except AttributeError:
        count = os.cpu_count()
        assert count is not None
        return count


def init_status_listeners():
    """
    Set up status listeners.
    """
    runner.job_status_listener = on_job_status
    runner.runner_status_listener = on_runner_status


def build(
    actions: List[str],
    job_count: int | None,
    always_make: bool,
    check: bool,
) -> bool:
    """
    actions: The actions to build.

    job_count: The number of jobs to run simultaneously. None means to use the number of
    available cores.

    always_make: If True, all actions will be built, even if they are up to date.

    check: If True, apply various checks:

    * Check that the inputs and outputs of all actions will be checked for consistency.
      A job that runs later must not have files as output that are inputs to a job that
      runs earlier.
    """
    try:
        init_status_listeners()

        max_workers = get_job_count_limit() if job_count is None else job_count

        for action in actions:
            t1 = time.time()
            output_info(f"Building action '{action}':")

            progress.start()
            scheduler.start_run(
                action,
                always_make=always_make,
                check=check,
            )
            status = runner.start(max_workers)
            progress.disable
            progress.stop()
            scheduler.shutdown()

            if status:
                output_ok(f"Action '{action}' completed in {time.time() - t1:.2f} s.")
            else:
                output_error(
                    f"Action '{action}' failed after {time.time() - t1:.2f} s."
                )

            # cs = build(action)
            # if cs is None:
            #     rich.print(f"Action '{action}' is up to date.")
            # else:
            #     rich.print(f"Action '{action}' completed with return code {cs.rc}.")
            #     rich.print(
            #         f"{len(cs.changed_files)} files changed in {time() - t1:.2f} s."
            #     )
            # rich.print("=========================================")
    except KeyboardInterrupt:
        output_warning("\n[yellow]Build was interrupted by user.[/yellow]")
        return False
    except KeyError as e:
        output_error(f"Error: Action '{e}' not found.")
        return False
    finally:
        progress.stop()
        scheduler.shutdown()

    if check and failed_checks:
        return output_check_results()

    return True


def clean(actions: List[str]):
    try:
        init_status_listeners()

        for action in actions:
            output_info(f"Cleaning action '{action}':")
            scheduler.prepare_run(action)
            for job_name in scheduler.job_graph.get_all_jobs():
                job = scheduler.build_actions.get(job_name, None)
                if job is None:
                    continue
                for output in job.outputs:
                    try:
                        s = os.stat(output)
                        if stat.S_ISREG(s.st_mode):
                            os.unlink(output)
                        elif stat.S_ISDIR(s.st_mode):
                            output_info(f"Removing directory: {output}")
                            shutil.rmtree(output)
                    except FileNotFoundError:
                        pass
            scheduler.shutdown()
    except KeyboardInterrupt:
        output_warning("Build was interrupted by user.")
        return False
    except KeyError as e:
        output_error(f"Error: Action '{e}' not found.")
        return False
    finally:
        progress.stop()
        scheduler.shutdown()

    return True


def get_entrypoints(configuration: ByggFile | None) -> List[Action]:
    entrypoints = []
    if configuration:
        entrypoints += [x for x in configuration.actions if x.is_entrypoint]

    if not configuration or not configuration.environments:
        entrypoints += [x for x in scheduler.build_actions.values() if x.is_entrypoint]

    return entrypoints


def list_actions(configuration: ByggFile | None) -> bool:
    entrypoints = get_entrypoints(configuration)

    if entrypoints:
        max_width = max([len(x.name) for x in entrypoints])
        output_info("Available actions:")
        for action in sorted(entrypoints, key=lambda x: x.name):
            output_info(
                f"  {action.name: <{max_width}} : {action.description if action.description else 'No description'}"
            )
        return True
    else:
        program_name = os.path.basename(sys.argv[0])
        output_error("Loaded build files but no entrypoints were found.")
        output_error(f"Type `{program_name} --help` for help.")
        return False


def print_no_actions_text(configuration: ByggFile | None):
    return list_actions(configuration)


def print_version():
    import importlib.metadata

    output_info(f"{__package__} {importlib.metadata.version(__package__)}")


MAKE_COMPATIBLE_PANEL = "(Roughly) Make-compatible options"


def list_actions_and_exit(configuration: ByggFile | None):
    status = list_actions(configuration)
    sys.exit(0) if status else sys.exit(1)


def dispatcher(args: argparse.Namespace):
    """
    A build tool written in Python, where all actions can be written in Python.
    """
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

    if args.list:
        list_actions_and_exit(configuration)

    action_partitions = partition_actions(configuration, args.actions)

    if not action_partitions:
        if os.path.isfile(PYTHON_INPUTFILE):
            # No configuration file, so load the Python build file directly.
            apply_configuration(None, None, None)
            # TODO will not be needed once we allow configuring default action also in
            # Python.
            if not args.actions:
                list_actions_and_exit(configuration)
            status = do_dispatch(args, args.actions)
        else:
            status = print_no_actions_text(configuration)
        if status:
            sys.exit(0)
        sys.exit(1)

    for partition in action_partitions:
        env = partition.environment_name
        # Check if we should restart with another Python interpreter (e.g. from a
        # virtualenv):
        restart_with = apply_configuration(configuration, env, is_restarted_with_env)

        if restart_with is not None and not is_restarted_with_env:
            exec_list = construct_exec_list(args, restart_with, partition)
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
            status = do_dispatch(args, partition.actions)
            if not status:
                sys.exit(1)


def do_dispatch(args: argparse.Namespace, actions: List[str]) -> bool:
    # Analysis implies building:
    always_make = args.always_make or args.check
    if args.clean:
        status = clean(actions)
    else:
        jobs = int(args.jobs) if args.jobs else None
        status = build(actions, jobs, always_make, args.check)

    return status


@dataclass
class ActionPartition:
    """
    environment_name: The name of the environment that the actions should be run in.
    None means the implicit default environment, i.e. typically the base process.

    actions: The actions that should be run in the environment.
    """

    environment_name: str | None
    actions: List[str]


def construct_exec_list(
    args: argparse.Namespace, restart_with: str, partition: ActionPartition
):
    exec_list = [restart_with, *partition.actions]
    for k, v in vars(args).items():
        if k == "actions":
            continue
        elif v is True:
            exec_list.append(f"--{k}")
        elif v:
            exec_list.append(f"--{k} {v}")
    if partition.environment_name:
        exec_list.append("--is_restarted_with_env")
        exec_list.append(partition.environment_name)
    return exec_list


def partition_actions(
    configuration: ByggFile | None,
    actions: List[str] | None,
) -> List[ActionPartition] | None:
    """
    Partition the actions into groups that should be run in the same environment.
    """

    # TODO: Implement this.

    resolved_actions = actions if actions else []

    if configuration:
        if not actions and configuration.settings.default_action is not None:
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


def entrypoint_completions(prefix, parsed_args, **kwargs):
    entrypoints = get_entrypoints(read_config_file())
    return {x.name: x.message for x in entrypoints}


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
    actions_action: Any = parser.add_argument(
        "actions",
        nargs="*",
        default=None,
        help="Entrypoint actions to operate on.",
    )

    actions_action.completer = entrypoint_completions

    # Only add completions for the actions:
    argcomplete.autocomplete(parser, exclude=["-h", "--help"])

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
    # Some arguments inspired by Make:
    make_group = parser.add_argument_group("Make-like arguments")
    make_group.add_argument(
        "-C",
        "--directory",
        nargs=1,
        type=str,
        default=None,
        help="Change to the specified directory.",
    )
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

    return parser


def main():
    parser = create_argument_parser()
    args = parser.parse_args()

    try:
        return dispatcher(args)
    except KeyboardInterrupt:
        output_warning("Interrupted by user. Aborting.")
        return 1


if __name__ == "__main__":
    main()
