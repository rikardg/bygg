from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterable, Literal, Optional

from bygg.core.common_types import CommandStatus

if TYPE_CHECKING:
    from bygg.core.scheduler import Scheduler

SchedulingType = Literal["in-process", "processpool"]

# Function that returns a string that is included in the dependency digest. Returning
# None causes the value to be ignored.
DynamicDependency = Callable[[], str | None]


@dataclass
class ActionContext:
    name: str
    message: str | None
    inputs: set[str]
    outputs: set[str]
    dependencies: set[str]
    dynamic_dependency: Optional[DynamicDependency]
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
    is_entrypoint : bool, optional
        Whether this action is an entrypoint to the build graph. Default is False.
    command : Command, optional
        Function to run. Default is None.
    scheduling_type : SchedulingType, optional
        The scheduling type for the action. Default is "processpool". Use "in-process"
        for small Python functions that finish quickly so that they can be run in the
        main process.
    description : str, optional
        A description of the action. Default is the docstring of the command if
        provided, else None.
    """

    scheduler: Scheduler | None = None

    command: Command | None
    dependency_files: set[str]

    def __init__(
        self,
        name: str,
        message: str | None = None,
        inputs: Optional[Iterable[str]] = None,
        outputs: Optional[Iterable[str]] = None,
        dependencies: Optional[Iterable[str]] = None,
        dynamic_dependency: Optional[DynamicDependency] = None,
        is_entrypoint: bool = False,
        command: Command | None = None,
        scheduling_type: SchedulingType = "processpool",
        description: str | None = None,
    ):
        self.name = name
        self.message = message
        self.inputs = {*inputs} if inputs else set()
        self.outputs = {*outputs} if outputs else set()
        self.dependencies = {*dependencies} if dependencies else set()
        self.dynamic_dependency = dynamic_dependency
        self.is_entrypoint = is_entrypoint
        self.command = command
        self.scheduling_type = scheduling_type

        self.description = (
            description
            if description is not None
            else command.__doc__
            if command is not None and command.__doc__ is not None
            else None
        )

        self.dependency_files = set()

        assert self.scheduler
        self.scheduler.build_actions[name] = self

    def __repr__(self):
        return f"""Action(name={self.name}, inputs=({
                ', '.join([str(i) for i in self.inputs])}), outputs=({
                ', '.join([str(o) for o in self.outputs])}), dependencies=({
                ', '.join(self.dependencies)}) is_entrypoint={
            self.is_entrypoint})"""

    def __str__(self):
        return self.__repr__()


def action(
    name: str,
    *,
    message: Optional[str] = None,
    inputs: Optional[Iterable[str]] = None,
    outputs: Optional[Iterable[str]] = None,
    dependencies: Optional[Iterable[str]] = None,
    dynamic_dependency: Optional[DynamicDependency] = None,
    scheduling_type: SchedulingType = "processpool",
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
        Action(
            name,
            message=message,
            inputs=inputs,
            outputs=outputs,
            dependencies=dependencies,
            dynamic_dependency=dynamic_dependency,
            is_entrypoint=is_entrypoint,
            scheduling_type=scheduling_type,
            command=func,
        )

    return create_action


def action_set(
    base_name: str,
    *,
    message: Optional[str] = None,
    file_pairs: Iterable[tuple[str, str]],
    extra_inputs: Optional[Iterable[str]] = None,
    dependencies: Optional[Iterable[str]] = None,
    is_entrypoint: bool = False,
    scheduling_type: SchedulingType = "processpool",
    description: str | None = None,
):
    """
    Decorator for creating individual Actions from a list of input-output file pairs and
    a function. Creates one Action that depends on all of the individual Actions. It has
    name = base_name, which in turn can be used as a dependency for other Actions.

    Parameters
    ----------
    base_name : str
        Base name to use for generated actions
    message : str, optional
        Message for actions, by default None
    file_pairs : Iterable[tuple[str, str]]
        Input and output file pairs
    extra_inputs : Iterable[str], optional
        Extra input files, by default None
    dependencies : Iterable[str], optional
        Dependencies for actions, by default None
    is_entrypoint : bool, optional
        Whether the top-most action should be an entrypoint, by default False
    scheduling_type : SchedulingType, optional
        The scheduling type for the action. Default is "processpool". Use "in-process"
        for small Python functions that finish quickly so that they can be run in the
        main process.
    description : str, optional
        A description of the action, by default None

    Returns
    -------
    Callable[[Callable], None]
        A decorator that registers actions constructed around the decorated function
    """

    def create_actions(func: Callable):
        action_list = []
        for input_file, output_file in file_pairs:
            action_name = f"{base_name}::{output_file}"
            action_list.append(action_name)
            Action(
                action_name,
                message,
                inputs=[input_file] + (list(extra_inputs) if extra_inputs else []),
                outputs=[output_file],
                dependencies=dependencies,
                scheduling_type=scheduling_type,
                command=func,
            )
        Action(
            base_name,
            f"Action set {base_name}",
            dependencies=action_list,
            is_entrypoint=is_entrypoint,
            scheduling_type=scheduling_type,
            description=description,
        )

    return create_actions
