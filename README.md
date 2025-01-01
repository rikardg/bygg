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

Bygg requires Python 3.11 or higher.

Install with

`pipx install bygg` (recommended)
or
`pip install bygg`

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
def a_build_command(ctx: ActionContext):
    # do stuff
    ...


# Separate function + Action constructor:

def also_a_build_command(ctx: ActionContext):
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

### Environments

Bygg can manage virtual environments. See `examples/environments/Byggfile.yml`
for an example.

Python files and the actions declared therein will run in the environment that
the Python file was declared to belong to in the static configuration.

No environment will be managed or loaded implicitly for actions that are
declared in the static configuration. Actions that need an environment must
declare the `environment` property.

Any `shell` commands will need to have their respective environments activated
as needed (e.g. by prefacing them with `. .venv/bin/activate`) even if they are
declared from Python code that runs in an environment. This is because shells
are not intrinsically aware of virtual environments.

### Settings files

There is also support for declaring actions, environments and settings in YAML
and TOML files called `Byggfile.yml` and `Byggfile.toml`, respectively. This is
intended primarily for configuring static settings like which virtual
environment to use and their respective entrypoints, but can also be used for
declaring static actions. See `examples/taskrunner/Byggfile.toml`,
`examples/taskrunner/Byggfile.yml` and `examples/environments/Byggfile.yml`.

The evaluation order is TOML -> YAML -> Python. Actions and settings declared
later will override earlier ones.

## Shell tab completions

Bygg has support for Bash and Zsh tab completions of arguments and entrypoint
actions. The completions will be loaded from the files that exist out of
`Byggfile.toml`, `Byggfile.yml` and `Byggfile.py`, in that order.

Any environments declared in the static config files will be installed as
needed and their respective Byggfiles will be evaluated to collect entrypoint
actions.

To install completions, do:

```shell
bygg --completions
```

It will output a line that you can then add to `.bashrc` or `.zshrc`.

_Don't forget to open a new shell instance after you've made changes to the
settings files._

Note: if you reinstall Bygg with `pipx`, the completions file will probably
have been removed, but the path to `bygg` will be the same. In this case, just
run the reinstalled `bygg` once to create the completions file and then restart
your shell. If the completions still don't work, you might have to compare the
output of `bygg --completions` with the settings in the shell configuration
file per above.

### Notes

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

If [uv](https://github.com/astral-sh/uv) is installed (e.g. with `pipx install uv`),
it will be used by `bootstrap.py` and the Bygg examples where relevant.
This will speed up project setup and test running. If `uv` is not installed,
regular `pip` will be used.

```shell
# Create a virtual environment and install Bygg into it together with its dependencies:
./bootstrap.py
# Activate the virtual environment:
. .venv/bin/activate
# Optional: install and activate shell completions for this specific Bygg installation:
eval "$(bygg --completions)"
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
Bygg's virtual environment since it manages its own virtual environments:

```shell
pipx install nox
```

or

```shell
pip install --user --upgrade nox
```

After that, run tests with

```shell
nox
```
