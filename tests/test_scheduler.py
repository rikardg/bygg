import os
from pathlib import Path
from tempfile import mkstemp

from bygg.action import Action, CommandStatus
from bygg.scheduler import scheduler


def get_closed_tmpfile() -> Path:
    fd, path = mkstemp()
    os.close(fd)
    return Path(path)


def test_scheduler_single_action():
    scheduler.__init__()
    scheduler.init_cache(get_closed_tmpfile())

    Action(
        name="action1",
        is_entrypoint=True,
    )

    assert scheduler.run_status() == "not started"

    scheduler.start_run("action1")

    assert scheduler.run_status() == "running"

    # check that the scheduler has the correct number of actions
    assert len(scheduler.build_actions) == 1
    assert len(scheduler.job_graph) == 1

    job = scheduler.get_ready_jobs(1)[0]
    assert job
    assert job.action.name == "action1"
    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)
    assert len(scheduler.job_graph) == 0
    assert scheduler.run_status() == "finished"


def test_scheduler_nonbranching():
    scheduler.__init__()
    scheduler.init_cache(get_closed_tmpfile())

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

    assert scheduler.run_status() == "not started"

    scheduler.start_run("action1")

    assert scheduler.run_status() == "running"

    # check that the scheduler has the correct number of actions
    assert len(scheduler.build_actions) == 4
    assert len(scheduler.job_graph) == 4

    job = scheduler.get_ready_jobs(1)[0]
    assert job
    assert job.action.name == "action4"
    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)
    assert len(scheduler.job_graph) == 3
    assert scheduler.run_status() == "running"

    job = scheduler.get_ready_jobs(1)[0]
    assert job
    assert job.action.name == "action3"
    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)
    assert len(scheduler.job_graph) == 2
    assert scheduler.run_status() == "running"

    job = scheduler.get_ready_jobs(1)[0]
    assert job
    assert job.action.name == "action2"
    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)
    assert len(scheduler.job_graph) == 1
    assert scheduler.run_status() == "running"

    job = scheduler.get_ready_jobs(1)[0]
    assert job
    assert job.action.name == "action1"
    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)
    assert len(scheduler.job_graph) == 0
    assert scheduler.run_status() == "finished"

    assert len(scheduler.build_actions) == 4
    assert len(scheduler.running_jobs) == 0
    assert len(scheduler.finished_jobs) == 4


def test_scheduler_branching():
    scheduler.__init__()
    scheduler.init_cache(get_closed_tmpfile())

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

    assert scheduler.run_status() == "not started"

    scheduler.start_run("action1")

    assert scheduler.run_status() == "running"

    # check that the scheduler has the correct number of actions
    assert len(scheduler.build_actions) == 4
    assert len(scheduler.job_graph) == 4

    jobs = scheduler.get_ready_jobs(1)
    assert jobs
    job = jobs[0]
    assert job.action.name == "action4"
    assert not scheduler.get_ready_jobs(1)
    assert scheduler.run_status() == "running"

    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)
    assert len(scheduler.job_graph) == 3
    assert scheduler.run_status() == "running"

    job1 = scheduler.get_ready_jobs(1)[0]
    assert job1 is not None
    assert job1.action.name == "action2" or job1.action.name == "action3"
    job1.status = CommandStatus(0, "Executed successfully", None)
    assert scheduler.run_status() == "running"

    job2 = scheduler.get_ready_jobs(1)[0]
    assert job2 is not None
    assert job2.action.name == "action2" or job2.action.name == "action3"
    job2.status = CommandStatus(0, "Executed successfully", None)
    assert scheduler.run_status() == "running"

    assert job1.name != job2.name

    assert not scheduler.get_ready_jobs(1)
    scheduler.job_finished(job1)
    scheduler.job_finished(job2)
    assert len(scheduler.job_graph) == 1
    assert scheduler.run_status() == "running"

    job = scheduler.get_ready_jobs(1)[0]
    assert job is not None
    assert job.action.name == "action1"
    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)
    assert len(scheduler.job_graph) == 0
    assert scheduler.run_status() == "finished"

    assert len(scheduler.build_actions) == 4
    assert len(scheduler.running_jobs) == 0
    assert len(scheduler.finished_jobs) == 4


def test_scheduler_branching_one_failed():
    scheduler.__init__()
    scheduler.init_cache(get_closed_tmpfile())

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

    assert scheduler.run_status() == "not started"

    scheduler.start_run("action1")

    assert scheduler.run_status() == "running"

    # check that the scheduler has the correct number of actions
    assert len(scheduler.build_actions) == 4
    assert len(scheduler.job_graph) == 4

    job = scheduler.get_ready_jobs(1)[0]
    assert job is not None
    assert job.action.name == "action4"
    assert not scheduler.get_ready_jobs(1)
    assert scheduler.run_status() == "running"

    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)
    assert len(scheduler.job_graph) == 3

    job1 = scheduler.get_ready_jobs(1)[0]
    assert job1 is not None
    assert job1.action.name == "action2" or job1.action.name == "action3"
    job1.status = CommandStatus(0, "Executed successfully", None)
    assert scheduler.run_status() == "running"

    job2 = scheduler.get_ready_jobs(1)[0]
    assert job2 is not None
    assert job2.action.name == "action2" or job2.action.name == "action3"
    job2.status = CommandStatus(1, "Failed", None)
    assert scheduler.run_status() == "running"

    assert job1.name != job2.name

    assert not scheduler.get_ready_jobs(1)
    scheduler.job_finished(job1)
    scheduler.job_finished(job2)
    assert scheduler.run_status() == "failed"

    assert not scheduler.get_ready_jobs(1)
    assert len(scheduler.ready_jobs) == 0
    assert len(scheduler.job_graph) == 2
    assert scheduler.run_status() == "failed"

    assert len(scheduler.build_actions) == 4
    assert len(scheduler.running_jobs) == 0
    assert len(scheduler.finished_jobs) == 3


def test_scheduler_dynamic_dependency():
    scheduler.__init__()
    cache_file = get_closed_tmpfile()
    scheduler.init_cache(cache_file)

    Action(
        name="action1",
        dependencies=["action2"],
        is_entrypoint=True,
    )
    Action(name="action2", dynamic_dependency=lambda: "foo")

    assert scheduler.run_status() == "not started"

    scheduler.start_run("action1")

    assert scheduler.run_status() == "running"

    # check that the scheduler has the correct number of actions
    assert len(scheduler.build_actions) == 2
    assert len(scheduler.job_graph) == 2

    job = scheduler.get_ready_jobs(1)[0]
    assert job
    assert job.action.name == "action2"
    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)
    assert len(scheduler.job_graph) == 1
    assert scheduler.run_status() == "running"

    job = scheduler.get_ready_jobs(1)[0]
    assert job
    assert job.action.name == "action1"
    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)
    assert len(scheduler.job_graph) == 0
    assert scheduler.run_status() == "finished"

    assert len(scheduler.build_actions) == 2
    assert len(scheduler.running_jobs) == 0
    assert len(scheduler.finished_jobs) == 2

    scheduler.shutdown()

    # Second run

    scheduler.__init__()
    scheduler.init_cache(cache_file)

    Action(
        name="action1",
        dependencies=["action2"],
        is_entrypoint=True,
    )
    Action(name="action2", dynamic_dependency=lambda: "foo")

    assert scheduler.run_status() == "not started"

    scheduler.start_run("action1")

    assert scheduler.run_status() == "running"

    # check that the scheduler has the correct number of actions
    assert len(scheduler.build_actions) == 2
    assert len(scheduler.job_graph) == 2

    jobs = scheduler.get_ready_jobs()
    assert len(jobs) == 0

    # Asking again triggers the scheduler to realise whether it's done or not.
    # TODO this behavious should probably be changeed.
    jobs = scheduler.get_ready_jobs()
    assert len(scheduler.job_graph) == 0
    assert scheduler.run_status() == "finished"

    assert len(scheduler.build_actions) == 2
    assert len(scheduler.running_jobs) == 0
