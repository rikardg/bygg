<div align="center">

# Bygg

_a Python build system that gets out of your way_

[![PyPI](https://img.shields.io/pypi/v/bygg?flat)](https://pypi.org/project/bygg/)
[![GitHub Release Date](https://img.shields.io/github/release-date/rikardg/bygg)](https://github.com/rikardg/bygg/releases)
[![GitHub Workflow Status (with branch)](https://img.shields.io/github/actions/workflow/status/rikardg/bygg/code_quality.yml?branch=master&flat)](https://github.com/rikardg/bygg/actions?query=branch%3Amaster+)
![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Frikardg%2Fbygg%2Fmaster%2Fpyproject.toml)
[![GitHub](https://img.shields.io/github/license/rikardg/bygg)](LICENSE)

[Installation](#installation) • [Usage](#usage) • [Development](#development)

</div>

---

_Bygg is in early stage of development. It is usable and useful for its
currently implemented use cases. Feel free to try it out, but also expect
things to change and evolve. Feedback and bug reports are welcome!_

## Introduction

Bygg is a build system implemented in and configured using Python. It is
general-purpose, but is aimed at those that (want to) use Python to glue
together other systems.

Bygg tries to get out of your way and be as thin as possible, while still
providing correctness and minimal rebuilds.

### Basics

- Specify actions in pure Python.
- Actions can depend on other actions.
- An action will be executed if the digests of its source or output files have
  changed.

## Installation

Bygg requires Python 3.11 or 3.12.

Install with

`pip install bygg`
or
`pipx install bygg`

or in a virtual environment.

## Usage

Specify the actions in `Byggfile.py` in your source directory. Either wrap the
action function using the `@action` decorator, or use the `Action` constructor
directly.

```python

# Decorator:

@action(
    "build1",
    inputs=["foo.in", "bar.in"],
    outputs=["foo.out", "bar.out"],
    is_entrypoint=True
)
def a_build_command(ctx: Context):
    # do stuff
    ...


# Separate function + Action constructor:

def also_a_build_command(ctx: Context):
    # do stuff
    ...

Action(
    "build2",
    inputs=["foo.in", "bar.in"],
    outputs=["foo.out", "bar.out"],
    dependencies=["another action"],
    command=also_a_build_command,
    is_entrypoint=True
)
```

Bygg will check for the presence of `Byggfile.py` in the current directory. The
actions above would be built with `bygg build1` and `bygg build2`,
respectively. See the `examples/` directory for worked examples.

### Settings file

There is also support for declaring actions in a YAML settings file,
`Byggfile.yml`. This is intended primarily for configuring static settings like
which virtual environment to use and their respective entrypoints, but can also
be used for declaring other (static) actions. See
`examples/taskrunner/Byggfile.yml` and `examples/environments/Byggfile.yml`.

## Shell tab completions

TL;DR: `bygg --completions`

Bygg has support for Bash and Zsh tab completions of arguments and entrypoint
actions. The completions will be loaded:

- from `Byggfile.py` if `Byggfile.yml` doesn't exist, or if there are no
  environments declared in `Byggfile.yml`.
- from `Byggfile.yml` if it exists and has environments. In this case, only the
  entrypoint actions listed in `Byggfile.yml` will be loaded; no Python files
  will be loaded to look for entrypoint actions since this might require an
  lengthy (in the context) install of environments.

To install completions, do:

```shell
bygg --completions
```

It will output a line that you can then add to `.bashrc` or `.zshrc`.

_Don't forget to open a new shell instance after you've made changes to the
settings files._

<details>
<summary>
Manual steps
</summary>

Add the following line to `.bashrc` or `.zshrc`:

```shell
eval "$(.your_bygg_venv/bin/register-python-argcomplete .your_bygg_venv/bin/bygg)"
```

</details>

<details>
<summary>Note for Zsh + argcomplete v2 users</summary>

The recommended setup above uses the argcomplete that is installed with Bygg,
since this version (starting with v3) has proper support for Zsh so that the
action completions will show descriptions. If you for whatever reason need to
use a lower version of argcomplete you need to load the Bash compatibility
layer first, and then the Bygg completions:

```shell
autoload -U bashcompinit ; bashcompinit
eval "$(register-python-argcomplete bygg)"
```

</details>

## Getting a local copy

If you want to try out the examples or even develop Bygg itself, Bygg can be
tried out and worked on without installing it globally:

First, clone this repo and cd into it, then execute the commands below.
`bootstrap.py` creates a virtual environment and installs Bygg into it together
with its dependencies.

```shell
./bootstrap.py
. .venv/bin/activate
```

Now you can try out one of the examples:

```shell
cd examples/trivial
bygg transform
```

In the above, `bygg` is the command to execute `bygg`, and `transform` is an
action (much like a target in a `Makefile`). See `examples/trivial/Byggfile.py`
for details.

The target can be cleaned with

```shell
bygg transform --clean
```

## Development

### Running tests

With Bygg's virtual environment activated per above, tests can be run from the root directory:

```shell
pytest
```

With the virtual environment _deactivated_, the full test suite can be run with
[Nox](https://nox.thea.codes/en/stable/). Nox should be installed outside of
the virtual environment since it manages its own virtual environments:

```shell
pip install --user --upgrade nox
```

After that, run tests with

```shell
nox
```
