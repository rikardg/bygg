import argparse
import functools


@functools.cache
def _build_dest_to_action(parser: argparse.ArgumentParser) -> dict:
    actions = parser._get_optional_actions() + parser._get_positional_actions()
    dest_to_action = {action.dest: action for action in actions}
    return dest_to_action


def _get_argument_for_dest(parser: argparse.ArgumentParser, dest: str) -> str | None:
    dest_to_action: dict[str, argparse.Action] = _build_dest_to_action(parser)
    action = dest_to_action.get(dest, None)
    if action is None:
        return None
    option_strings = action.option_strings
    return option_strings[-1] if option_strings else ""


def unparse_args(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    *,
    drop: list[str] | None = None,
) -> list[str]:
    """
    Convert an argparse.Namespace back to a list of command line arguments.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The parser that was used to parse the command line arguments.
    args : argparse.Namespace
        The parsed command line arguments to unparse.
    drop : list[str] | None, optional
        Which dest keys to drop, by default None.

    Returns
    -------
    list[str]
        A list of command line arguments
    """
    exec_list: list[str] = []
    for k, v in vars(args).items():
        argument = _get_argument_for_dest(parser, k)
        if drop and k in drop:
            continue
        if v is False or v is None:
            # These are arguments that were not given
            continue
        if v is True:
            # If argument is None, something wrong is broken in the argparse Namespace
            # and should be looked into.
            assert argument
            exec_list.append(argument)
        elif v:
            if argument:
                exec_list.append(
                    f"{argument}={','.join(v) if isinstance(v, (list, tuple)) else v}"
                )
            elif isinstance(v, (list, tuple)):
                exec_list.extend(v)
            else:
                assert False
        elif argument == "":
            continue
        else:
            # Could happen if we add another type of argument
            assert False
    return exec_list
