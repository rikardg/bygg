import sys

isatty = sys.stdout.isatty()


class TerminalStyle:
    """Terminal Text Styling"""

    CLEARLINE = "\033[2K\r" if isatty else ""
    RESET = "\033[0m" if isatty else ""
    BOLD = "\033[1m" if isatty else ""
    NOBOLD = "\033[22m" if isatty else ""
    DIM = "\033[2m" if isatty else ""
    UNDERLINE = "\033[4m" if isatty else ""
    BLINK = "\033[5m" if isatty else ""
    INVERTED = "\033[7m" if isatty else ""
    STRIKETHROUGH = "\033[9m" if isatty else ""
    HIDE_CURSOR = "\033[?25l" if isatty else ""
    SHOW_CURSOR = "\033[?25h" if isatty else ""

    class Fg:
        """Foreground Text Color"""

        BLACK = "\033[30m" if isatty else ""
        RED = "\033[31m" if isatty else ""
        GREEN = "\033[32m" if isatty else ""
        YELLOW = "\033[33m" if isatty else ""
        BLUE = "\033[34m" if isatty else ""
        MAGENTA = "\033[35m" if isatty else ""
        CYAN = "\033[36m" if isatty else ""
        WHITE = "\033[37m" if isatty else ""
        RESET = "\033[39m" if isatty else ""

        BRIGHT_RED = "\033[91m" if isatty else ""
        BRIGHT_GREEN = "\033[92m" if isatty else ""
        BRIGHT_YELLOW = "\033[93m" if isatty else ""
        BRIGHT_BLUE = "\033[94m" if isatty else ""
        BRIGHT_MAGENTA = "\033[95m" if isatty else ""
        BRIGHT_CYAN = "\033[96m" if isatty else ""
        BRIGHT_WHITE = "\033[97m" if isatty else ""

    class Bg:
        """Background Text Color"""

        BLACK = "\033[40m" if isatty else ""
        RED = "\033[41m" if isatty else ""
        GREEN = "\033[42m" if isatty else ""
        YELLOW = "\033[43m" if isatty else ""
        BLUE = "\033[44m" if isatty else ""
        MAGENTA = "\033[45m" if isatty else ""
        CYAN = "\033[46m" if isatty else ""
        WHITE = "\033[47m" if isatty else ""
        RESET = "\033[49m" if isatty else ""

        BRIGHT_RED = "\033[101m" if isatty else ""
        BRIGHT_GREEN = "\033[102m" if isatty else ""
        BRIGHT_YELLOW = "\033[103m" if isatty else ""
        BRIGHT_BLUE = "\033[104m" if isatty else ""
        BRIGHT_MAGENTA = "\033[105m" if isatty else ""
        BRIGHT_CYAN = "\033[106m" if isatty else ""
        BRIGHT_WHITE = "\033[107m" if isatty else ""


def output_with_status_line(bottom: str | None, scroll: str | None):
    """
    Outputs a line of text at the bottom of the terminal which is cleared and reprinted,
    and another line of text that scrolls up.

    Only prints the latter if the terminal is not a tty.
    """
    if not isatty:
        print(scroll)
        return

    print(TerminalStyle.CLEARLINE, end="")

    if scroll is not None:
        print(scroll)
    print(bottom if bottom is not None else "", end="\r")


STATUS_TEXT_FIELD_WIDTH = 8


bygg_prefix_string = f"{TerminalStyle.Fg.BRIGHT_CYAN}{'bygg >>>':<{STATUS_TEXT_FIELD_WIDTH}}{TerminalStyle.Fg.RESET}{TerminalStyle.NOBOLD}"


def output_info(s: str):
    print(
        f"{bygg_prefix_string} {TerminalStyle.Fg.BRIGHT_CYAN}{s}{TerminalStyle.Fg.RESET}"
    )


def output_warning(s: str):
    print(
        f"{bygg_prefix_string} {TerminalStyle.Fg.BRIGHT_YELLOW}{s}{TerminalStyle.Fg.RESET}"
    )


def output_error(s: str):
    print(
        f"{bygg_prefix_string} {TerminalStyle.Fg.BRIGHT_RED}{s}{TerminalStyle.Fg.RESET}"
    )


def output_ok(s: str):
    print(
        f"{bygg_prefix_string} {TerminalStyle.Fg.BRIGHT_GREEN}{s}{TerminalStyle.Fg.RESET}"
    )


def output_plain(s: str):
    print(s)
