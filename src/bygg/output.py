import sys

isatty = sys.stdout.isatty()


class TerminalStyle:
    """Terminal Text Styling"""

    RESET = "\033[0m" if isatty else ""
    BOLD = "\033[1m" if isatty else ""
    DIM = "\033[2m" if isatty else ""
    UNDERLINE = "\033[4m" if isatty else ""
    BLINK = "\033[5m" if isatty else ""
    INVERTED = "\033[7m" if isatty else ""
    STRIKETHROUGH = "\033[9m" if isatty else ""

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


def output_info(s: str):
    print(f"{TerminalStyle.Fg.BLUE}{s}{TerminalStyle.Fg.RESET}")


def output_warning(s: str):
    print(f"{TerminalStyle.Fg.YELLOW}{s}{TerminalStyle.Fg.RESET}")


def output_error(s: str):
    print(f"{TerminalStyle.Fg.RED}{s}{TerminalStyle.Fg.RESET}")


def output_ok(s: str):
    print(f"{TerminalStyle.Fg.GREEN}{s}{TerminalStyle.Fg.RESET}")


def output_plain(s: str):
    print(s)
