from itertools import chain

from bygg.cmd.datastructures import ByggContext, SubProcessIpcDataTree
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


def display_tree(ctx: ByggContext, entry_points: list[str]):
    """
    Display the dependency tree for the given entry points.

    Example output:

    all_checks
    ├── check_inputs_outputs
    │   └── circular_C
    │       └── circular_B
    │           └── circular_A
    └── output_file_missing
        └── no_outputs_A
    """

    indent = 4
    style = TreeStyleUnicode(indent)

    formatted_data: dict[str, str] = {}

    for entry_point in entry_points:
        build_actions = ctx.scheduler.build_actions

        def format_children(name: str, last_sibling: bool, depth: int) -> list[str]:
            action = build_actions[name]
            display_name = f"{TS.BOLD}{name}{TS.RESET}" if depth == 0 else name

            # Format children and flatten:
            children = chain.from_iterable(
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

        formatted_data[entry_point] = "\n".join(format_children(entry_point, True, 0))

        tree_data = SubProcessIpcDataTree(actions=formatted_data)
        if ctx.ipc_data:
            ctx.ipc_data.tree = tree_data
        else:
            print_tree(tree_data, entry_points)
    return len(entry_points) > 0


def print_tree(ipc_data_tree: SubProcessIpcDataTree, actions: list[str]):
    """Print the dependency tree from the IPC data."""
    actions_to_list = actions if actions else sorted(ipc_data_tree.actions.keys())
    trees = list(
        filter(
            lambda x: len(x) > 0,
            [ipc_data_tree.actions.get(a, "") for a in actions_to_list],
        )
    )
    if trees:
        print()
        print("\n".join(trees))
