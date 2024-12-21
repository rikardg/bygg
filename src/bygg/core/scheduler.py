from pathlib import Path
from typing import Literal

from bygg.core.action import Action, CommandStatus
from bygg.core.cache import Cache
from bygg.core.dag import Dag, create_dag
from bygg.core.digest import calculate_dependency_digest, calculate_digest
from bygg.logging import logger
from bygg.output.status_display import on_check_failed


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


class Scheduler:
    cache: Cache
    build_actions: dict[str, Action]

    job_graph: Dag
    dirty_jobs: set[str]
    ready_jobs: set[str]
    running_jobs: dict[str, Job]
    finished_jobs: dict[str, Job]

    started: bool
    always_make: bool
    check_inputs_outputs_set: set[str] | None

    def __init__(self):
        Action.scheduler = self
        self.cache = Cache()
        self.build_actions = {}
        self.job_graph = create_dag()
        self.dirty_jobs = set()
        self.ready_jobs = set()
        self.running_jobs = {}
        self.finished_jobs = {}
        self.started = False
        self.always_make = False
        self.check_inputs_outputs_set = None

    def init_cache(self, cache_file: Path):
        self.cache = Cache(cache_file)

    def prepare_run(self, entrypoint: str, check=False):
        self.job_graph.clear()
        self.ready_jobs = set()
        self.running_jobs = {}
        self.finished_jobs = {}

        self.job_graph.build_action_graph(
            self.build_actions, self.build_actions[entrypoint]
        )

        if check:
            # Do this check before dependency files are filled in from dependencies
            files_with_several_actions = {
                f: a
                for f, a in self.create_outputs_to_action_dict().items()
                if len(a) > 1
            }
            for f, a in files_with_several_actions.items():
                scapegoat = list(a)[0]
                on_check_failed(
                    "same_output_files",
                    self.build_actions[scapegoat],
                    f"The file {f} is in the output list from multiple actions: {', '.join(a)}",
                    "error",
                )

        # Fill the actions' dependency_files from self and their dependencies
        for action in self.build_actions.values():
            action.dependency_files.update(action.inputs)
            for dependency in action.dependencies:
                action.dependency_files.update(self.build_actions[dependency].outputs)
            # print(f"Action {action.name} inputs: {action._dependency_files}")

    def start_run(
        self, entrypoint: str, *, always_make: bool = False, check: bool = False
    ):
        self.always_make = always_make
        self.check_inputs_outputs_set = set() if check else None
        self.prepare_run(entrypoint, check)
        self.cache.load()
        self.started = True

    def create_outputs_to_action_dict(self):
        """Create a dictionary of outputs to actions"""
        res: dict[str, set[str]] = {}
        for job in self.job_graph.get_all_jobs():
            action = self.build_actions[job]
            for output in action.outputs:
                if output not in res:
                    res[output] = set()
                res[output].add(action.name)
        return res

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
            len(action.inputs) == 0
            and len(action.outputs) == 0
            and not action.dynamic_dependency
        ):
            # An action with neither inputs nor outputs will always be built
            logger.debug("Job '%s' is dirty (no inputs or outputs)", job_name)
            return True

        if (
            not cached_digests
            or not cached_digests.outputs_digest
            or not cached_digests.inputs_digest
        ):
            # No previous result, so we need to build
            logger.debug("Job '%s' is dirty (no previous result)", job_name)
            return True

        outputs_digest, files_were_missing = calculate_dependency_digest(action.outputs)
        if files_were_missing or cached_digests.outputs_digest != outputs_digest:
            # The output has changed, so we need to rebuild
            logger.debug("Job '%s' is dirty (output changed)", job_name)
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
                logger.debug("Job '%s' is dirty (dynamic dependency changed)", job_name)
                return True

        # TODO handle files_were_missing here? abort?
        if cached_digests.inputs_digest != inputs_digest:
            # The inputs have changed, so we need to rebuild
            logger.debug("Job '%s' is dirty (inputs changed)", job_name)
            return True

        logger.debug("Job '%s' is clean", job_name)
        return False

    def get_ready_jobs(self, batch_size: int = 0) -> list[Job]:
        """
        Create a batch of jobs and put them in the running pool. Returns all ready jobs
        if batch_size is 0.

        An empty job list may be returned even if there are more jobs left to run if all
        jobs in the batch were skipped. Job runners should continue polling for more
        jobs until the scheduler status is "finished".
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

        job_list: list[Job] = []
        for _ in range(
            len(self.ready_jobs)
            if batch_size == 0
            else min(batch_size, len(self.ready_jobs))
        ):
            action = self.build_actions[self.ready_jobs.pop()]
            new_job = Job(action)
            self.running_jobs[new_job.name] = new_job
            job_list.append(new_job)

        if self.check_inputs_outputs_set is not None:
            # Check that no job has outputs that are inputs to an earlier job
            self.check_inputs_outputs_set.update(
                *[job.action.inputs for job in job_list],
                *[job.action.dependency_files for job in job_list],
            )
            for job_to_check in job_list:
                overlap = job_to_check.action.outputs & self.check_inputs_outputs_set
                if overlap:
                    plural = len(overlap) > 1
                    on_check_failed(
                        "check_inputs_outputs",
                        job_to_check.action,
                        f"Output{'s' if plural else ''} was declared as input{'s' if plural else ''} to earlier action: {', '.join(overlap)}",
                        "error",
                    )

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
