from pathlib import Path

import pytest

from bygg.output.job_output import HighlightConfig, highlight_log

short_gcc_log = """
main.c: In function ‘main’:
main.c:5:5: warning: implicit declaration of function ‘foo’ [-Wimplicit-function-declaration]
    foo();
    ^~~
main.c:5:5: warning: unused variable ‘a’ [-Wunused-variable]
    int a = 5;
    ^~~
main.c:6:5: warning: unused variable ‘b’ [-Wunused-variable]
    int b = 10;
    ^~~
main.c:7:5: warning: unused variable ‘c’ [-Wunused-variable]
    int c = a + b;
    ^~~
main.c:9:5: error: expected declaration or statement at end of input
    return 0;
    ^~~~~~
"""


def test_no_config():
    assert highlight_log(short_gcc_log) == short_gcc_log


config = [
    HighlightConfig(
        pattern=r"(warning:)",
        start="[START_WARNING]",
        end="[END_WARNING]",
    ),
    HighlightConfig(
        pattern=r"(error:)",
        start="[START_ERROR]",
        end="[END_ERROR]",
    ),
]


def test_highlight_warning(snapshot):
    print(highlight_log(short_gcc_log, config))
    assert highlight_log(short_gcc_log, config) == snapshot


testdata_path = Path("examples/failing_jobs/testdata/")
logfiles = ["gcc.log", "go.log", "make.log", "npm.log"]


@pytest.mark.parametrize("logfile", logfiles, ids=lambda x: x)
def test_highlight_warning_logfiles(snapshot, logfile):
    with open(testdata_path / logfile) as f:
        log = f.read()
    assert highlight_log(log, config) == snapshot
