import os
import re
import subprocess
from typing import List, Optional, Set, Tuple

from bygg.types import CommandStatus


def create_shell_command(shell_command: str, message: Optional[str] = None):
    def call_shell_command(inputs: Optional[Set[str]], outputs: Optional[Set[str]]):
        # Map stderr onto stdout and return both as the output
        process = subprocess.run(
            shell_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        return CommandStatus(process.returncode, message, process.stdout)

    return lambda ctx: call_shell_command(ctx.inputs, ctx.outputs)


def filenames_from_pattern(
    input_files: List[str], in_pattern: str, out_pattern: str
) -> List[Tuple[str, str]]:
    """
    Generate a list of tuples with the input and output file names from a a list of
    input file names and a pattern like in Makefile pattern rules. File names that don't
    match the pattern are ignored. Example:

      ["/foo/bar/baz.txt.j2"], "%.txt.j2", "out_%.txt")
        => [("/foo/bar/baz.txt.j2", "/foo/bar/out_baz.txt")]
    """

    output_files = []
    matcher = re.compile(in_pattern.replace("%", "(.+)"))
    for input_file in input_files:
        head, tail = os.path.split(input_file)
        matches = matcher.match(tail)
        if matches:
            output_file = os.path.join(head, out_pattern.replace("%", matches.group(1)))
            output_files.append((input_file, output_file))
    return output_files
