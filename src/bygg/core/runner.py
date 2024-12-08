import os
import signal
from typing import Callable

import multiprocess.managers  # type: ignore
from multiprocess.pool import ApplyResult, Pool  # type: ignore

from bygg.core.action import Action, CommandStatus
from bygg.core.common_types import JobStatus
from bygg.core.scheduler import Job, Scheduler
from bygg.output.output import TerminalStyle as TS
from bygg.output.status_display import on_check_failed

JobStatusListener = Callable[[str, JobStatus, Action, CommandStatus | None], None]
RunnerStatusListener = Callable[[str], None]


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

    def start(self, max_workers: int = 1) -> bool:
        self.runner_status_listener(
            f"Starting process runner with {max_workers} threads"
        )

        def init_worker():
            """Ignore CTRL+C in the worker process."""
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        with Pool(max_workers, init_worker) as pool:
            scheduled_queue: list[ApplyResult] = []
            backlog: list[Job] = []

            manager = multiprocess.managers.SyncManager()
            manager.start()
            qq = manager.Queue()  # type: ignore # no/bad multiprocess types

            def poll_msg_queue():
                while not qq.empty():
                    msg, job_msg = qq.get_nowait()
                    self.job_status_listener(
                        job_msg.name, "running", job_msg.action, None
                    )

            # If a job fails, we want to stop scheduling new jobs and just wait for the
            # ones that are already running to finish.
            early_out = False

            while True:
                if (
                    not early_out
                    and len(backlog) < 2 * max_workers
                    and (jobs := self.scheduler.get_ready_jobs())
                ):
                    backlog += jobs

                if (
                    len(scheduled_queue) == 0
                    and len(backlog) == 0
                    and (self.scheduler.run_status() == "finished" or early_out)
                ):
                    return not early_out

                # Keep the scheduled queue relatively short since we're polling
                batch_size = max_workers * 2
                if len(scheduled_queue) < batch_size:
                    for job in backlog[:batch_size]:
                        # Skip jobs with no command or ones that are clean
                        if job.action.command is None:
                            job.status = CommandStatus(
                                0,
                                f"{'No command, skipping'}",
                                None,
                            )
                            self.scheduler.job_finished(job)
                            self.job_status_listener(
                                job.name, "skipped", job.action, job.status
                            )
                            backlog.remove(job)
                            continue

                        # Run in-process
                        if job.action.scheduling_type == "in-process":
                            self.job_status_listener(
                                job.name, "running", job.action, None
                            )
                            job.status = job.action.command(job.action)
                            self.scheduler.job_finished(job)
                            self.job_status_listener(
                                job.name,
                                "finished" if job.status.rc == 0 else "failed",
                                job.action,
                                job.status,
                            )
                            backlog.remove(job)
                            continue

                        # Schedule job to be run on the worker processes
                        backlog.remove(job)
                        scheduled_queue.append(pool.apply_async(run_job, (job, qq)))

                poll_msg_queue()

                if len(scheduled_queue) == 0:
                    continue

                queued_job = scheduled_queue.pop(0)
                queued_job.wait(0.1)
                if not queued_job.ready():
                    scheduled_queue.append(queued_job)  # add it back to the queue
                else:
                    job_result: Job = queued_job.get()
                    self.check_for_missing_output_files(job_result)

                    self.scheduler.job_finished(job_result)
                    if job_result.status is not None and job_result.status.rc == 0:
                        self.job_status_listener(
                            job_result.name,
                            "finished",
                            job_result.action,
                            job_result.status,
                        )
                    else:
                        self.failed_jobs.append(job_result)
                        self.job_status_listener(
                            job_result.name,
                            "failed",
                            job_result.action,
                            job_result.status,
                        )
                        poll_msg_queue()
                        early_out = True

    def check_for_missing_output_files(self, job: Job):
        missing_files: list[str] = []
        for filename in job.action.outputs:
            if not os.path.exists(filename):
                missing_files.append(filename)
        if missing_files:
            on_check_failed(
                "output_file_missing",
                job.action,
                f"Job {TS.BOLD}{job.name}{TS.RESET} didn't create the output file{'s' if len(missing_files) > 1 else ''} that it declared: {TS.BOLD}{', '.join(missing_files)}{TS.RESET}",
                "error",
            )


def run_job(job: Job, qq):
    qq.put_nowait(("START", job))
    try:
        if job.action.command is None:
            job.status = CommandStatus(0, "No command, skipping", None)
        else:
            job.status = job.action.command(job.action)
    except Exception as e:
        job.status = CommandStatus(1, "Job failed with exception.", f"{e}")
    return job


def get_job_count_limit():
    try:
        # Use os.sched_getaffinity where available (on U**X):
        # https://stackoverflow.com/a/55423170
        return len(os.sched_getaffinity(0))
    except AttributeError:
        count = os.cpu_count()
        assert count is not None
        return count
