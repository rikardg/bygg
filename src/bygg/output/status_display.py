from dataclasses import dataclass
import shutil
from typing import Literal

from bygg.cmd.argument_parsing import ByggNamespace
from bygg.cmd.configuration import Byggfile
from bygg.core.action import Action
from bygg.core.common_types import JobStatus, Severity
from bygg.core.job import Job
from bygg.output.job_output import format_job_log
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


def format_queued_jobs_line(prefix: str) -> str:
    terminal_cols, _ = shutil.get_terminal_size()
    output = f"{prefix} {' '.join(running_jobs)}"
    if len(output) > terminal_cols:
        output = output[: terminal_cols - 3] + "..."
    return output


def format_result_status(status: JobStatus, field_width: int) -> str:
    match status:
        case "failed":
            return f"{TS.BOLD}{TS.Fg.GREEN}{'FAILED':>{field_width}}{TS.Fg.RESET}{TS.NOBOLD}"
        case "stopped":
            return f"{TS.BOLD}{TS.Fg.GREEN}{'STOPPED':>{field_width}}{TS.Fg.RESET}{TS.NOBOLD}"
        case "finished":
            return (
                f"{TS.BOLD}{TS.Fg.GREEN}{'OK':>{field_width}}{TS.Fg.RESET}{TS.NOBOLD}"
            )
        case _:
            return (
                f"{TS.BOLD}{TS.Fg.BLUE}{'OTHER':>{field_width}}{TS.Fg.RESET}{TS.NOBOLD}"
            )


max_name_length = 0


def get_on_job_status(args: ByggNamespace, configuration: Byggfile):
    def on_job_status(job_status: JobStatus, job: Job, jobs_count: tuple[int, int]):
        match job_status:
            case "skipped":
                pass
            case "running":
                running_jobs.add(job.name)
            case "failed" | "finished" | "stopped":
                running_jobs.discard(job.name)
                print_job_ended(job_status, job, jobs_count)
            case _:
                raise ValueError(f"Unhandled job status {job_status}")

    def print_job_ended(job_status: JobStatus, job: Job, jobs_count: tuple[int, int]):
        global max_name_length
        max_name_length = max(len(job.name), max_name_length)
        status_code_message = f"[{job.status.rc}] " if job.status else "?"
        status_message = job.status.message if job.status and job.status.message else ""
        message_part = f"{status_code_message if job.status and job.status.rc else ''}{status_message}"

        total_job_count_length = len(str(jobs_count[1]))
        job_count_info = f" ({jobs_count[0]:>{total_job_count_length}}/{jobs_count[1]})"

        if args.verbose or configuration.settings.verbose:
            result_status = format_result_status(job_status, 0)
            formatted_log = format_job_log(job)
            log = f"\n{formatted_log}" if formatted_log else ""
            output_with_status_line(
                format_queued_jobs_line(job_count_info),
                f"{result_status} {job.name}{(' : ' + message_part) if len(message_part) > 0 else ''}{log}",
            )
        else:
            result_status = format_result_status(job_status, STATUS_TEXT_FIELD_WIDTH)
            output_with_status_line(
                format_queued_jobs_line(job_count_info),
                f"{result_status} {job.name:<{max_name_length}}{(' : ' + message_part) if len(message_part) > 0 else ''}",
            )

    return on_job_status


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
