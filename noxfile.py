import nox

nox.options.error_on_external_run = True


@nox.session(python=["3.11"])
def tests(session):
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.install(".")
    session.run("pytest")


@nox.session(python=["3.11"])
def basics(session):
    session.install(".")
    session.run("bygg", success_codes=[1], silent=True)
    session.run("bygg", "--help", silent=True)


@nox.session(python=["3.11"])
def examples(session):
    session.install(".")

    with session.chdir("examples/only_python"):
        session.run("bygg")
        session.run("bygg", "--clean")

    with session.chdir("examples/parametric"):
        session.run("bygg")
        session.run("bygg", "--clean")

    with session.chdir("examples/taskrunner"):
        session.run("bygg")
        session.run("bygg", "--clean")

    with session.chdir("examples/trivial"):
        session.run("bygg")
        session.run("bygg", "--clean")

    with session.chdir("examples/environments"):
        session.run("bygg")
        session.run("bygg", "clean_environments")

        session.run("bygg", "default_action")
        session.run("bygg", "clean_environments")

        session.run("bygg", "action1")
        session.run("bygg", "clean_environments")

        session.run("bygg", "action2")
        session.run("bygg", "clean_environments")

        session.run("bygg", "action1", "default_action", "action2")
        session.run("bygg", "clean_environments")
