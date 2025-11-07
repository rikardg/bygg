# Usage

- [Structure](#Structure)
- [Actions](#Actions)

## Command line interface

### `ACTION [ACTION2, ACTION3, ...]`

To build a target (execute an action) and its dependencies, just type `bygg
ACTION`, e.g.

```shell
bygg myprogram
```

Any number of actions can be listed on the command line. Eachone will be built
one at the time in the order they were given. The dependencies in their
respective dependency trees will be built in parallel.

The actions on the command line can use different environments if needed --
there is no restriction that they need to use the same one.

Executing `bygg` with no arguments will build the default action if one is set,
and otherwise give an error.

### `--clean`

Removes all files declared as outputs from the stated entrypoint (or default)
action and its dependencies.

### `-l`, `--list`

Lists the available entrypoint actions. Note that declaring an action as being
an entrypoint only affects the content of this list; any action can still be
built from the command line.

### `--tree`

Displays the dependency tree of the given (or default) action.

### `-h`, `--help`

Displays brief help for the available command line options.

### `-v`, `--version`

Prints the version.

## Execution model

Bygg will go through the `Action`s and check their dependencies on other
`Action`s. Based on this information it will build up a DAG (Directed Acyclic
Graph). When asked to build/execute an entrypoint action from the command line,
Bygg will execute each of the dependencies to the entrypoint, starting from the
leaf nodes of the graph (the nodes without any dependencies).

### Doing less work

Each `Action` declares its input and output files. Bygg will store the hash
digests of these files between builds. If the input and output hashes match,
the `Action` can safely be skipped.

This means that we have to declare all relevant input and output files
correctly, or at least sufficiently so.

## Structure

### Starting points

#### `Byggfile.py`

Bygg will check for the presence of `Byggfile.py` in the current directory. The
actions above would be built with `bygg build1` and `bygg build2`,
respectively. See the `examples/` directory for worked examples.

#### `Byggfile.yml`

There is also support for declaring actions in a YAML settings file,
`Byggfile.yml`. This is intended primarily for configuring static settings like
which virtual environment to use and their respective entrypoints, but can also
be used for declaring other (static) actions. See
`examples/taskrunner/Byggfile.yml` and `examples/environments/Byggfile.yml`.

### Expanding

#### Choose another directory

- Avoid `bygg` for Python reasons.
- `__init__.py` to mark it as a package.

## Actions

Actions are the basic building blocks in Bygg. From the user perspective they
are regular Python functions. There are no restrictions on what they can do.

Specify the actions in `Byggfile.py` in your source directory. Either wrap the
action function using the `@action` decorator, or use the `Action` constructor
directly.

### Entrypoints

### Examples

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

### Wrapping shell commands

There is nothing magic in Bygg with calling shell commands, but there is a
utility function `create_shell_command` that abstracts away having to call
`subprocess.run` directly.

### Calling Python code
