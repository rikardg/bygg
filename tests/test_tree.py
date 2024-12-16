from bygg.cmd.configuration import Byggfile
from bygg.cmd.datastructures import ByggContext
from bygg.cmd.tree import display_tree
from bygg.core.runner import ProcessRunner


def test_tree_single_action(scheduler_single_action, capsys, snapshot):
    scheduler, _ = scheduler_single_action
    ctx = ByggContext(ProcessRunner(scheduler), scheduler, Byggfile())
    display_tree(ctx, ["action1"])
    stdout, _ = capsys.readouterr()
    assert stdout == snapshot


def test_tree_four_nonbranching_actions(
    scheduler_four_nonbranching_actions, capsys, snapshot
):
    scheduler, _ = scheduler_four_nonbranching_actions
    ctx = ByggContext(ProcessRunner(scheduler), scheduler, Byggfile())
    display_tree(ctx, ["action1"])
    stdout, _ = capsys.readouterr()
    assert stdout == snapshot


def test_tree_branching_actions(scheduler_branching_actions, capsys, snapshot):
    scheduler, _ = scheduler_branching_actions
    ctx = ByggContext(ProcessRunner(scheduler), scheduler, Byggfile())
    display_tree(ctx, ["action1"])
    stdout, _ = capsys.readouterr()
    assert stdout == snapshot
