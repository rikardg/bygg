#!/usr/bin/env python3

from pathlib import Path
import shutil
import sys

from src.bygg.system_helpers import call

venv = Path(".venv")

# Always remove existing venv, to make sure requirements are correctly installed.
if venv.exists():
    print(f"Removing existing {venv} directory")
    shutil.rmtree(venv)

print("Creating Python virtualenv")
s = call(f"python3 -m venv {venv}")
if not s or not venv.exists():
    print("Failed to create Python virtualenv")
    sys.exit(s)

print("Installing requirements:")
s = call(".venv/bin/pip install -r requirements.txt -r requirements-dev.txt")
if not s:
    print("Failed to install requirements")
    sys.exit(s)

print("Installing myself:")
s = call(".venv/bin/pip install -e .")
if not s:
    print("Failed to install Bygg")
    sys.exit(s)
