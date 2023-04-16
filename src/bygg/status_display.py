from typing import Set

import rich
import rich.box
import rich.progress
import rich.status
import rich.table

from bygg.action import Action
from bygg.runner import JobStatus
from bygg.types import CommandStatus

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
