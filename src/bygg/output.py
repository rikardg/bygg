import rich


def output_info(s: str):
    rich.print(f"[blue]{s}[/blue]")


def output_warning(s: str):
    rich.print(f"[yellow]{s}[/yellow]")


def output_error(s: str):
    rich.print(f"[red]{s}[/red]")


def output_ok(s: str):
    rich.print(f"[green]{s}[/green]")


def output_plain(s: str):
    rich.print(s)
