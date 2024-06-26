import os
import random
import subprocess
import time

from bygg.core.action import Action, ActionContext, CommandStatus

# Modify these constants to change aspects of the test build:

# Directory for output files
LEVELLED_DIR_PATH = "t"

# How many levels to build up
TEST_LEVELS = 3

# How many files per level
TEST_FILES_PER_LEVEL = 50

# Do something more than just sort lines in files. This will calculate prime numbers.
GENERATE_LOAD = False

# Sleep in each job. Reduces throughput; useful to check logging and output. Don't sleep
# in CI.
ADD_SLEEP = False if "CI" in os.environ else True

# Execute touch <outfile> in a shell instead of sorting the test files in Python. This
# will cause work to be done by the process pool, but since the work is trivial, it
# won't hardly be noticeable.
USE_SHELL_COMMAND = False


def calculate_first_prime_numbers(count: int) -> list[int]:
    """Calculate the first n prime numbers."""
    primes: list[int] = []
    i = 2
    while len(primes) < count:
        if all(i % prime != 0 for prime in primes):
            primes.append(i)
        i += 1
    return primes


# Action function for sorting the input files.
def sort_lines(ctx: ActionContext):
    if not ctx.inputs:
        return CommandStatus(1, "No inputs.", None)

    changed_files: set[str] = set()
    output_lines: list[str] = []

    for input in ctx.inputs:
        output = input[:-3]
        output_lines.append(f"{input} -> {output}")
        with open(input, "r") as f:
            lines = f.readlines()
        lines.sort()
        with open(output, "w") as f:
            f.writelines(lines)
        changed_files.add(output)
    sleep_time = random.random() if ADD_SLEEP else 0
    output_lines.append(f"Slept for {sleep_time} seconds")
    time.sleep(sleep_time)

    if GENERATE_LOAD:
        calculate_first_prime_numbers(5000)
    return CommandStatus(0, "Sorted lines.", "\n".join(output_lines))


def shell_executor(command: str) -> tuple[int, str]:
    process = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    return process.returncode, process.stdout


def call_shell_command(ctx: ActionContext):
    sleep_time = random.random() if ADD_SLEEP else 0
    time.sleep(sleep_time)
    output_lines: list[str] = []
    rc_list: list[int] = []
    for output_file in ctx.outputs:
        rc, output = shell_executor(f"touch {output_file}")
        rc_list.append(rc)
        output_lines.append(output)
    return CommandStatus(
        max(rc_list),
        f"Touched output file in {sleep_time:.2f} s",
        "\n".join(output_lines),
    )


def generate_create_action(path: str):
    def action(ctx: ActionContext):
        if not os.path.isdir(LEVELLED_DIR_PATH):
            os.makedirs(LEVELLED_DIR_PATH, exist_ok=True)
        with open(path, "w") as f:
            f.write("foo\nbar\nbaz\n")
        return CommandStatus(0, "Created test file.", None)

    return action


def declare_test_files_actions():
    generated_files: list[str] = []
    generated_output_actions: list[Action] = []

    # Create a set of files with multiple dependency levels. In a real-world scenario,
    # these files would most likely already be present in the filesystem as source files
    # and listed out by a glob.

    def get_filename(level: int, file: int):
        return os.path.join(LEVELLED_DIR_PATH, f"l{level}f{file}.txt.in")

    for level in range(TEST_LEVELS):
        for file in range(TEST_FILES_PER_LEVEL):
            path = get_filename(level, file)
            generated_files += [path]

            Action(
                name=path,
                message=f"Creating test file {path}",
                inputs=None,
                outputs=[path],
                command=generate_create_action(path),
                scheduling_type="in-process",
            )

            # Add an action for an output file.
            output_file = path[:-3]
            name = output_file
            dependencies = [path]
            if level < TEST_LEVELS - 1:
                dependencies += [get_filename(level + 1, file)[:-3]]
            else:
                dependencies += []

            generated_output_actions += [
                Action(
                    name=name,
                    message=f"Sorting test file {path}",
                    inputs=[path],
                    outputs=[output_file],
                    dependencies=dependencies,
                    command=call_shell_command if USE_SHELL_COMMAND else sort_lines,
                )
            ]

    # Create the dummy input files
    Action(
        name="setup_test_files",
        outputs=generated_files,
        dependencies=[f for f in generated_files],
        message="Setting up test files.",
    )

    # Perform a "build" job (execute all the sort actions)
    Action(
        name="sort_test_files",
        dependencies=[
            a.name
            for a in generated_output_actions
            if a.name.startswith(f"{LEVELLED_DIR_PATH}/l0")
        ],
        outputs=["t"],
        message="Sorting test files.",
    )


declare_test_files_actions()


if __name__ == "__main__":
    declare_test_files_actions()
