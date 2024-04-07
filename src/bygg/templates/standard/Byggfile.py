from bygg.core.action import ActionContext, action
from bygg.core.common_types import CommandStatus
import Byggfiles.actions  # noqa: F401 (imported for side effects)


@action("entrypoint_action_1", is_entrypoint=True)
def action1(ctx: ActionContext):
    """This is entrypoint action 1"""
    return CommandStatus(0, "Action successful.", None)
