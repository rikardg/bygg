import argparse
import dataclasses
from typing import Optional

import pytest

from bygg.cmd.argument_parsing import ByggNamespace, create_argument_parser
from bygg.cmd.completions import EntrypointCompleter
from bygg.cmd.configuration import Byggfile
from bygg.cmd.datastructures import ByggContext, SubProcessIpcData
from bygg.cmd.tree import print_tree, tree_collect_for_environment
from bygg.core.runner import ProcessRunner
from bygg.core.scheduler import Scheduler


@dataclasses.dataclass
class ArgparseFixtureData:
    parser: argparse.ArgumentParser
    args: argparse.Namespace
    bygg_namespace: ByggNamespace


@pytest.fixture
def create_byggcontext():
    def instantiate_context(scheduler: Scheduler, argv: Optional[list[str]] = None):
        parser = create_argument_parser(EntrypointCompleter())
        args = parser.parse_args(argv or [])
        return ByggContext(
            ProcessRunner(scheduler),
            scheduler,
            Byggfile(),
            parser,
            args,
            ByggNamespace(**vars(args)),
            SubProcessIpcData(),
        )

    yield instantiate_context


def test_tree_single_action(
    scheduler_single_action, create_byggcontext, capsys, snapshot
):
    scheduler, _ = scheduler_single_action
    ctx = create_byggcontext(scheduler)
    print_tree(tree_collect_for_environment(ctx), ["action1"])
    stdout, _ = capsys.readouterr()
    assert stdout == snapshot


def test_tree_four_nonbranching_actions(
    scheduler_four_nonbranching_actions, create_byggcontext, capsys, snapshot
):
    scheduler, _ = scheduler_four_nonbranching_actions
    ctx = create_byggcontext(scheduler)
    print_tree(tree_collect_for_environment(ctx), ["action1"])
    stdout, _ = capsys.readouterr()
    assert stdout == snapshot


def test_tree_branching_actions(
    scheduler_branching_actions, create_byggcontext, capsys, snapshot
):
    scheduler, _ = scheduler_branching_actions
    ctx = create_byggcontext(scheduler)
    print_tree(tree_collect_for_environment(ctx), ["action1"])
    stdout, _ = capsys.readouterr()
    assert stdout == snapshot
