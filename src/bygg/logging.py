import datetime
import logging
import os

from bygg.output.output import TerminalStyle as TS


def __getattr__(name):
    if name == "logger":
        return logging.getLogger("bygg")
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


class CustomLogFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": TS.Fg.BLUE,
        "INFO": TS.Fg.GREEN,
        "WARNING": TS.Fg.YELLOW,
        "ERROR": TS.Fg.RED,
        "CRITICAL": TS.Fg.RED + TS.BOLD,
    }

    no_colors = False

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        no_colors: bool = False,
    ):
        super().__init__(fmt, datefmt)
        self.no_colors = no_colors

    def format(self, record: logging.LogRecord) -> str:
        # Doesn't care about the format string used when instantiating the logger
        level_color = self.COLORS.get(record.levelname, "")
        filename_width = 40
        # Add the length of the colour code so the width will be the same for no_colors
        color_filename_width = filename_width + len(TS.Fg.WHITE)

        filename = (
            f"{record.filename + ':' + str(record.lineno) :<{filename_width}}"
            if self.no_colors
            else f"{TS.Fg.CYAN}{record.filename + ':' + TS.Fg.WHITE + str(record.lineno) :<{color_filename_width}}{TS.RESET}"
        )

        message = record.getMessage()

        if self.no_colors:
            return f"{self.formatTime(record)} | {record.name} | {record.levelname:<8} | {filename} | {message}"

        return f"{self.formatTime(record)} | {TS.Fg.MAGENTA}{record.name}{TS.RESET} | {level_color}{record.levelname:<8}{TS.RESET} | {filename} | {message}"

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        formatted_time = super().formatTime(record, datefmt)
        if self.no_colors:
            return formatted_time
        return f"{TS.Fg.CYAN}{formatted_time}{TS.RESET}"


def setup_logging():
    debug = str.lower(os.environ.get("DEBUG_BYGG", ""))

    if not debug:
        logging.getLogger("bygg").disabled = True
        return

    logger = logging.getLogger("bygg")
    logger.setLevel(logging.DEBUG)

    if "silent" not in debug:
        colored_formatter = CustomLogFormatter()

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(colored_formatter)
        logger.addHandler(stream_handler)

    # file or silent enables file debugging
    if "file" in debug or "silent" in debug:
        bw_formatter = CustomLogFormatter(no_colors=True)

        iso_datetime = datetime.datetime.now().isoformat(timespec="seconds")
        file_handler = logging.FileHandler(f"debug_{iso_datetime}.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(bw_formatter)
        logger.addHandler(file_handler)

        # Create symlink to latest log
        latest_log_link = "debug_latest.log"
        if os.path.lexists(latest_log_link):
            os.unlink(latest_log_link)
        os.symlink(f"debug_{iso_datetime}.log", latest_log_link)

    logger.debug("Debug logging enabled")
