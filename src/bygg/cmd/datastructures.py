from dataclasses import dataclass

from bygg.cmd.configuration import ByggFile
from bygg.core.runner import ProcessRunner
from bygg.core.scheduler import Scheduler


@dataclass
class ByggContext:
    """Container for various state"""

    runner: ProcessRunner
    scheduler: Scheduler
    configuration: ByggFile


@dataclass
class EntryPoint:
    name: str
    description: str


NO_DESCRIPTION = "No description"


def get_entrypoints(ctx: ByggContext) -> list[EntryPoint]:
    return [
        EntryPoint(x.name, x.description or NO_DESCRIPTION)
        for x in ctx.scheduler.build_actions.values()
        if x.is_entrypoint
    ] or [
        EntryPoint(x.name, x.description or NO_DESCRIPTION)
        for x in ctx.configuration.actions
        if x.is_entrypoint
    ]
