from pathlib import Path
import shutil
import textwrap

from bygg.output.output import (
    TerminalStyle as TS,
)

TEMPLATE_PATH = Path(__file__).parent.parent / "templates"


def complete_templates() -> list[str]:
    return [x.name for x in list_template_dirs()]


def describe_templates():
    terminal_cols, terminal_rows = shutil.get_terminal_size()
    output = [f"{TS.BOLD}Available templates:{TS.RESET}"]

    for name, description in [
        create_template_description(template) for template in list_template_dirs()
    ]:
        output.append(f"{TS.BOLD}{name}{TS.RESET}")
        for paragraph in description.split("\n\n"):
            output.append(
                textwrap.fill(
                    paragraph.strip(),
                    initial_indent="    ",
                    subsequent_indent="    ",
                    width=min(80, terminal_cols),
                )
            )

    print("\n\n".join(output))


def create_template_description(path: Path) -> tuple[str, str]:
    description_file = path / "description.txt"
    try:
        description = description_file.read_text("utf-8").strip()
    except FileNotFoundError:
        description = "No description provided"
    return path.name, description


def list_template_dirs():
    return (x for x in TEMPLATE_PATH.iterdir() if x.is_dir())
