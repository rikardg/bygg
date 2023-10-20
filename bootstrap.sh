#!/bin/sh

set -e

if [ ! -d ./.venv ] ; then
  echo "Creating Python virtualenv:"
  python3 -m venv .venv
fi

echo "Installing dependencies:"
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

echo "Installing myself:"
.venv/bin/pip install -e .
