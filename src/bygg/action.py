from dataclasses import dataclass
from typing import Callable, Iterable, Literal, Optional, Set, Tuple

from bygg.types import CommandStatus

SchedulingType = Literal["in-process", "processpool"]

# Function that returns a string that is included in the dependency digest. Returning
# None causes the value to be ignored.
DynamicDependency = Callable[[], str | None]


@dataclass
class ActionContext:
    name: str
    message: str | None
    inputs: Set[str]
    outputs: Set[str]
    dependencies: Set[str]
    dynamic_dependency: Optional[DynamicDependency]
    is_entrypoint: bool
    scheduling_type: SchedulingType


Command = Callable[
    [ActionContext],
    CommandStatus,
]


class Action(ActionContext):
    """
    An action in the build graph.

    name: The name of the action.
    message (optional): A message to display when the action is run.
    inputs (optional): A list of paths that are inputs to the action.
    outputs (optional): A list of paths that are outputs of the action.
    dependencies (optional): A list of action names that this action depends on.
    is_entrypoint (optional): Whether this action is an entrypoint to the build graph.
    command (optional): Instance of one of the Command types to run.

    """

    command: Command | None
    dependency_files: Set[str]

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
    ):
        from bygg.scheduler import scheduler

        self.name = name
        self.message = message
        self.inputs = {*inputs} if inputs else set()
        self.outputs = {*outputs} if outputs else set()
        self.dependencies = {*dependencies} if dependencies else set()
        self.dynamic_dependency = dynamic_dependency
        self.is_entrypoint = is_entrypoint
        self.command = command
        self.scheduling_type = scheduling_type

        self.dependency_files = set()

        scheduler.build_actions[name] = self

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
    is_entrypoint: bool = False,
):
    """Decorator for creating an Action from a function."""

    def create_action(func: Callable):
        Action(
            name,
            message,
            inputs=inputs,
            outputs=outputs,
            dependencies=dependencies,
            dynamic_dependency=dynamic_dependency,
            is_entrypoint=is_entrypoint,
            command=func,
        )

    return create_action


def action_set(
    base_name: str,
    *,
    message: Optional[str] = None,
    file_pairs: Iterable[Tuple[str, str]],
    dependencies: Optional[Iterable[str]] = None,
    is_entrypoint: bool = False,
):
    """
    Decorator for creating individual Actions from a list of input-output file pairs and
    a function. Creates one Action that depends on all of the individual Actions. It has
    name = base_name, which in turn can be used as a dependency for other Actions.
    """

    def create_actions(func: Callable):
        action_list = []
        for input_file, output_file in file_pairs:
            action_name = f"{base_name}_{output_file}"
            action_list.append(action_name)
            Action(
                action_name,
                message,
                inputs=[input_file],
                outputs=[output_file],
                dependencies=dependencies,
                is_entrypoint=is_entrypoint,
                command=func,
            )
        Action(base_name, f"Action set {base_name}", dependencies=action_list)

    return create_actions
