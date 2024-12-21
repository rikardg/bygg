from bygg.cmd.argument_parsing import MaintenanceCommand
from bygg.cmd.configuration import Byggfile
from bygg.cmd.environments import remove_environments
from bygg.core.cache import Cache
from bygg.logging import logger
from bygg.output.output import output_info


def perform_maintenance(configuration: Byggfile, commands: list[MaintenanceCommand]):
    logger.debug("Maintenance commands: %s", commands)
    # Sorting for testability and tidyness
    unique_cmds = sorted(set(commands))

    while unique_cmds and (cmd := unique_cmds.pop()):
        match cmd:
            case "remove_cache":
                output_info("Removing cache")
                Cache.reset()
            case "remove_environments":
                output_info("Removing environments")
                remove_environments(configuration)
            case _:
                raise ValueError(f"Unknown maintenance command '{cmd}'")
