from bygg.core.action import Action, ActionContext, action
from bygg.core.common_types import CommandStatus


def hello(ctx: ActionContext):
    """An action that says 'Hello'."""
    print("Hello")
    return CommandStatus(0, "And goodbye.", None)


Action("hello", command=hello, is_entrypoint=True)


@action("hi", is_entrypoint=True)
def hi(ctx: ActionContext):
    """An action that says 'Hi'."""
    print("Hi")
    return CommandStatus(0, "And goodbye.", None)
