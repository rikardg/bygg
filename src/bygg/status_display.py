from dataclasses import dataclass
from typing import List, Literal, Set

import rich
import rich.progress
import rich.table

from bygg.action import Action
from bygg.common_types import CommandStatus, JobStatus, Severity
from bygg.output import output_error, output_warning

console = rich.console.Console()

progress: rich.progress.Progress = rich.progress.Progress(
    rich.progress.SpinnerColumn(
        table_column=rich.table.Column(ratio=None),
        spinner_name="bouncingBar",
        style="blue",
    ),
    rich.progress.TimeElapsedColumn(table_column=rich.table.Column(ratio=None)),
    rich.progress.TextColumn(
        "[cyan]{task.description}",
        table_column=rich.table.Column(ratio=1),
    ),
    transient=True,
    console=console,
)

task_id = None


def on_runner_status(message: str):
    console.print(f"[blue]{message}")


running_jobs: Set[str] = set()
processed_jobs = 0


def print_job_ended(
    name: str, job_status: JobStatus, action: Action, status: CommandStatus | None
):
    job_prefix = "[red]✗[/red]" if job_status == "failed" else "[green]✓[/green]"
    status_color = "red" if job_status == "failed" else "green"

    status_message = status.message if status and status.message else ""

    table = rich.table.Table(show_header=False, pad_edge=False, box=None)
    table.add_column()
    table.add_row(
        f"{job_prefix} [{status_color}]{name}[/{status_color}]"
        f"{': [cyan]' + status_message + '[/cyan]' }"
        f"{' (start) ---' if status and status.output else ''}"
    )
    if status and status.output:
        table.add_row(status.output)
        table.add_row(f"--- [{status_color}]{name}[/{status_color}] (end) ---")
        table.add_row()

    console.print(table)


def on_job_status(
    name: str, job_status: JobStatus, action: Action, status: CommandStatus | None
):
    global processed_jobs
    global task_id
    if task_id is None:
        task_id = progress.add_task("[blue]Building[/blue]")

    if job_status == "failed":
        processed_jobs += 1
        if name in running_jobs:
            running_jobs.remove(name)
        print_job_ended(name, job_status, action, status)
    elif job_status == "running":
        running_jobs.add(name)
        progress.update(
            task_id,
            description=f"[blue]Finished [yellow]{processed_jobs}[/yellow] jobs.[/blue]",
        )
    else:
        processed_jobs += 1
        print_job_ended(name, job_status, action, status)
        if name in running_jobs:
            running_jobs.remove(name)


CheckRule = Literal["check_inputs_outputs", "output_file_missing"]
"""
The different rules that can be checked.

    check_inputs_outputs: Check that earlier actions don't need outputs from subsequent
    actions.

    output_file_missing: Check that actions create the files that they declare as
    outputs.
"""


@dataclass
class CheckStatus:
    rule_name: CheckRule
    action: Action
    status_text: str
    severity: Severity


failed_checks: List[CheckStatus] = []


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
