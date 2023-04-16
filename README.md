# Bygg, a Python build system that gets out of your way

_Bygg is in early stage of development. It is usable and useful for its
currently implemented use cases. Feel free to try it out, but also expect
things to change and evolve. Comments and bug reports are welcome!_

## Introduction

Bygg is a build system implemented in and configured using Python. It is
general-purpose, but is aimed at those that use Python to glue together other
systems.

Bygg tries to get out of your way and be as thin as possible, while still
providing correctness and minimal rebuilds.

### Basics

- Specify actions in pure Python.
- Actions can depend on other actions.
- An action will be executed if the digests of its source or output files have
  changed.

## Installation

_Bygg currently requires Python 3.11. Support for earlier versions should be
straightforward but hasn't been prioritised; feel free to open an issue if you
need it._

Install globally with

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
    outputs=["foo.out", "bar.out"]
    is_entrypoint: True
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
  command=my_python_command
  is_entrypoint=True
)
```

Bygg will check for the presence of `Byggfile.py` in the current directory. The
actions above can be built with `bygg build1` and `bygg build2`, respectively.

### Settings file

There is also experimental support for declaring actions in a settings file
(currently YAML). This is intended primarily for configuring static settings
like which virtual environment to use, but can also be used for declaring
simple actions. See `examples/taskrunner/Byggfile.yml`.

## Getting a local copy

If you want to try out the examples or even develop Bygg itself, Bygg can be
tried out and worked on without installing it globally:

First, clone this repo and cd into it, then execute the commands below.
`bootstrap.sh` creates a virtual environment and installs Bygg into it together
with its dependencies.

```shell
./bootstrap.sh
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
bygg transform --clean` .
```

## Development

### Running tests

With Bygg's virtual environment activated per above, tests can be run from the root directory:

```shell
pytest
```

With the virtual environment _deactivated_, the full test suite (so far
synonymous to just running `pytest` though) can be run with `nox`. Nox should
be installed globally since it manages its own virtual environments:

```shell
pipx install nox
```

After that, run tests with

```shell
nox
```
