"""
A build tool written in Python, where all actions can be written in Python.
"""

# PYTHON_ARGCOMPLETE_OK

from bygg.cmd.dispatcher import bygg
from bygg.logutils import logger, setup_logging
from bygg.output.output import (
    TerminalStyle as TS,
)
from bygg.output.output import output_warning


def main():
    print(TS.HIDE_CURSOR, end="")
    setup_logging()
    logger.info("Starting")
    try:
        return bygg()
    except KeyboardInterrupt:
        output_warning("Interrupted by user. Aborting.")
        return 1
    finally:
        print(TS.SHOW_CURSOR, end="")


if __name__ == "__main__":
    main()
