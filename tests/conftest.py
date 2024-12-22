import os
from pathlib import Path
import shutil
from tempfile import mkstemp

import pytest

from bygg.core.action import Action
from bygg.core.scheduler import Scheduler


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


# .git is needed for hatch to be able to extract version when doing pip install
# from the sub environments
clean_bygg_tree_exclusions = (
    "__pycache__",
    ".bygg",
    ".nox",
    ".venv*",
    "foo",
    "bar",
    "t",
)


@pytest.fixture
def clean_bygg_tree(tmp_path):
    clean_path = tmp_path / "bygg"
    shutil.copytree(
        Path("."),
        clean_path,
        ignore=shutil.ignore_patterns(*clean_bygg_tree_exclusions),
    )
    return clean_path


@pytest.fixture(autouse=True)
def set_is_CI():
    os.environ["CI"] = "1"
