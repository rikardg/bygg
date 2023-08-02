from bygg.action import ActionContext, action
from bygg.common_types import CommandStatus
import rich


@action("action1_python")
def example_action(ctx: ActionContext):
    rich.print("[magenta]Running default action from Python.[/magenta]")
    return CommandStatus(0, "All ok.", None)
