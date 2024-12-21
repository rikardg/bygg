from pathlib import Path
import shutil
import subprocess
import sys

from bygg.cmd.configuration import Byggfile, Environment
from bygg.core.digest import calculate_string_digest
from bygg.output.output import output_error, output_info, output_plain


def calculate_environment_hash(environment: Environment) -> str:
    requirements: list[str] = []
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
