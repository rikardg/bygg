import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
from typing import TYPE_CHECKING

from bygg.cmd.configuration import (
    DEFAULT_ENVIRONMENT_NAME,
    PYTHON_INPUTFILE,
    Byggfile,
    Environment,
)
from bygg.cmd.datastructures import ByggContext
from bygg.core.action import Action
from bygg.core.digest import calculate_string_digest
from bygg.logging import logger
from bygg.output.output import output_error, output_info, output_plain
from bygg.util import create_shell_command


def calculate_environment_hash(environment: Environment) -> str:
    requirements: list[str] = []
    requirements.append(environment.shell)
    if environment.inputs:
        for input in environment.inputs:
            with open(input, "r") as f:
                requirements += f.readlines()
    return calculate_string_digest(" ".join(requirements))


def should_restart_with(environment: Environment) -> str | None:
    """Returns the path to the bygg file to restart with if it's not the one in the
    already loaded environment; in that case returns None."""
    venv_bin_path = Path(environment.venv_directory) / "bin"

    # # TODO: we could check here if the new venv is using the same Python binary that
    # # we're already running under, and if so just activate the venv.

    is_relative = Path(sys.executable).is_relative_to(venv_bin_path.resolve())
    if not is_relative:
        return str((venv_bin_path / "bygg"))
    return None


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

    environment_name = f' "{environment.name}" ' if environment.name else " "

    if venv_path.exists():
        output_info(f"Replacing venv{environment_name}at {venv_path}")
        shutil.rmtree(venv_path)

    output_info(f"Setting up environment{environment_name}in {venv_path}")
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


def remove_environments(configuration: Byggfile) -> list[str]:
    removed_environments: list[str] = []
    for name, env in configuration.environments.items():
        venv_path = Path(env.venv_directory)
        if venv_path.exists():
            output_info(f"Removing venv {name} at {venv_path}")
            shutil.rmtree(venv_path)
            removed_environments.append(name)
    return removed_environments


def load_environment(ctx: ByggContext, environment_name: str):
    environment = ctx.configuration.environments.get(environment_name, None)

    # Now set up the actions for the current environment:
    register_actions_from_configuration(ctx.configuration, environment_name)

    # Evaluate the Python build file:

    # If the default Python byggfile is used in an environment, don't load it by default
    if environment_name == DEFAULT_ENVIRONMENT_NAME and PYTHON_INPUTFILE in {
        bf.byggfile for bf in ctx.configuration.environments.values()
    }:
        return None

    python_build_file = environment.byggfile if environment else PYTHON_INPUTFILE
    load_python_build_file(python_build_file)
    return None


def register_actions_from_configuration(
    configuration: Byggfile, is_restarted_with_env: str | None
):
    logger.info(
        "Registering actions from configuration for '%s'", is_restarted_with_env
    )
    for action_name, action in configuration.actions.items():
        if TYPE_CHECKING:
            assert not isinstance(action, str)

        if is_restarted_with_env and action.environment != is_restarted_with_env:
            logger.info(
                "Skipping action '%s' for environment '%s', it belongs to '%s'",
                action_name,
                is_restarted_with_env,
                action.environment,
            )
            continue

        logger.info("Registering action '%s'", action_name)
        logger.debug("Action: %s", action)
        shell_command = (
            create_shell_command(action.shell, action.message) if action.shell else None
        )
        Action(
            action_name,
            # Use the shell command as fallback for the description
            description=action.description or f"`{action.shell}`",
            is_entrypoint=bool(action.is_entrypoint),
            inputs=action.inputs,
            outputs=action.outputs,
            dependencies=action.dependencies,
            command=shell_command,
        )


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
