import rich

from bygg.core.action import ActionContext, action
from bygg.core.common_types import CommandStatus


@action("action1_python")
def example_action(ctx: ActionContext):
    rich.print("[magenta]Running default action from Python.[/magenta]")
    return CommandStatus(0, "All ok.", None)


@action("action1_python_entrypoint_python", is_entrypoint=True)
def example_action_entrypoint(ctx: ActionContext):
    """An entrypoint action declared in Python."""
    rich.print("[magenta]Running entrypoint action from Python.[/magenta]")
    return CommandStatus(0, "All ok.", None)
