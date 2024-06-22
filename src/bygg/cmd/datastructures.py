import argparse
from dataclasses import dataclass
from typing import Optional

from bygg.cmd.configuration import ByggFile
from bygg.core.runner import ProcessRunner
from bygg.core.scheduler import Scheduler
import msgspec


class SubProcessIpcDataList(msgspec.Struct):
    """Holds the data for --list from a subprocess."""

    actions: dict[str, str]
    default_action: Optional[str] = None


class SubProcessIpcDataTree(msgspec.Struct):
    """Holds the data for --tree from a subprocess."""

    actions: dict[str, str]


class SubProcessIpcData(msgspec.Struct):
    """Holds the results for metadata from a subprocess."""

    # Actions that were found
    found_actions: set[str] = msgspec.field(default_factory=set)
    list: Optional[SubProcessIpcDataList] = None
    tree: Optional[SubProcessIpcDataTree] = None


@dataclass
class ByggContext:
    """Container for various state"""

    runner: ProcessRunner
    scheduler: Scheduler
    configuration: ByggFile
    ipc_data: Optional[SubProcessIpcData] = None


@dataclass
class EntryPoint:
    name: str
    description: str


NO_DESCRIPTION = "No description"


def get_entrypoints(ctx: ByggContext, args: argparse.Namespace) -> list[EntryPoint]:
    return [
        EntryPoint(x.name, x.description or NO_DESCRIPTION)
        for x in ctx.scheduler.build_actions.values()
        if x.is_entrypoint
    ] or [
        EntryPoint(x.name, x.description or NO_DESCRIPTION)
        for x in ctx.configuration.actions
        if x.is_entrypoint and x.environment == args.is_restarted_with_env
    ]
