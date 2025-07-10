from dataclasses import dataclass
from typing import Literal

RunnerInstruction = Literal["restart_build", "exit_job_failed"]


@dataclass
class CommandStatus:
    """The status of a command."""

    rc: int  # return code; follows shell conventions where 0 is success
    message: str | None = None  # a message to display to the user
    output: str | None = None  # output of the command
    runner_instruction: RunnerInstruction | None = None  # instruction to the runner


JobStatus = Literal["queued", "running", "finished", "failed", "stopped", "skipped"]

Severity = Literal["error", "warning", "info"]
