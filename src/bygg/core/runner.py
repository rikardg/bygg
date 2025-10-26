import os
from pathlib import Path
import signal
import sys
from typing import Callable
import warnings

from bygg.core.action import WorkChannel
from bygg.core.common_types import CommandStatus, JobStatus
from bygg.core.job import Job
from bygg.core.scheduler import Scheduler
from bygg.logutils import logger
from bygg.output.output import TerminalStyle as TS
from bygg.output.status_display import on_check_failed

JobStatusListener = Callable[[JobStatus, Job, tuple], None]
RunnerStatusListener = Callable[[str], None]


# Suppress the specific loky warning about fork start method. The current runner
# architecture depends on forking, and at least from what I can discern from reading in
# the loky source code, this is only a problem on Windows.
warnings.filterwarnings(
    "ignore",
    message="`fork` start method should not be used with `loky`",
    category=UserWarning,
)


class ProcessRunner:
    scheduler: Scheduler
    job_status_listener: JobStatusListener
    runner_status_listener: RunnerStatusListener
    failed_jobs: list[Job]

    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
        self.job_status_listener = lambda *args: None
        self.runner_status_listener = lambda *args: None
        self.failed_jobs = []

    def start(self, max_workers: int = 1) -> list[Job]:
        from loky import Future, ProcessPoolExecutor, wait  # type: ignore
        from loky.backend import get_context  # type: ignore

        total_job_count = len(self.scheduler.job_graph)

        self.runner_status_listener(
            f"Starting process runner with {max_workers} threads"
        )

        def init_worker():
            """Ignore CTRL+C in the worker process."""
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        with ProcessPoolExecutor(
            max_workers=max_workers,
            initializer=init_worker,
            context=get_context("fork"),
        ) as pool:
            scheduled_jobs: dict[Job, Future] = {}
            backlog: list[Job] = []

            # Jobs can be deferred because their channel is full. We then need the
            # runner to iterate over running jobs before adding them back to the
            # backlog.
            deferred_backlog: list[Job] = []
            # Keep active WorkChannel objects here since the objects don't survive the
            # serialisation pass intact.
            work_channels: dict[str, WorkChannel] = {}

            def manage_work_channel_add(job: Job) -> bool:
                if work_channel := job.action.work_channel:
                    logger.debug(
                        "Job %s is allocated to work channel %s",
                        job.name,
                        work_channel.name,
                    )

                    if work_channel.name not in work_channels:
                        work_channels[work_channel.name] = work_channel

                    if len(work_channel.current_jobs) >= work_channel.width:
                        logger.debug(
                            "Work channel %s is full. Contents: %s",
                            work_channel.name,
                            work_channel.current_jobs,
                        )
                        backlog.remove(job)
                        deferred_backlog.append(job)
                        return True
                    else:
                        logger.debug(
                            "Work channel %s has room, adding job %s",
                            work_channel.name,
                            job.name,
                        )
                        work_channel.current_jobs.add(job.name)
                return False

            def manage_work_channel_remove(job: Job):
                if job.action.work_channel:
                    work_channel = work_channels.get(job.action.work_channel.name)
                    if work_channel and job.name in work_channel.current_jobs:
                        work_channel.current_jobs.remove(job.name)

            def call_status_listener():
                for job in scheduled_jobs.keys():
                    self.job_status_listener(
                        "running",
                        job,
                        (len(self.scheduler.finished_jobs), total_job_count),
                    )

            def get_job_count_tuple():
                return (
                    len(self.scheduler.finished_jobs) + len(self.failed_jobs),
                    total_job_count,
                )

            # If a job fails, we want to stop scheduling new jobs and just wait for the
            # ones that are already running to finish.
            exit_reasons: list[Job] = []

            while True:
                if (
                    not exit_reasons
                    and len(backlog) < 2 * max_workers
                    and (jobs := self.scheduler.get_ready_jobs())
                ):
                    backlog += jobs

                # Put deferred jobs back on the backlog
                backlog += deferred_backlog
                deferred_backlog = []

                if (
                    len(scheduled_jobs) == 0
                    and len(backlog) == 0
                    and (self.scheduler.run_status() == "finished" or exit_reasons)
                ):
                    return exit_reasons

                # Keep the scheduled queue relatively short; no need to schedule much
                # more than we have workers
                batch_size = max_workers * 2
                if len(scheduled_jobs) < batch_size:
                    for job in backlog:
                        # Skip jobs with no command or ones that are clean
                        if job.action.command is None:
                            job.status = CommandStatus(
                                0,
                                f"{'No command, skipping'}",
                                None,
                            )
                            self.scheduler.job_finished(job)
                            self.job_status_listener(
                                "skipped",
                                job,
                                get_job_count_tuple(),
                            )
                            backlog.remove(job)
                            continue

                        if manage_work_channel_add(job):
                            # Job got deferred; continue to the next job
                            continue

                        # Run in-process
                        if job.action.scheduling_type == "in-process":
                            self.job_status_listener(
                                "running",
                                job,
                                get_job_count_tuple(),
                            )
                            job.status = job.action.command(job.action)

                            manage_work_channel_remove(job)

                            self.scheduler.job_finished(job)
                            self.job_status_listener(
                                "finished" if job.status.rc == 0 else "failed",
                                job,
                                get_job_count_tuple(),
                            )
                            backlog.remove(job)

                            continue

                        # Schedule job to be run on the worker processes
                        backlog.remove(job)
                        scheduled_jobs[job] = pool.submit(run_job, (job))

                call_status_listener()

                if len(scheduled_jobs) == 0:
                    continue

                completed_jobs, _ = wait(
                    scheduled_jobs.values(), timeout=0.1, return_when="FIRST_COMPLETED"
                )
                for future in completed_jobs:
                    job_result = future.result()
                    assert isinstance(job_result, Job)
                    del scheduled_jobs[job_result]

                    self.check_for_missing_output_files(job_result)

                    manage_work_channel_remove(job_result)

                    self.scheduler.job_finished(job_result)
                    if job_result.status is not None and job_result.status.rc == 0:
                        if job_result.status.runner_instruction:
                            exit_reasons.append(job_result)
                        self.job_status_listener(
                            "finished",
                            job_result,
                            get_job_count_tuple(),
                        )
                    else:
                        self.failed_jobs.append(job_result)
                        self.job_status_listener(
                            "failed",
                            job_result,
                            get_job_count_tuple(),
                        )
                        call_status_listener()
                        exit_reasons.append(job_result)

    def check_for_missing_output_files(self, job: Job):
        missing_files: list[str | Path] = []
        for filename in job.action.outputs:
            if not os.path.exists(filename):
                missing_files.append(filename)
        if missing_files:
            on_check_failed(
                "output_file_missing",
                job.action,
                f"Job {TS.BOLD}{job.name}{TS.RESET} didn't create the output file{'s' if len(missing_files) > 1 else ''} that it declared: {TS.BOLD}{', '.join([str(missing_file) for missing_file in missing_files])}{TS.RESET}",
                "error",
            )


def run_job(job: Job):
    try:
        if job.action.command is None:
            job.status = CommandStatus(0, "No command, skipping", None)
        else:
            job.status = job.action.command(job.action)
    except Exception as e:
        job.status = CommandStatus(1, "Job failed with exception.", f"{e}")
    return job


def get_job_count_limit():
    if sys.version_info >= (3, 13):
        return os.process_cpu_count() or 1
    try:
        # Use os.sched_getaffinity where available (on U**X):
        # https://stackoverflow.com/a/55423170
        return len(os.sched_getaffinity(0))
    except AttributeError:
        count = os.cpu_count()
        assert count is not None
        return count
