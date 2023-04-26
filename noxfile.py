import nox


@nox.session(python=["3.11"], reuse_venv=False)
def tests(session):
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.install(".")
    session.run("pytest")


@nox.session(python=["3.11"], reuse_venv=True)
def basics(session):
    session.run("bygg", success_codes=[1], silent=True)
    session.run("bygg", "--help", silent=True)


@nox.session(python=["3.11"], reuse_venv=True)
def examples(session):
    session.install(".")

    with session.chdir("examples/parametric"):
        session.run("bygg")

    with session.chdir("examples/taskrunner"):
        session.run("bygg")

    with session.chdir("examples/trivial"):
        session.run("bygg")

    with session.chdir("examples/venv_and_pre"):
        session.run("bygg", success_codes=[1])
