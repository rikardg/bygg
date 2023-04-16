import os
from pathlib import Path

from bygg.action import Action, ActionContext
from bygg.types import CommandStatus
import more_things.MoreActions  # noqa: F401 (imported for side effects)
from more_things.MoreActions import action


@action(
    "testfile 1",
    inputs=["input1.txt"],
    outputs=["output1.txt"],
)
def transform_uppercase(ctx: ActionContext):
    print(f"Transforming: {ctx.inputs} -> {ctx.outputs}")
    if not ctx.inputs or not ctx.outputs:
        return CommandStatus(1, "No inputs or outputs.", None)

    for input_file in ctx.inputs:
        with open(input_file) as f:
            lines = f.readlines()
        p = Path(input_file)
        output_file = p.parent / p.name.replace("input", "output")

        with open(output_file, "w") as f:
            for line in lines:
                f.write(line.upper())

        return CommandStatus(0, "Transformed file.", None)

    return CommandStatus(1, "Something went wrong.", None)


@action(
    "dynamic",
    dynamic_dependency=lambda: f"{os.environ.get('DEBUG', 'False')}",
)
def dynamic_test(ctx: ActionContext):
    return CommandStatus(0, "Ran dynamic dependency action.", None)


Action(
    "transform",
    dependencies=["testfile 1", "testfile 2", "foo", "dynamic"],
    is_entrypoint=True,
)
