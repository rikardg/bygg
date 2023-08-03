from bygg.action import Action, ActionContext
from bygg.common_types import CommandStatus


def hello(ctx: ActionContext):
    print("Hello")
    return CommandStatus(0, "And goodbye.", None)


Action("hello", command=hello, is_entrypoint=True)
