from dataclasses import dataclass
import os
import re
import subprocess
from typing import Optional

from bygg.core.common_types import CommandStatus


def create_shell_command(shell_command: str, message: Optional[str] = None):
    def call_shell_command(inputs: Optional[set[str]], outputs: Optional[set[str]]):
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


@dataclass
class FileListsFromPattern:
    input_files: list[str]
    output_files: list[str]
    unmatched_input_files: list[str]


def filenames_from_pattern(
    input_files: list[str], in_pattern: str, target_pattern: str
) -> FileListsFromPattern:
    """
    Generate a list of target filenames from a list of input file names and a pattern
    like in Makefile pattern rules. File names that don't match the pattern are ignored
    and returned as a separate list.

    Returns a FileListsFromPattern dataclass containing lists of the input and output
    filenames as well as the ignored input files.

    Example filename transformation:

      ["/foo/bar/baz.txt.j2"], "%.txt.j2", "out_%.txt")
        => "/foo/bar/out_baz.txt"

    Intended to work like the corresponding mechanism in GNU Makefiles. From
    https://www.gnu.org/software/make/manual/html_node/Pattern-Match.html:

    "A target pattern is composed of a ‘%’ between a prefix and a suffix, either or both
    of which may be empty. The pattern matches a file name only if the file name starts
    with the prefix and ends with the suffix, without overlap. The text between the
    prefix and the suffix is called the stem. Thus, when the pattern ‘%.o’ matches the
    file name test.o, the stem is ‘test’. The pattern rule prerequisites are turned into
    actual file names by substituting the stem for the character ‘%’. Thus, if in the
    same example one of the prerequisites is written as ‘%.c’, it expands to ‘test.c’.

    When the target pattern does not contain a slash (and it usually does not),
    directory names in the file names are removed from the file name before it is
    compared with the target prefix and suffix. After the comparison of the file name to
    the target pattern, the directory names, along with the slash that ends them, are
    added on to the prerequisite file names generated from the pattern rule’s
    prerequisite patterns and the file name. The directories are ignored only for the
    purpose of finding an implicit rule to use, not in the application of that rule.
    Thus, ‘e%t’ matches the file name src/eat, with ‘src/a’ as the stem. When
    prerequisites are turned into file names, the directories from the stem are added at
    the front, while the rest of the stem is substituted for the ‘%’. The stem ‘src/a’
    with a prerequisite pattern ‘c%r’ gives the file name src/car."
    """

    matched_input_files = []
    output_files = []
    unmatched_input_files = []
    regex = f"^{in_pattern.replace('%', '(.+)')}$"
    matcher = re.compile(regex)

    for input_file in input_files:
        input_file_head, input_file_tail = os.path.split(input_file)
        target_pattern_head, _ = os.path.split(target_pattern)

        outfilename = ""

        if target_pattern_head:
            # Target pattern has a directory, so compare them including directories
            match_object = matcher.match(input_file)
            if match_object:
                stem = match_object.group(1)
                outfilename = target_pattern.replace("%", stem)
        else:
            # Target pattern does not have a directory, so strip each filename from the
            # directory part before comparing
            match_object = matcher.match(input_file_tail)
            if match_object:
                stem = match_object.group(1)
                outfilename = os.path.join(
                    input_file_head, target_pattern.replace("%", stem)
                )

        if outfilename:
            matched_input_files.append(input_file)
            output_files.append(outfilename)
        else:
            unmatched_input_files.append(input_file)

    return FileListsFromPattern(
        matched_input_files,
        output_files,
        unmatched_input_files,
    )
