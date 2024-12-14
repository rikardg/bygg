"""
A build tool written in Python, where all actions can be written in Python.
"""

# PYTHON_ARGCOMPLETE_OK

from bygg.cmd.dispatcher import bygg
from bygg.logging import logger, setup_logging
from bygg.output.output import output_warning


def main():
    setup_logging()
    logger.info("Starting")
    try:
        return bygg()
    except KeyboardInterrupt:
        output_warning("Interrupted by user. Aborting.")
        return 1


if __name__ == "__main__":
    main()
