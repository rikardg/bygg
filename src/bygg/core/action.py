from dataclasses import dataclass
from pathlib import Path

# import inspect
from typing import TYPE_CHECKING, Callable, Iterable, Literal, Optional, Protocol, Self

from bygg.core.common_types import CommandStatus
from bygg.logutils import logger

if TYPE_CHECKING:
    from bygg.core.scheduler import Scheduler

SchedulingType = Literal["in-process", "processpool"]

# Function that returns a string that is included in the dependency digest. Returning
# None causes the value to be ignored.
DynamicDependency = Callable[[], str | None]


class WorkChannel:
    """A WorkChannel is a semaphore that limits the number of concurrent jobs. Create an
    instance with a unique name and a job limit, then assign it to the Action objects
    that should be limited by it."""

    name: str
    width: int
    current_jobs: set[str]

    def __init__(self, name: str, width: int = 1):
        self.name = name
        self.width = width
        assert self.width > 0, "Work channel width less than 1 makes no sense"
        self.current_jobs = set()


class DynamicTrim(Protocol):
    """Return file paths to trim"""

    def __call__(self) -> Iterable[str]:
        """Return file paths to trim."""
        ...


@dataclass
class ActionContext:
    name: str
    message: str | None
    inputs: set[str]
    outputs: set[str]
    dependencies: set[str]
    dynamic_dependency: Optional[DynamicDependency]
    trim: Optional[Iterable[str] | DynamicTrim]
    is_entrypoint: bool
    scheduling_type: SchedulingType


Command = Callable[[ActionContext], CommandStatus]


class Action(ActionContext):
    """
    An action in the build graph.

    Parameters
    ----------
    name : str
        The name of the action.
    message : str, optional
        A message to display when the action is run. Default is None.
    inputs : Iterable[str], optional
        An iterable of paths that are inputs to the action. Default is None.
    outputs : Iterable[str], optional
        An iterable of paths that are outputs of the action. Default is None.
    dependencies : Iterable[str], optional
        An iterable of action names that this action depends on. Default is None.
    dynamic_dependency : DynamicDependency, optional
        A dynamic dependency of the action. Default is None.
    trim : Iterable[str] | DynamicTrim, optional
        The purpose of trim_globs is to be able to remove files that should no longer
        exist, e.g. because they belong to a previous configuration of the source tree.
        - Trimming will be performed before the action has run.
        - The list of outputs from all the action's dependencies will be collected and
          subtracted from the file list of the evaluated trim list.
        - Directories that contain such output files will also be subtracted.
        - Paths will be normalised using os.path.normpath before comparison.
        - Any files or directories that remain will be deleted.
        See utils.py for utility functions for git controlled files.
    is_entrypoint : bool, optional
        Whether this action is an entrypoint to the build graph. Default is False.
    command : Command, optional
        Function to run. Default is None.
    scheduling_type : SchedulingType, optional
        The scheduling type for the action. Default is "processpool". Use "in-process"
        for small Python functions that finish quickly so that they can be run in the
        main process.
    work_channel: WorkChannel, optional
        A WorkChannel that the action should run in. Default is None.
    description : str, optional
        A description of the action. Default is the docstring of the command if
        provided, else None.
    """

    # Set when Scheduler is initialised. Quotes around the type because of circular
    # import shenanigans.
    scheduler: "Scheduler | None" = None
    _current_environment: str | None = None

    command: Command | None
    dependency_files: set[str]

    def __init__(
        self,
        name: str,
        message: str | None = None,
        inputs: Optional[Iterable[str | Path]] = None,
        outputs: Optional[Iterable[str | Path]] = None,
        dependencies: Optional[Iterable[str | Self]] = None,
        dynamic_dependency: Optional[DynamicDependency] = None,
        trim: Optional[Iterable[str] | DynamicTrim] = None,
        is_entrypoint: bool = False,
        command: Command | None = None,
        scheduling_type: SchedulingType = "processpool",
        work_channel: Optional[WorkChannel] = None,
        description: str | None = None,
        environment: Optional[str] = None,
    ):
        self.name = name
        self.message = message
        self.inputs = {str(i) for i in inputs} if inputs else set()
        self.outputs = {str(o) for o in outputs} if outputs else set()
        self.dependencies = {
            d.name if isinstance(d, Action) else d for d in (dependencies or [])
        }
        self.dynamic_dependency = dynamic_dependency
        self.trim = trim
        self.is_entrypoint = is_entrypoint
        self.command = command
        self.scheduling_type = scheduling_type
        self.work_channel = work_channel

        self.description = (
            description.strip()
            if description is not None
            else command.__doc__
            if command is not None and command.__doc__ is not None
            else None
        )

        self.environment = environment or Action._current_environment
        assert self.environment
        logger.info("Constructing Action for environment %s", self.environment)

        self.dependency_files = set()

        assert self.scheduler
        self.scheduler.build_actions[name] = self

    def __repr__(self):
        return f"""Action(name={self.name}, inputs=({
            ", ".join([str(i) for i in self.inputs])
        }), outputs=({", ".join([str(o) for o in self.outputs])}), dependencies=({
            ", ".join(self.dependencies)
        }) is_entrypoint={self.is_entrypoint})"""

    def __str__(self):
        return self.__repr__()


def action(
    name: str,
    *,
    message: Optional[str] = None,
    inputs: Optional[Iterable[str | Path]] = None,
    outputs: Optional[Iterable[str | Path]] = None,
    dependencies: Optional[Iterable[str | Action]] = None,
    dynamic_dependency: Optional[DynamicDependency] = None,
    trim: Optional[Callable[[], Iterable[str]]] = None,
    scheduling_type: SchedulingType = "processpool",
    work_channel: Optional[WorkChannel] = None,
    is_entrypoint: bool = False,
):
    """Decorator to define a Bygg action.

    Wraps the decorated function in an Action instance.

    Parameters
    ----------
    name : str
        The name of the action
    message : str, optional
        A message to display when the action is run, by default None
    inputs : Iterable[str], optional
        An iterable of input files, by default None
    outputs : Iterable[str], optional
        An iterable of output files, by default None
    dependencies : Iterable[str], optional
        An iterable of dependency actions, by default None
    dynamic_dependency : DynamicDependency, optional
        A dynamic dependency, by default None
    trim : Iterable[str] | DynamicTrim, optional
        The purpose of trim_globs is to be able to remove files that should no longer
        exist, e.g. because they belong to a previous configuration of the source tree.
        - Trimming will be performed before the action has run.
        - The list of outputs from all the action's dependencies will be collected and
          subtracted from the file list of the evaluated trim list.
        - Directories that contain such output files will also be subtracted.
        - Paths will be normalised using os.path.normpath before comparison.
        - Any files or directories that remain will be deleted.
        See utils.py for utility functions for git controlled files.
    is_entrypoint : bool, optional
        Whether the action is an entrypoint, by default False
    scheduling_type : SchedulingType, optional
        The scheduling type for the action. Default is "processpool". Use "in-process"
        for small Python functions that finish quickly so that they can be run in the
        main process.
    description : str, optional
        A description of the action, by default None

    Returns
    -------
    Callable[[Callable], Action]
        A decorator that converts the decorated function into an Action
    """

    def create_action(func: Callable):
        return Action(
            name,
            message=message,
            inputs=inputs,
            outputs=outputs,
            dependencies=dependencies,
            dynamic_dependency=dynamic_dependency,
            trim=trim,
            is_entrypoint=is_entrypoint,
            scheduling_type=scheduling_type,
            work_channel=work_channel,
            command=func,
        )

    return create_action
