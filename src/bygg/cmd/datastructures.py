from dataclasses import dataclass
from typing import Optional

from bygg.cmd.configuration import ByggFile
from bygg.core.runner import ProcessRunner
from bygg.core.scheduler import Scheduler
import msgspec


class SubProcessIpcDataList(msgspec.Struct):
    actions: dict[str, str]
    default_action: Optional[str] = None


class SubProcessIpcDataTree(msgspec.Struct):
    actions: dict[str, str]


class SubProcessIpcData(msgspec.Struct):
    list: Optional[SubProcessIpcDataList] = None
    tree: Optional[SubProcessIpcDataTree] = None


@dataclass
class ByggContext:
    """Container for various state"""

    runner: ProcessRunner
    scheduler: Scheduler
    configuration: ByggFile
    is_restarted_with_env: str | None
    ipc_data: Optional[SubProcessIpcData] = None


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
        if x.is_entrypoint and x.environment == ctx.is_restarted_with_env
    ]
