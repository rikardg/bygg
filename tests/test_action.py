from bygg.action import Action, ActionContext, CommandStatus


def test_Action_setup_empty():
    action = Action(name="empty Action", inputs=None, outputs=None, dependencies=None)
    assert action.name == "empty Action"
    assert action.inputs == set()
    assert action.outputs == set()
    assert action.dependencies == set()
    assert action.is_entrypoint is False
    assert action.command is None


def test_Action_setup_with_dependencies():
    action = Action(
        name="test Action",
        inputs=["input1", "input2"],
        outputs=["output1", "output2"],
        dependencies=["dependency1", "dependency2"],
        is_entrypoint=True,
    )
    assert action.name == "test Action"
    assert action.inputs == {"input1", "input2"}
    assert action.outputs == {"output1", "output2"}
    assert action.dependencies == {"dependency1", "dependency2"}
    assert action.is_entrypoint is True
    assert action.command is None


def test_Action_with_python_cmd():
    def test_command(ctx: ActionContext):
        if not ctx.inputs:
            return CommandStatus(1, "No inputs.", None)

        return CommandStatus(0, "Executed successfully", None)

    action = Action(
        name="test with Python command",
        command=test_command,
        inputs=["input1", "input2"],
        outputs=["changed_file1", "changed_file2"],
    )

    assert action.command is not None
    assert action.command is test_command
    assert action.command(action).rc == 0
    assert action.command(action).message == "Executed successfully"
