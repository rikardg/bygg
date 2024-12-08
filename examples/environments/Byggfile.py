import rich

from bygg.core.action import ActionContext, action
from bygg.core.common_types import CommandStatus


@action("default_action_python")
def example_action(ctx: ActionContext):
    rich.print("[magenta]Running default action from Python.[/magenta]")
    return CommandStatus(0, "All ok.", None)
