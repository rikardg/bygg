import itertools

from bygg.cmd.datastructures import SubProcessIpcDataTree, get_entrypoints
from bygg.output.output import TerminalStyle as TS


class TreeStyle:
    """Base class for tree styles."""

    BAR = "─"
    PIPE = "│"
    T_JOINT = "├"
    END_CORNER = "└"
    CONNECTOR = T_JOINT + BAR * 2 + " "
    HANGER = END_CORNER + BAR * 2 + " "


class TreeStyleUnicode(TreeStyle):
    """Same style as base class, but with parametrized indent."""

    def __init__(self, indent=4):
        self.CONNECTOR = (
            f"{self.T_JOINT + self.BAR * (indent - 1 - len(self.T_JOINT)):<{indent}}"
        )
        self.HANGER = f"{self.END_CORNER + self.BAR * (indent - 1 - len(self.END_CORNER)):<{indent}}"


class TreeStyleAscii(TreeStyle):
    """ASCII characters instead of unicode."""

    BAR = "-"
    PIPE = "|"
    T_JOINT = "+"
    END_CORNER = "\\"

    def __init__(self, indent=4):
        self.CONNECTOR = (
            f"{self.T_JOINT + self.BAR * (indent - 1 - len(self.T_JOINT)):<{indent}}"
        )
        self.HANGER = f"{self.END_CORNER + self.BAR * (indent - 1 - len(self.END_CORNER)):<{indent}}"


def print_tree(ipc_data_tree: SubProcessIpcDataTree, actions: list[str]):
    """Print the dependency tree from the IPC data."""
    actions_to_list = actions if actions else sorted(ipc_data_tree.actions)
    trees = [
        x for x in [ipc_data_tree.actions.get(a, "") for a in actions_to_list] if x
    ]
    if trees:
        # Python 3.11 f-strings don't support `\n`
        print("\n" + "\n".join(trees))


def tree_collect_for_environment(ctx) -> SubProcessIpcDataTree:
    """Collect the currently loaded entrypoints and render their respective dependency
    trees.

    Example output:

    all_checks
    ├── check_inputs_outputs
    │   └── circular_C
    │       └── circular_B
    │           └── circular_A
    └── output_file_missing
        └── no_outputs_A
    """

    entrypoints = get_entrypoints(ctx)

    indent = 4
    style = TreeStyleUnicode(indent)

    formatted_data: dict[str, str] = {}

    for entrypoint in entrypoints:

        def format_children(name: str, last_sibling: bool, depth: int) -> list[str]:
            action = ctx.scheduler.build_actions[name]
            display_name = f"{TS.BOLD}{name}{TS.RESET}" if depth == 0 else name

            # Format children and flatten:
            children = itertools.chain.from_iterable(
                (
                    format_children(dep, i == len(action.dependencies) - 1, depth + 1)
                    for i, dep in enumerate(sorted(action.dependencies))
                )
            )

            # Indent with the correct prefixes:
            prefix = style.HANGER if last_sibling else style.CONNECTOR
            subtree = [f"{prefix if depth > 0 else ''}{display_name}"]

            child_prefix = f"{style.PIPE if not last_sibling else ' ':<{indent}}"
            subtree.extend(
                [f"{child_prefix if depth > 0 else ''}{item}" for item in children]
            )
            return subtree

        formatted_data[entrypoint.name] = "\n".join(
            format_children(entrypoint.name, True, 0)
        )

    return SubProcessIpcDataTree(actions=formatted_data)
