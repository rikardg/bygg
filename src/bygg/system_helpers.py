"""
System-near helper functions. Only import things from the standard library here; this
way these helpers can be used also for utility scripts.
"""

import contextlib
import errno
import os
import pty
import shlex
import signal
import subprocess
from typing import Generator


class ProcessGenerator:
    """
    Class that wraps a process return value and a generator that yields the output of a
    process line by line.

    Attributes
    ----------
    returncode : int
        Process return code.
    generator : Generator
        Generator that yields the output of the process line by line.

    Yields
    ------
    str
        Output of the process.
    """

    returncode: int
    """Process return code."""

    generator: Generator
    """Generator that yields the output of the process line by line."""

    def __init__(self):
        self.returncode = -1

    def __iter__(self):
        self.value = yield from self.generator


def subprocess_tty(cmd, encoding="utf-8", timeout=10, **kwargs):
    """
    Wrapper around subprocess.Popen that sets up the process as if it were running in a
    TTY and returns a generator that yields the stdout of the process line by line.

    Parameters
    ----------
    cmd :
        Passed directly to subprocess.Popen; see its documentation for details.
    encoding : str, optional
        Encoding to use when reading stdout, by default "utf-8".
    timeout : int, optional
        Timeout to use when polling the child process to see if it has exited, by
        default 10 seconds.

    Returns
    -------
    ProcessGenerator
        Generator that yields the stdout of the child process line by line. After the
        generator is exhausted, the returncode attribute of the generator will be set to
        the exit code of the child process.

    Yields
    ------
    str
        Lines of stdout from the child process.

    Raises
    ------
    subprocess.TimeoutExpired
        Re-raised if the child process did not exit within the set timeout after having
        received both terminate and kill signals.

    Can also raise other exceptions from subprocess.Popen.
    """

    generator = ProcessGenerator()

    def subprocess_iterator():
        # From https://stackoverflow.com/a/77387332
        m, s = pty.openpty()
        p = subprocess.Popen(cmd, stdout=s, stderr=s, **kwargs)
        os.close(s)

        try:
            for line in open(m, encoding=encoding):
                if not line:  # EOF
                    break
                yield line
        except OSError as e:
            if e.errno != errno.EIO:  # EIO also means EOF
                raise
        finally:
            if p.poll() is None:
                p.send_signal(signal.SIGINT)
                try:
                    p.wait(timeout)
                except subprocess.TimeoutExpired:
                    p.terminate()
                    try:
                        p.wait(timeout)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        raise
            p.wait()
            generator.returncode = p.returncode

    generator.generator = subprocess_iterator()
    return generator


def subprocess_tty_print(cmd, encoding="utf-8", timeout=10, **kwargs):
    """
    Thin wrapper around subprocess_tty that prints its output line by line. See
    subprocess_tty for details.


    Parameters
    ----------
    See subprocess_tty.

    Returns
    -------
    int
        The status code from the subprocess.
    """
    proc = subprocess_tty(cmd, encoding, timeout, **kwargs)
    for line in proc:
        print(line.rstrip())
    return proc.returncode


class ExitCode(int):
    """
    An int with a customised __bool__ method that considers 0 to be truthy. This is
    useful for working with subprocess return codes.
    """

    def __bool__(self):
        return self == 0


def call(cmd, encoding="utf-8", timeout=10, **kwargs) -> ExitCode:
    """
    Convenience wrapper around subprocess_tty_print; the command to be executed can be
    given as string that will be split instead of as an array. Output will be printed
    line by line.

    Parameters
    ----------
    cmd : str
        The command to be executed. Will be run through shlex.split().

    See subprocess_tty_print and subprocess_tty for the other parameters.

    Returns
    -------
    ExitCode
        The exit code from the subprocess. ExitCode is a subclass of int that can be
        used as a boolean; subprocess success (0) is considered truthy.

    Raises
    ------
    See subprocess_tty_print and subprocess_tty.
    """

    return ExitCode(subprocess_tty_print(shlex.split(cmd), encoding, timeout, **kwargs))


@contextlib.contextmanager
def change_dir(dir: str | os.PathLike | None):
    old_dir = os.getcwd()
    try:
        if dir is not None:
            os.chdir(dir)
        yield
    finally:
        os.chdir(old_dir)
