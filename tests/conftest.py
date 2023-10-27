import os
from pathlib import Path
from tempfile import mkstemp

from bygg.action import Action
from bygg.scheduler import Scheduler
import pytest


def get_closed_tmpfile() -> Path:
    fd, path = mkstemp()
    os.close(fd)
    return Path(path)


@pytest.fixture
def scheduler_fixture():
    """Return a scheduler and a cache file."""
    scheduler = Scheduler()
    scheduler.__init__()
    cache_file = get_closed_tmpfile()
    scheduler.init_cache(cache_file)
    yield (scheduler, cache_file)
    scheduler.shutdown()


@pytest.fixture
def scheduler_single_action(scheduler_fixture):
    Action(
        name="action1",
        is_entrypoint=True,
    )
    return scheduler_fixture


@pytest.fixture
def scheduler_four_nonbranching_actions(scheduler_fixture):
    Action(
        name="action1",
        dependencies=["action2"],
        is_entrypoint=True,
    )
    Action(
        name="action2",
        dependencies=["action3"],
    )
    Action(
        name="action3",
        dependencies=["action4"],
    )
    Action(
        name="action4",
        dependencies=[],
    )
    return scheduler_fixture


@pytest.fixture
def scheduler_branching_actions(scheduler_fixture):
    Action(
        name="action1",
        dependencies=["action2", "action3"],
        is_entrypoint=True,
    )
    Action(
        name="action2",
        dependencies=["action4"],
    )
    Action(
        name="action3",
        dependencies=["action4"],
    )
    Action(
        name="action4",
        dependencies=[],
    )
    return scheduler_fixture
