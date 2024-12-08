#!/usr/bin/env python3

from pathlib import Path
import shutil
import sys

from src.bygg.system_helpers import call

venv = Path(".venv")

uv_bin = shutil.which("uv")
venv_command = "python3 -m venv" if not uv_bin else f"{uv_bin} venv"
pip_install_command = ".venv/bin/pip install" if not uv_bin else f"{uv_bin} pip install --reinstall"

# Always remove existing venv, to make sure requirements are correctly installed.
if venv.exists():
    print(f"Removing existing {venv} directory")
    shutil.rmtree(venv)

print("Creating Python virtualenv")
s = call(f"{venv_command} {venv}")
if not s or not venv.exists():
    print("Failed to create Python virtualenv")
    sys.exit(s)

print("Installing requirements:")
s = call(f"{pip_install_command} -r requirements.txt -r requirements-dev.txt")
if not s:
    print("Failed to install requirements")
    sys.exit(s)

print("Installing myself:")
s = call(f"{pip_install_command} -e .")
if not s:
    print("Failed to install Bygg")
    sys.exit(s)
