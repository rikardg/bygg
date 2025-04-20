import os
import shutil
import stat
import time

from bygg.cmd.datastructures import ByggContext
from bygg.core.runner import get_job_count_limit
from bygg.output.job_output import output_job_logs
from bygg.output.output import output_error, output_info, output_ok, output_warning
from bygg.output.status_display import failed_checks, output_check_results


def build(
    ctx: ByggContext,
    action: str,
    job_count: int | None,
    always_make: bool,
    check: bool,
) -> tuple[bool, set[str]]:
    """
    actions: The actions to build.

    job_count: The number of jobs to run simultaneously. None means to use the number of
    available cores.

    always_make: If True, all actions will be built, even if they are up to date.

    check: If True, apply various checks:

    * Check that the inputs and outputs of all actions will be checked for consistency.
      A job that runs later must not have files as output that are inputs to a job that
      runs earlier.

    Returns a tuple with build status and a set with found input files.
    """
    input_files: set[str] = set()
    try:
        max_workers = get_job_count_limit() if job_count is None else job_count

        t1 = time.time()
        output_info(f"Building action '{action}':")

        ctx.scheduler.start_run(
            action,
            always_make=always_make,
            check=check,
        )

        # Collect for --watch. Needs to be done here when the graph is built up and
        # before build has started.
        for job_name in ctx.scheduler.job_graph.get_all_jobs():
            build_action = ctx.scheduler.build_actions.get(job_name)
            if build_action:
                input_files.update(build_action.inputs)

        status = ctx.runner.start(max_workers)
        ctx.scheduler.shutdown()

        if status:
            output_ok(f"Action '{action}' completed in {time.time() - t1:.2f} s.")
        else:
            output_error(f"Action '{action}' failed after {time.time() - t1:.2f} s.")
            output_job_logs(ctx.runner.failed_jobs)
            return (False, input_files)

    except KeyboardInterrupt:
        output_warning("\nBuild was interrupted by user.")
        return (False, input_files)
    except KeyError as e:
        output_error(f"Error: Action '{e}' not found.")
        return (False, input_files)
    finally:
        ctx.scheduler.shutdown()

    if check and failed_checks:
        return (output_check_results(), input_files)

    return (True, input_files)


def clean(ctx: ByggContext, action: str):
    try:
        output_info(f"Cleaning action '{action}':")
        ctx.scheduler.prepare_run(action)
        for job_name in ctx.scheduler.job_graph.get_all_jobs():
            job = ctx.scheduler.build_actions.get(job_name, None)
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
        ctx.scheduler.shutdown()
    except KeyboardInterrupt:
        output_warning("Build was interrupted by user.")
        return False
    except KeyError as e:
        output_error(f"Error: Action '{e}' not found.")
        return False
    finally:
        ctx.scheduler.shutdown()

    return True
