import subprocess
import sys

import rich

from bygg.action import Action
from bygg.configuration import ByggFile, PreCommand, VenvSettings
from bygg.util import create_shell_command


def apply_venv_settings(venv_settings: VenvSettings):
    if not venv_settings.manage_venv or not venv_settings.create_venv_command:
        return True

    command_string = f"{venv_settings.create_venv_command} {venv_settings.venv_path if venv_settings.venv_path else '.venv'}"
    rich.print("[blue]Creating virtual environment[/blue]")
    process = subprocess.run(
        command_string,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )

    print(process.stdout)

    if process.returncode != 0:
        rich.print(
            f"[red bold]Error while creating virtual environment: [/red bold]{process.stdout}"
        )
        sys.exit(1)
    return True


def run_pre_command(pre_command: PreCommand) -> bool:
    if not pre_command.shell:
        return False

    rich.print(
        f"[blue]Running precommand: [/blue]{pre_command.message if pre_command.message else pre_command.shell}"
    )
    process = subprocess.run(
        pre_command.shell,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )

    print(process.stdout)

    if process.returncode != 0:
        rich.print(
            f"[red bold]Error while running precommand: [/red bold]{process.stdout}"
        )
        sys.exit(1)
    return True


def apply_configuration(configuration: ByggFile | None):
    if not configuration:
        return

    if configuration.settings.pre_command:
        run_pre_command(configuration.settings.pre_command)

    if configuration.settings.venv_settings:
        apply_venv_settings(configuration.settings.venv_settings)

    for action in configuration.actions:
        shell_command = (
            create_shell_command(action.shell, action.message) if action.shell else None
        )
        Action(
            action.name,
            is_entrypoint=bool(action.is_entrypoint),
            inputs=action.inputs,
            outputs=action.outputs,
            dependencies=action.dependencies,
            command=shell_command,
        )
