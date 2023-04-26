from pathlib import Path
import subprocess
import sys

import rich

from bygg.action import Action
from bygg.configuration import ByggFile, PreCommand, VenvSettings
from bygg.digest import calculate_string_digest
from bygg.util import create_shell_command


def calculate_requirements_hash(venv_settings: VenvSettings) -> str:
    requirements = []
    if venv_settings.create_venv_command:
        requirements.append(venv_settings.create_venv_command)
    if venv_settings.requirements_files:
        for requirements_file in venv_settings.requirements_files:
            with open(requirements_file, "r") as f:
                requirements += f.readlines()
    if venv_settings.requirements:
        requirements += venv_settings.requirements
    print(f"requirements: {requirements}")
    digest = calculate_string_digest(" ".join(requirements))
    print(f"requirements digest: {digest}")
    return digest


def apply_venv_settings(venv_settings: VenvSettings):
    if not venv_settings.manage_venv:
        return True

    venv_path = venv_settings.venv_path if venv_settings.venv_path else ".venv"

    requirements_hash = calculate_requirements_hash(venv_settings)
    requirements_hash_file = Path(venv_path) / "bygg_requirements_hash.txt"
    if requirements_hash_file.exists():
        with open(requirements_hash_file, "r") as f:
            if f.read() == requirements_hash:
                print("hashes match, skipping venv creation")
                return True
        requirements_hash_file.unlink()

    # TODO should we remove the whole venv or just trust pip to do the right thing? For
    # now, we'll just trust pip.

    command_string = (
        venv_settings.create_venv_command
        if venv_settings.create_venv_command
        else f"python3 -m venv {venv_path}"
    )
    print(f"command_string: {command_string}")
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

    # packages

    reqfiles_string = (
        [f"-r { reqfile }" for reqfile in venv_settings.requirements_files]
        if venv_settings.requirements_files
        else ""
    )
    reqs_string = (
        " ".join(venv_settings.requirements) if venv_settings.requirements else ""
    )

    command_string = (
        f"{Path(venv_path) / 'bin' / 'pip'} install {reqfiles_string} {reqs_string}"
    )
    print(f"command_string: {command_string}")
    rich.print("[blue]Installing requirements[/blue]")
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

    with open(requirements_hash_file, "w") as f:
        f.write(requirements_hash)

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
