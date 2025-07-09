import argparse
from dataclasses import dataclass, field
import os
from typing import Optional

from bygg.cmd.argument_parsing import ByggNamespace
from bygg.cmd.configuration import Byggfile
from bygg.core.common_types import CommandStatus
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
    return_code: int = 0
    found_input_files: set[str] = field(default_factory=set)
    failed_jobs: dict[str, CommandStatus] = field(default_factory=dict)


@dataclass
class ByggContext:
    """Container for various state"""

    runner: ProcessRunner
    scheduler: Scheduler
    configuration: Byggfile
    parser: argparse.ArgumentParser
    args_namespace: argparse.Namespace
    bygg_namespace: ByggNamespace
    ipc_data: SubProcessIpcData


@dataclass
class EntryPoint:
    def __repr__(self):
        return self.name

    name: str
    description: str


NO_DESCRIPTION = "No description"


def get_entrypoints(ctx: ByggContext, environment_name: str) -> list[EntryPoint]:
    show_all = os.environ.get("BYGG_DEV")
    return [
        EntryPoint(x.name, x.description or NO_DESCRIPTION)
        for x in ctx.scheduler.build_actions.values()
        if (x.is_entrypoint or show_all) and x.environment == environment_name
    ]
