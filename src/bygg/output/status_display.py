from dataclasses import dataclass
import shutil
from typing import Literal

from bygg.core.action import Action
from bygg.core.common_types import CommandStatus, JobStatus, Severity
from bygg.output.output import (
    STATUS_TEXT_FIELD_WIDTH,
    output_error,
    output_info,
    output_warning,
    output_with_status_line,
)
from bygg.output.output import (
    TerminalStyle as TS,
)


def on_runner_status(message: str):
    output_info(message)


running_jobs: set[str] = set()


def format_queued_jobs_line() -> str:
    terminal_cols, _ = shutil.get_terminal_size()
    output = f"{' '.join(running_jobs)}"
    if len(output) > terminal_cols:
        output = output[: terminal_cols - 3] + "..."
    return output


def format_result_status(
    status: JobStatus,
) -> str:
    match status:
        case "failed":
            return f"{TS.BOLD}{TS.Fg.GREEN}{'FAILED':>{STATUS_TEXT_FIELD_WIDTH}}{TS.Fg.RESET}{TS.NOBOLD}"
        case "stopped":
            return f"{TS.BOLD}{TS.Fg.GREEN}{'STOPPED':>{STATUS_TEXT_FIELD_WIDTH}}{TS.Fg.RESET}{TS.NOBOLD}"
        case "finished":
            return f"{TS.BOLD}{TS.Fg.GREEN}{'OK':>{STATUS_TEXT_FIELD_WIDTH}}{TS.Fg.RESET}{TS.NOBOLD}"
        case _:
            return f"{TS.BOLD}{TS.Fg.BLUE}{'OTHER':>{STATUS_TEXT_FIELD_WIDTH}}{TS.Fg.RESET}{TS.NOBOLD}"


max_name_length = 0


def print_job_ended(
    name: str, job_status: JobStatus, action: Action, status: CommandStatus | None
):
    global max_name_length
    max_name_length = max(len(name), max_name_length)
    result_status = format_result_status(job_status)
    status_code_message = f"[{status.rc}] " if status else "?"
    status_message = status.message if status and status.message else ""
    message_part = (
        f"{status_code_message if status and status.rc else ''}{status_message}"
    )
    output_with_status_line(
        format_queued_jobs_line(),
        f"{result_status} {name:<{max_name_length}}{(' : ' + message_part) if len(message_part) > 0 else ''}",
    )


def on_job_status(
    name: str, job_status: JobStatus, action: Action, status: CommandStatus | None
):
    match job_status:
        case "skipped":
            pass
        case "running":
            running_jobs.add(name)
        case "failed" | "finished" | "stopped":
            running_jobs.discard(name)
            print_job_ended(name, job_status, action, status)
        case _:
            raise ValueError(f"Unhandled job status {job_status}")


CheckRule = Literal["check_inputs_outputs", "output_file_missing", "same_output_files"]
"""
The different rules that can be checked.

    check_inputs_outputs: Check that earlier actions don't need outputs from subsequent
    actions.

    output_file_missing: Check that actions create the files that they declare as
    outputs.

    same_output_files: Check that different actions don't produce the same output files.
"""


@dataclass
class CheckStatus:
    rule_name: CheckRule
    action: Action
    status_text: str
    severity: Severity


failed_checks: list[CheckStatus] = []


def on_check_failed(
    rule_name: CheckRule, action: Action, status_text: str, severity: Severity
):
    failed_checks.append(CheckStatus(rule_name, action, status_text, severity))


def output_check_results():
    status = True
    output_error("The following checks reported issues:")
    for c in failed_checks:
        compound_status = f"{c.rule_name} :: {c.action.name} :: {c.status_text}"
        match c.severity:
            case "error":
                status = False
                output_error(compound_status)
            case "warning":
                status = False
                output_warning(compound_status)
            case "info":
                continue
            case _:
                raise ValueError(f"Unhandled severity {c.severity}")

    return status
