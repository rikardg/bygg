from pathlib import Path
import time

from bygg.core.action import ActionContext, action
from bygg.core.common_types import CommandStatus


# Simulate e.g. fetching variables from a CI system. Doing it twice is not a practical
# use case, but works for testing.
@action(
    name="restart_once",
    is_entrypoint=True,
    outputs=["restart_status.txt"],
    dynamic_dependency=lambda: str(time.time()),
)
def restart_once(ctx: ActionContext):
    indicator_file = Path("restart_status.txt")
    if indicator_file.exists():
        with indicator_file.open("r", encoding="utf-8") as f:
            content = f.read()
        if content == "1":
            with indicator_file.open("w", encoding="utf-8") as f:
                content = f.write("2")
            return CommandStatus(0, "Restarting 1", None, "restart_build")
        if content == "2":
            return CommandStatus(0, "Proceeding, was up-to-date", None)
    else:
        with indicator_file.open("w", encoding="utf-8") as f:
            content = f.write("1")
    return CommandStatus(0, "Restarting", None, "restart_build")


@action(name="another_action", inputs=["has_run_once.txt"])
def another_action(ctx: ActionContext):
    return CommandStatus(0, "Finished", None)
