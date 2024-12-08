import pytest

from bygg.core.action import Action, ActionContext, CommandStatus

pytestmark = pytest.mark.scheduler


def test_scheduler_single_action(scheduler_single_action):
    scheduler, _ = scheduler_single_action

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


def test_scheduler_nonbranching(scheduler_four_nonbranching_actions):
    scheduler, _ = scheduler_four_nonbranching_actions

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


def test_scheduler_branching(scheduler_branching_actions):
    scheduler, _ = scheduler_branching_actions

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


def test_scheduler_branching_one_failed(scheduler_branching_actions):
    scheduler, _ = scheduler_branching_actions

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


def test_scheduler_dynamic_dependency(scheduler_fixture):
    scheduler, _ = scheduler_fixture

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

    job = scheduler.get_ready_jobs()[0]
    assert job
    assert job.name == "action2"
    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)

    # check again that the scheduler has the correct number of actions
    assert len(scheduler.build_actions) == 2
    assert len(scheduler.job_graph) == 1

    job = scheduler.get_ready_jobs()[0]
    assert job
    assert len(scheduler.job_graph) == 1
    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)

    assert scheduler.run_status() == "finished"

    assert len(scheduler.build_actions) == 2
    assert len(scheduler.running_jobs) == 0


def test_scheduler_dynamic_dependency_two_runs(scheduler_fixture):
    scheduler, cache_file = scheduler_fixture

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
    assert scheduler.run_status() == "running"

    # Ask again since the job should have been skipped and the scheduler is still
    # running:
    job = scheduler.get_ready_jobs()[0]
    assert job
    assert len(scheduler.job_graph) == 1

    job.status = CommandStatus(0, "Executed successfully", None)
    scheduler.job_finished(job)

    assert scheduler.run_status() == "finished"

    assert len(scheduler.build_actions) == 2
    assert len(scheduler.running_jobs) == 0


def test_scheduler_single_file(scheduler_fixture, tmp_path):
    scheduler, cache_file = scheduler_fixture

    def action1(ctx: ActionContext):
        for output in ctx.outputs:
            with open(output, "w") as f:
                f.write("file content")
        return CommandStatus(0, "Executed successfully", None)

    Action(
        name="file",
        is_entrypoint=True,
        inputs=[],
        outputs=[str(tmp_path / "file1")],
        command=action1,
    )

    scheduler.start_run("file")

    job = scheduler.get_ready_jobs(1)[0]
    job.status = job.action.command(job.action)
    scheduler.job_finished(job)

    assert len(scheduler.job_graph) == 0
    assert scheduler.run_status() == "finished"

    scheduler.shutdown()

    # Second run

    scheduler.__init__()
    scheduler.init_cache(cache_file)

    Action(
        name="file",
        is_entrypoint=True,
        inputs=[],
        outputs=[str(tmp_path / "file1")],
        command=action1,
    )

    scheduler.start_run("file")
    job_list = scheduler.get_ready_jobs(1)

    assert len(job_list) == 0
    assert len(scheduler.job_graph) == 0
    assert scheduler.run_status() == "finished"


def test_scheduler_single_file_changed(scheduler_fixture, tmp_path):
    scheduler, cache_file = scheduler_fixture
    infile = tmp_path / "file0"
    outfile = tmp_path / "file1"

    def action1(ctx: ActionContext):
        for output in ctx.outputs:
            with open(output, "w") as f:
                f.write("file content")
        return CommandStatus(0, "Executed successfully", None)

    Action(
        name="file",
        is_entrypoint=True,
        inputs=[str(infile)],
        outputs=[str(outfile)],
        command=action1,
    )

    infile.write_text("infile content")

    scheduler.start_run("file")

    job = scheduler.get_ready_jobs(1)[0]
    job.status = job.action.command(job.action)
    scheduler.job_finished(job)

    assert len(scheduler.job_graph) == 0
    assert scheduler.run_status() == "finished"

    scheduler.shutdown()

    # Second run

    scheduler.__init__()
    scheduler.init_cache(cache_file)

    Action(
        name="file",
        is_entrypoint=True,
        inputs=[str(infile)],
        outputs=[str(outfile)],
        command=action1,
    )

    scheduler.start_run("file")
    job_list = scheduler.get_ready_jobs(1)

    assert len(job_list) == 0
    assert len(scheduler.job_graph) == 0
    assert scheduler.run_status() == "finished"

    # Third run, modify input file

    infile.write_text("modified infile content")

    scheduler.__init__()
    scheduler.init_cache(cache_file)

    Action(
        name="file",
        is_entrypoint=True,
        inputs=[str(infile)],
        outputs=[str(outfile)],
        command=action1,
    )

    scheduler.start_run("file")
    job_list = scheduler.get_ready_jobs(1)

    assert len(job_list) == 1
    assert len(scheduler.job_graph) == 1

    job.status = job.action.command(job.action)
    scheduler.job_finished(job)

    assert len(scheduler.job_graph) == 0
    assert scheduler.run_status() == "finished"
