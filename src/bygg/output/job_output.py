from dataclasses import dataclass
import re

from bygg.core.scheduler import Job
from bygg.output.output import TerminalStyle as TS
from bygg.output.output import isatty, output_plain


@dataclass
class HighlightConfig:
    pattern: str | re.Pattern[str]
    start: str
    end: str


warning_hl_config = HighlightConfig(
    pattern=r"(warn\w*:?|WARN\w*:?)",
    start=TS.Bg.YELLOW + TS.Fg.BLACK,
    end=TS.Fg.RESET + TS.Bg.RESET,
)

error_hl_config = HighlightConfig(
    pattern=r"(error\w*:?|ERR!)",
    start=TS.Bg.RED,
    end=TS.Fg.RESET + TS.Bg.RESET,
)

default_highlight_config: list[HighlightConfig] = [warning_hl_config, error_hl_config]


def highlight_log(message: str, config: list[HighlightConfig] | None = None):
    """
    Highlights the message according to the regexes and styles. Regexes are applied
    per line.
    """
    if not config:
        return message

    lines = []
    for line in message.splitlines():
        for c in config:
            line = re.sub(c.pattern, c.start + r"\1" + c.end, line, flags=re.IGNORECASE)
        lines.append(line)
    return "\n".join(lines)


def output_job_logs(jobs: list[Job]):
    print(
        f"\n{TS.BOLD}Showing logs for {len(jobs)} failed job{'s' if len(jobs) > 1 else ''}:{TS.RESET}\n"
    )
    for job in jobs:
        if job.status and (log := job.status.output):
            output_plain(f'{TS.BOLD}--- Start "{ job.name }" ---{TS.RESET}')
            output_plain(
                highlight_log(log, default_highlight_config) if isatty else log
            )
            output_plain(f'{TS.BOLD}--- End "{ job.name}" ---{TS.RESET}')
            output_plain("")
