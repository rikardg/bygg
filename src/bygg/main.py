import argparse
from multiprocessing import cpu_count
import os
import shutil
import stat
import sys
import time
from typing import List, Optional

import rich
import rich.status

from bygg.configuration import (
    PYTHON_INPUTFILE,
    YAML_INPUTFILE,
    ByggFile,
    apply_configuration,
    load_python_build_file,
    read_config_file,
)
from bygg.runner import runner
from bygg.scheduler import scheduler
from bygg.status_display import on_job_status, on_runner_status, progress


def get_job_count_limit():
    # TODO use affinity instead (on U**X): https://stackoverflow.com/a/55423170
    return cpu_count()


def init_status_listeners():
    """
    Set up status listeners.
    """
    runner.job_status_listener = on_job_status
    runner.runner_status_listener = on_runner_status


loading_python_build_file = rich.status.Status(
    "[cyan]Executing Python build file", spinner="dots"
)


def build(actions: List[str], job_count: int | None, always_make: bool) -> bool:
    try:
        with loading_python_build_file:
            load_python_build_file()

        init_status_listeners()

        max_workers = get_job_count_limit() if job_count is None else job_count

        for action in actions:
            t1 = time.time()
            rich.print(f"Building action '{action}':")

            progress.start()
            scheduler.start_run(action, always_make=always_make)
            status = runner.start(max_workers)
            progress.disable
            progress.stop()
            scheduler.shutdown()

            if status:
                rich.print(
                    f"[green]Action '{action}' completed in {time.time() - t1:.2f} s."
                )
            else:
                rich.print(
                    f"[red]Action '{action}' failed after {time.time() - t1:.2f} s."
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
        rich.print("\n[yellow]Build was interrupted by user.[/yellow]")
        return False
    except KeyError as e:
        rich.print(f"[red]Error: Action '{e}' not found.[/red]")
        return False
    finally:
        progress.stop()
        scheduler.shutdown()

    return True


def clean(actions: List[str]):
    try:
        with loading_python_build_file:
            load_python_build_file()

        init_status_listeners()

        for action in actions:
            rich.print(f"Cleaning action '{action}':")
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
                            rich.print(f"Removing directory: {output}")
                            shutil.rmtree(output)
                    except FileNotFoundError:
                        pass
            scheduler.shutdown()
    except KeyboardInterrupt:
        rich.print("[yellow]Build was interrupted by user.[/yellow]")
        return False
    except KeyError as e:
        rich.print(f"[yellow]Error: Action '{e}' not found.[/yellow]")
        return False
    finally:
        progress.stop()
        scheduler.shutdown()

    return True


def check(actions: List[str]):
    print("check")
    t0 = time.time()
    action_count = len(scheduler.build_actions)

    with loading_python_build_file:
        load_python_build_file()
    rich.print(
        f"{len(scheduler.build_actions) - action_count} actions registered in "
        f"{time.time() - t0:.2f} seconds."
    )
    init_status_listeners()

    for action in actions:
        t1 = time.time()
        with rich.status.Status(f"Preparing action '{action}':"):
            scheduler.prepare_run(action)
        rich.print(f"Action '{action}' prepared in {time.time() - t1:.2f} s.")

    rich.print(f"Total time for --check was {time.time() - t0:.2f} s.")
    return True


def list_actions() -> bool:
    with loading_python_build_file:
        load_python_build_file()

    entrypoints = [x for x in scheduler.build_actions.values() if x.is_entrypoint]

    if entrypoints:
        rich.print("Available actions:")
        for action in sorted(entrypoints, key=lambda x: x.name):
            rich.print(f"  {action.name}")
        return True
    else:
        program_name = os.path.basename(sys.argv[0])
        rich.print("[yellow]Loaded build files but no entrypoints were found.[/yellow]")
        rich.print(f"[yellow]Type `{program_name} --help` for help.[/yellow]")
        return False


def print_no_actions_text(configuration: ByggFile | None):
    return list_actions()


MAKE_COMPATIBLE_PANEL = "(Roughly) Make-compatible options"


def dispatcher(
    actions: Optional[List[str]],
    directory_arg: Optional[str],
    jobs_arg: Optional[int],
    always_make_arg: bool,
    check_arg: bool,
    clean_arg: bool,
    list_arg: bool,
):
    """
    A build tool written in Python, where all actions can be written in Python.
    """
    if directory_arg:
        rich.print(f"Entering directory '{directory_arg}'")
        os.chdir(directory_arg)

    if not os.path.isfile(PYTHON_INPUTFILE) and not os.path.isfile(YAML_INPUTFILE):
        rich.print("No build files found.")
        sys.exit(1)

    configuration = read_config_file()
    apply_configuration(configuration)

    resolved_actions = actions if actions else []

    if (
        configuration is not None
        and not actions
        and configuration.settings.default_action is not None
    ):
        resolved_actions += [configuration.settings.default_action]

    status = None

    if not resolved_actions:
        status = print_no_actions_text(configuration)
    elif check_arg:
        status = check(resolved_actions)
    elif clean_arg:
        status = clean(resolved_actions)
    elif list_arg:
        status = list_actions()
    else:
        status = build(resolved_actions, jobs_arg, always_make_arg)

    if not status:
        sys.exit(1)


def main():
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
    parser.add_argument(
        "actions",
        nargs="*",
        default=None,
        help="Entrypoint actions to operate on.",
    )
    # Commands that operate on the build setup:
    build_setup_group = parser.add_argument_group(
        "Commands that operate on the build setup"
    )
    build_setup_group.add_argument(
        "-c",
        "--check",
        action="store_true",
        help="Check the specified actions.",
    )
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

    args = parser.parse_args()

    try:
        return dispatcher(
            args.actions,
            args.directory[0] if args.directory else None,
            int(args.jobs) if args.jobs else None,
            args.always_make,
            args.check,
            args.clean,
            args.list,
        )
    except KeyboardInterrupt:
        rich.print("[red]Interrupted by user. Aborting.[/red]")
        return 1


if __name__ == "__main__":
    main()
