import os
import shutil

from bygg.core.action import ActionContext, action_set
from bygg.core.common_types import CommandStatus

static_file_pairs = [
    ("files/a.txt", "files/out/a.txt"),
    ("files/b.txt", "files/out/b.txt"),
    ("files/c.txt", "files/out/c.txt"),
]


@action_set(
    "testfiles_static",
    message="Transforming file",
    file_pairs=static_file_pairs,
    is_entrypoint=True,
    description="Transforms a file to another file (testcase for action_set)",
)
def transform_testfile(ctx: ActionContext):
    if not ctx.inputs or not ctx.outputs:
        return CommandStatus(1, "No inputs or outputs.", None)
    for input_file, output_file in zip(ctx.inputs, ctx.outputs):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        shutil.copy(input_file, output_file)
    return CommandStatus(0, f"{ctx.inputs} -> {ctx.outputs}", None)
