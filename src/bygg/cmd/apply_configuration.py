import os
from pathlib import Path
import sys
import textwrap
from typing import TYPE_CHECKING

from bygg.cmd.configuration import PYTHON_INPUTFILE, Byggfile, Environment
from bygg.cmd.environments import setup_environment
from bygg.core.action import Action
from bygg.logging import logger
from bygg.util import create_shell_command


def should_restart_with(environment: Environment) -> str | None:
    venv_bin_path = Path(environment.venv_directory) / "bin"

    # # TODO: we could check here if the new venv is using the same Python binary that
    # # we're already running under, and if so just activate the venv.

    is_relative = Path(sys.executable).is_relative_to(venv_bin_path.resolve())
    if not is_relative:
        return str((venv_bin_path / "bygg"))
    return None


def register_actions_from_configuration(
    configuration: Byggfile, is_restarted_with_env: str | None
):
    logger.info(
        "Registering actions from configuration for '%s'", is_restarted_with_env
    )
    for action_name, action in configuration.actions.items():
        logger.debug("Action '%s'", action_name)
        if TYPE_CHECKING:
            assert not isinstance(action, str)

        if is_restarted_with_env and action.environment != is_restarted_with_env:
            logger.debug(
                "Skipping action '%s' for environment '%s', it belongs to '%s'",
                action_name,
                is_restarted_with_env,
                action.environment,
            )
            continue

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


def apply_configuration(
    configuration: Byggfile,
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
