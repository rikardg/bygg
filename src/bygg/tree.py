from itertools import chain
from typing import List

from bygg.output import TerminalStyle as TS
from bygg.scheduler import Scheduler


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


def display_tree(scheduler: Scheduler, entry_points: List[str]):
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

    for entry_point in entry_points:
        build_actions = scheduler.build_actions

        def format_children(name: str, last_sibling: bool, depth: int) -> List[str]:
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

        print()
        print("\n".join(format_children(entry_point, True, 0)))
    return True
