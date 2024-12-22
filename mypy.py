#!/usr/bin/env python3

from pathlib import Path

from bygg.output.output import TerminalStyle as TS
from bygg.output.output import output_error
from src.bygg.system_helpers import call

directories = [
    Path("src/bygg"),
    *{p.parent for p in Path("examples").glob("*/*.py")},
]
mypy = Path(".venv/bin/mypy")
extra_arguments = {
    # We want to type check without having to have all the environments set up.
    Path("examples/environments/"): "--ignore-missing-imports",
}

exit_code = 0

for directory in directories:
    print(f"\n{TS.BOLD}=== Running mypy in {directory} ==={TS.RESET}")
    s = call(
        f"{mypy} --no-warn-no-return --disable-error-code func-returns-value --check-untyped-defs --pretty {extra_arguments.get(directory, '')} {directory}"
    )
    if not s:
        output_error(f"Failed to run mypy in {directory}")
        exit_code |= s

exit(exit_code)
