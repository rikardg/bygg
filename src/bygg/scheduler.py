from pathlib import Path
from typing import Dict, List, Literal, Set

import msgspec

from bygg.action import Action, CommandStatus
from bygg.cache import Cache
from bygg.dag import Dag, create_dag
from bygg.digest import calculate_dependency_digest, calculate_digest


class Job:
    name: str
    action: Action
    status: CommandStatus | None

    def __init__(self, action: Action):
        self.name = action.name
        self.action = action
        self.status = None

    def __repr__(self) -> str:
        return f'"{self.name}, status: {self.status.rc if self.status else "unknown"}"'

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return self.name

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Job) and self.name == __o.name


class ActionDigestItem(msgspec.Struct):
    inputs_digest: str
    outputs_digest: str


class Scheduler:
    cache: Cache
    build_actions: Dict[str, Action]

    job_graph: Dag
    dirty_jobs: Set[str]
    ready_jobs: Set[str]
    running_jobs: Dict[str, Job]
    finished_jobs: Dict[str, Job]

    started: bool
    always_make: bool

    def __init__(self):
        self.cache = Cache()
        self.build_actions = {}
        self.job_graph = create_dag()
        self.dirty_jobs = set()
        self.ready_jobs = set()
        self.running_jobs = {}
        self.finished_jobs = {}
        self.started = False
        self.always_make = False

    def init_cache(self, cache_file: Path):
        self.cache = Cache(cache_file)

    def prepare_run(self, entrypoint: str):
        self.job_graph.clear()
        self.ready_jobs = set()
        self.running_jobs = {}
        self.finished_jobs = {}

        self.job_graph.build_action_graph(
            self.build_actions, self.build_actions[entrypoint]
        )

        # Fill the actions' _dependency_files from their dependencies
        for action in self.build_actions.values():
            for dependency in action.dependencies:
                action.dependency_files.update(self.build_actions[dependency].outputs)
            # print(f"Action {action.name} inputs: {action._dependency_files}")

    def start_run(self, entrypoint: str, *, always_make: bool = False):
        self.always_make = always_make
        self.prepare_run(entrypoint)
        self.cache.load()
        self.started = True

    def shutdown(self):
        self.cache.save()

    def run_status(self) -> Literal["not started", "running", "finished", "failed"]:
        """Check the status of the run"""
        if not self.started:
            return "not started"
        if (
            len(
                [
                    x
                    for x in self.finished_jobs.values()
                    if x.status is not None and x.status.rc != 0
                ]
            )
            > 0
        ):
            return "failed"
        if len(self.job_graph) == 0:
            return "finished"
        return "running"

    def check_dirty(self, job_name: str) -> bool:
        """Check if a job needs to be built."""
        if self.always_make:
            return True

        action = self.build_actions[job_name]
        cached_digests = self.cache.get_digests(job_name)

        if (
            not cached_digests
            or not cached_digests.outputs_digest
            or not cached_digests.inputs_digest
        ):
            # No previous result, so we need to build
            # print(f"Job {job_name} is dirty (no previous result)")
            return True

        outputs_digest, files_were_missing = calculate_dependency_digest(action.outputs)
        if files_were_missing or cached_digests.outputs_digest != outputs_digest:
            # The output has changed, so we need to rebuild
            # print(f"Job {job_name} is dirty (output changed)")
            return True

        inputs_digest, files_were_missing = calculate_dependency_digest(
            action.dependency_files
        )

        # Calculate dynamic dependencies
        if action.dynamic_dependency:
            if not cached_digests.dynamic_digest:
                return True

            dd_result = action.dynamic_dependency()
            if (
                dd_result is None
                or calculate_digest([dd_result]) != cached_digests.dynamic_digest
            ):
                return True

        # TODO handle files_were_missing here? abort?
        if cached_digests.inputs_digest != inputs_digest:
            # The inputs have changed, so we need to rebuild
            # print(f"Job {job_name} is dirty (inputs changed)")
            return True

        # print(f"Job {job_name} is clean")
        return False

    def get_ready_jobs(self, batch_size: int = 0) -> List[Job]:
        """
        Create a batch of jobs and put them in the running pool. Returns all ready jobs if
        batch_size is 0.
        """
        if batch_size == 0 or len(self.ready_jobs) < batch_size:
            new_jobs = self.job_graph.get_ready_jobs(
                self.finished_jobs, self.running_jobs
            )
            dirty_jobs = []
            for job in new_jobs:
                if self.check_dirty(job):
                    dirty_jobs.append(job)
                else:
                    self.skip_job(job)
            self.ready_jobs.update(dirty_jobs)

        if len(self.ready_jobs) == 0:
            return []

        job_list = []
        for _ in range(
            len(self.ready_jobs)
            if batch_size == 0
            else min(batch_size, len(self.ready_jobs))
        ):
            action = self.build_actions[self.ready_jobs.pop()]
            new_job = Job(action)
            self.running_jobs[new_job.name] = new_job
            job_list.append(new_job)

        return job_list

    def skip_job(self, job_name: str):
        """Skip a job, remove it from the graph and don't send it to the runner."""
        self.job_graph.remove_node(job_name)

    def job_finished(self, job: Job):
        """Move a job from the running pool to the finished pool"""
        self.running_jobs.pop(job.name)
        self.finished_jobs[job.name] = job

        if job.status and job.status.rc == 0:
            self.job_graph.remove_node(job.name)
            inputs_digest, _ = calculate_dependency_digest(job.action.dependency_files)
            outputs_digest, _ = calculate_dependency_digest(job.action.outputs)
            dynamic_digest = (
                calculate_digest([dd])
                if job.action.dynamic_dependency
                and (dd := job.action.dynamic_dependency())
                else None
            )

            self.cache.set_digests(
                job.name, inputs_digest, outputs_digest, dynamic_digest
            )
        else:
            self.cache.remove_digests(job.name)


scheduler = Scheduler()
