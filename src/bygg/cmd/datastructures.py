from dataclasses import dataclass, field
from typing import Optional

from bygg.cmd.argument_parsing import ByggNamespace
from bygg.cmd.configuration import Byggfile
from bygg.core.runner import ProcessRunner
from bygg.core.scheduler import Scheduler


@dataclass
class SubProcessIpcDataList:
    """Holds the data for --list from a subprocess."""

    actions: dict[str, str]
    default_action: Optional[str] = None


@dataclass
class SubProcessIpcDataTree:
    """Holds the data for --tree from a subprocess."""

    actions: dict[str, str]


@dataclass
class SubProcessIpcData:
    """Holds the results for metadata from a subprocess."""

    # Actions that were found
    found_actions: set[str] = field(default_factory=set)
    list: Optional[SubProcessIpcDataList] = None
    tree: Optional[SubProcessIpcDataTree] = None


@dataclass
class ByggContext:
    """Container for various state"""

    runner: ProcessRunner
    scheduler: Scheduler
    configuration: Byggfile
    ipc_data: Optional[SubProcessIpcData] = None


@dataclass
class EntryPoint:
    name: str
    description: str


NO_DESCRIPTION = "No description"


def get_entrypoints(ctx: ByggContext, args: ByggNamespace) -> list[EntryPoint]:
    return [
        EntryPoint(x.name, x.description or NO_DESCRIPTION)
        for x in ctx.scheduler.build_actions.values()
        if x.is_entrypoint
    ]
