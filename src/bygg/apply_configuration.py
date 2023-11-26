import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
from typing import List

from bygg.action import Action
from bygg.configuration import PYTHON_INPUTFILE, ByggFile, Environment
from bygg.digest import calculate_string_digest
from bygg.output import output_error, output_info, output_plain
from bygg.util import create_shell_command


def calculate_environment_hash(environment: Environment) -> str:
    requirements: List[str] = []
    requirements.append(environment.shell)
    if environment.inputs:
        for input in environment.inputs:
            with open(input, "r") as f:
                requirements += f.readlines()
    return calculate_string_digest(" ".join(requirements))


def setup_environment(environment: Environment):
    venv_path = Path(
        environment.venv_directory if environment.venv_directory else ".venv"
    )

    environment_hash = calculate_environment_hash(environment)
    environment_hash_file = venv_path / "bygg_environment_hash.txt"
    if environment_hash_file.exists():
        with open(environment_hash_file, "r") as f:
            if f.read() == environment_hash:
                return True
        environment_hash_file.unlink()

    # TODO should we remove the whole venv or just trust pip to do the right thing? For
    # now, remove the venv.

    if venv_path.exists():
        output_info(f"Replacing venv at {venv_path}")
        shutil.rmtree(venv_path)

    output_info("Setting up environment")
    process = subprocess.run(
        environment.shell,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )

    if process.returncode != 0:
        output_error("Error while creating virtual environment:")
        output_plain(process.stdout)
        sys.exit(1)

    with open(environment_hash_file, "w") as f:
        f.write(environment_hash)

    return True


def should_restart_with(environment: Environment) -> str | None:
    venv_bin_path = Path(environment.venv_directory) / "bin"

    # # TODO: we could check here if the new venv is using the same Python binary that
    # # we're already running under, and if so just activate the venv.

    is_relative = Path(sys.executable).is_relative_to(venv_bin_path.resolve())
    if not is_relative:
        return str((venv_bin_path / "bygg"))
    return None


def register_actions_from_configuration(
    configuration: ByggFile, is_restarted_with_env: str | None
):
    for action in configuration.actions:
        if is_restarted_with_env and action.environment != is_restarted_with_env:
            continue

        shell_command = (
            create_shell_command(action.shell, action.message) if action.shell else None
        )
        Action(
            action.name,
            description=action.description,
            is_entrypoint=bool(action.is_entrypoint),
            inputs=action.inputs,
            outputs=action.outputs,
            dependencies=action.dependencies,
            command=shell_command,
        )


def apply_configuration(
    configuration: ByggFile,
    environment_name: str | None,
    is_restarted_with_env: str | None,
) -> str | None:
    """Returns the path of the bygg install to restart with if a restart is needed."""

    environment = (
        configuration.environments[environment_name]
        if environment_name and environment_name in configuration.environments
        else None
    )

    # Check if we need to restart to run in a different environment:

    if not is_restarted_with_env and environment:
        setup_environment(environment)

        restart_with = should_restart_with(environment)
        if restart_with is not None:
            return restart_with

    # Now set up the actions for the current environment:
    register_actions_from_configuration(configuration, is_restarted_with_env)

    # Evaluate the Python build file:

    python_build_file = environment.byggfile if environment else PYTHON_INPUTFILE
    load_python_build_file(python_build_file)
    return None


def load_python_build_file(build_file: str):
    # modify load path to make the current directory importable
    preamble = """\
        import os
        import sys
        sys.path.insert(0, str(os.path.realpath('.')))

        """

    if os.path.isfile(build_file):
        with open(build_file, "r") as f:
            exec(textwrap.dedent(preamble) + f.read(), globals())
