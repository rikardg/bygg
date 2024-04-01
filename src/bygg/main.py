# PYTHON_ARGCOMPLETE_OK

from bygg.cmd.dispatcher import dispatcher
from bygg.output.output import output_warning


def main():
    try:
        return dispatcher()
    except KeyboardInterrupt:
        output_warning("Interrupted by user. Aborting.")
        return 1


if __name__ == "__main__":
    main()
