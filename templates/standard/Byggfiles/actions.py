from bygg.core.action import Action, ActionContext, action
from bygg.core.common_types import CommandStatus


@action("entrypoint_action_2", is_entrypoint=True)
def action2(ctx: ActionContext):
    """This is entrypoint action 2"""
    return CommandStatus(0, "Action successful.", None)


@action(
    "dependent_action",
    dependencies=["entrypoint_action_2"],
)
def dependent_action(ctx: ActionContext):
    """This is a dependent action"""
    return CommandStatus(0, "Dependent action successful.", None)


def constructor_action_cmd(ctx: ActionContext):
    """Do something constructive"""
    return CommandStatus(0, "Constructor action successful.", None)


Action("constructor_action", is_entrypoint=True, command=constructor_action_cmd)
