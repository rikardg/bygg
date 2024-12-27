import shutil

import nox

if shutil.which("uv"):
    nox.options.default_venv_backend = "uv"

nox.options.error_on_external_run = True
nox.options.stop_on_first_error

python_versions = ["3.11", "3.12", "3.13"]


# Not a test, but utility functionality for updating the help snapshots across all
# tested Python versions.
# Run with `nox -s update_help_snapshots`.
@nox.session(default=False, python=python_versions)
def update_help_snapshots(session):
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.install(".")
    session.run("pytest", "-m", "help", "--snapshot-update")


@nox.session(python=python_versions)
def tests(session):
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.install(".")
    session.run("pytest", "-vv", "-m", "not help")
    # The help test needs separate snapshots for each Python version, and the snapshot
    # package for pytest (syrupy) will report the snapshots for the Python version not
    # running currently as unused. Run the help test with the --snapshot-warn-unused
    # flag.
    session.run("pytest", "-vv", "-m", "help", "--snapshot-warn-unused")
    session.run("bygg", success_codes=[1], silent=True)
    session.run("bygg", "--help", silent=True)


@nox.session(python=python_versions)
def examples(session):
    session.install(".")

    with session.chdir("examples/only_python"):
        session.run("bygg", success_codes=[1])
        session.run("bygg", "hello")
        session.run("bygg", "hello", "--tree")
        session.run("bygg", "--clean", success_codes=[1])
        session.run("bygg", "hello", "--clean")

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
