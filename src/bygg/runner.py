import os
import signal
from typing import Callable, List, Literal

import multiprocess.managers  # type: ignore
from multiprocess.pool import ApplyResult, Pool  # type: ignore

from bygg.action import Action, CommandStatus
from bygg.scheduler import Job, scheduler

JobStatus = Literal["queued", "running", "finished", "failed", "stopped", "skipped"]
JobStatusListener = Callable[[str, JobStatus, Action, CommandStatus | None], None]
RunnerStatusListener = Callable[[str], None]


class ProcessRunner:
    job_status_listener: JobStatusListener
    runner_status_listener: RunnerStatusListener

    def __init__(self):
        self.job_status_listener = lambda *args: None
        self.runner_status_listener = lambda *args: None

    def start(self, max_workers: int = 1) -> bool:
        self.runner_status_listener(
            f"[blue]Starting process runner with {max_workers} threads"
        )

        def init_worker():
            """Ignore CTRL+C in the worker process."""
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        with Pool(max_workers, init_worker) as pool:
            scheduled_queue: List[ApplyResult] = []
            backlog: List[Job] = []

            manager = multiprocess.managers.SyncManager()
            manager.start()
            qq = manager.Queue()  # type: ignore # no/bad multiprocess types

            def poll_msg_queue():
                while not qq.empty():
                    msg, job_msg = qq.get_nowait()
                    self.job_status_listener(
                        job_msg.name, "running", job_msg.action, None
                    )

            while True:
                if len(backlog) < 2 * max_workers and (
                    jobs := scheduler.get_ready_jobs()
                ):
                    backlog += jobs

                if (
                    len(scheduled_queue) == 0
                    and len(backlog) == 0
                    and scheduler.run_status() == "finished"
                ):
                    return True

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
                            scheduler.job_finished(job)
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
                            scheduler.job_finished(job)
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
                    job_result = queued_job.get()
                    missing_files = self.check_for_missing_output_files(job_result)
                    if missing_files:
                        # TODO This should be a job status, not a runner status
                        self.runner_status_listener(
                            f"[red]Job [bold]{job_result.name}[/bold] didn't create the output file{'s' if len(missing_files) > 1 else ''} that it declared: [bold]{', '.join(missing_files)}"
                        )

                    scheduler.job_finished(job_result)
                    if job_result.status.rc == 0:
                        self.job_status_listener(
                            job_result.name,
                            "finished",
                            job_result.action,
                            job_result.status,
                        )
                    else:
                        self.job_status_listener(
                            job_result.name,
                            "failed",
                            job_result.action,
                            job_result.status,
                        )
                        self.runner_status_listener("Aborting.")
                        poll_msg_queue()
                        return False

    def check_for_missing_output_files(self, job: Job) -> List[str]:
        missing_files: List[str] = []
        for filename in job.action.outputs:
            if not os.path.exists(filename):
                missing_files.append(filename)
        return missing_files


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


# runner = SingleThreadedRunner()
runner = ProcessRunner()
