"""
A build tool written in Python, where all actions can be written in Python.
"""

# PYTHON_ARGCOMPLETE_OK

import os

from loguru import logger

from bygg.cmd.dispatcher import bygg
from bygg.output.output import output_warning


def main():
    setup_logging()
    logger.info("Starting")
    try:
        return bygg()
    except KeyboardInterrupt:
        output_warning("Interrupted by user. Aborting.")
        return 1


def setup_logging():
    debug = str.lower(os.environ.get("DEBUG_BYGG", ""))

    if not debug:
        logger.disable("bygg")
        return

    logger.enable("bygg")

    # file or silent enables file debugging
    if "file" in debug or "silent" in debug:
        logger.add("debug_{time}.log")

    # Remove the default handler to silence stderr
    if "silent" in debug:
        logger.remove(0)


if __name__ == "__main__":
    main()
