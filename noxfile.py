import nox

nox.options.error_on_external_run = True
nox.options.stop_on_first_error

python_versions = ["3.11", "3.12"]


@nox.session(python=python_versions)
def tests(session):
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.install(".")
    session.run("pytest")


@nox.session(python=python_versions)
def basics(session):
    session.install(".")
    session.run("bygg", success_codes=[1], silent=True)
    session.run("bygg", "--help", silent=True)


@nox.session(python=python_versions)
def examples(session):
    session.install(".")

    with session.chdir("examples/only_python"):
        session.run("bygg", success_codes=[1])
        session.run("bygg", "hello")
        session.run("bygg", "hello", "--tree")
        session.run("bygg", "--clean")

    with session.chdir("examples/parametric"):
        session.run("bygg")
        session.run("bygg", "--tree")
        session.run("bygg", "--clean")

    with session.chdir("examples/taskrunner"):
        session.run("bygg")
        session.run("bygg", "--tree")
        session.run("bygg", "--clean")

    with session.chdir("examples/trivial"):
        session.run("bygg")
        session.run("bygg", "transform")
        session.run("bygg", "--tree")
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
        session.run("bygg", "action1", "default_action", "action2", "--tree")
        session.run("bygg", "clean_environments")

    with session.chdir("examples/checks"):
        session.run("bygg")
        session.run("bygg", "--check", success_codes=[1])
        session.run("bygg", "--tree")
        session.run("bygg", "all_checks", "--check", success_codes=[1])
        session.run("bygg", "all_checks", "--tree")
