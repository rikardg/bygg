from bygg.tree import display_tree


def test_tree_single_action(scheduler_single_action, capsys, snapshot):
    scheduler, _ = scheduler_single_action
    display_tree(scheduler, ["action1"])
    stdout, _ = capsys.readouterr()
    assert stdout == snapshot


def test_tree_four_nonbranching_actions(
    scheduler_four_nonbranching_actions, capsys, snapshot
):
    scheduler, _ = scheduler_four_nonbranching_actions
    display_tree(scheduler, ["action1"])
    stdout, _ = capsys.readouterr()
    assert stdout == snapshot


def test_tree_branching_actions(scheduler_branching_actions, capsys, snapshot):
    scheduler, _ = scheduler_branching_actions
    display_tree(scheduler, ["action1"])
    stdout, _ = capsys.readouterr()
    assert stdout == snapshot
