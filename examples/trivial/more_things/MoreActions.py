from bygg.action import ActionContext, action
from bygg.types import CommandStatus


@action("testfile 2", message="testfile 2", outputs=["output2.txt"])
def write_foo_to_file(ctx: ActionContext):
    for filename in ctx.outputs:
        with open(filename, "w") as f:
            f.write("foo")
    return CommandStatus(0, "Wrote foo to file.", None)


@action("foo", message="foo", outputs={"foo.txt"})
def foo(ctx: ActionContext):
    print("foo called")
    print(ctx.message)
    return CommandStatus(0, "foo", None)
