import nox


@nox.session(python=["3.11"])
def tests(session):
    session.install("-r", "requirements.txt", "-r", "requirements-dev.txt")
    session.install(".")
    session.run("pytest")
