from dataclasses import dataclass
from typing import Literal


@dataclass
class CommandStatus:
    """The status of a command."""

    rc: int  # return code; follows shell conventions where 0 is success
    message: str | None  # a message to display to the user
    output: str | None  # output of the command


JobStatus = Literal["queued", "running", "finished", "failed", "stopped", "skipped"]

Severity = Literal["error", "warning", "info"]
