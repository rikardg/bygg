from bygg.core.action import Action
from bygg.core.common_types import CommandStatus


class Job:
    name: str
    action: Action
    status: CommandStatus | None

    def __init__(self, action: Action):
        self.name = action.name
        self.action = action
        self.status = None

    def __repr__(self) -> str:
        return f'"{self.name}, status: {self.status.rc if self.status else "unknown"}"'

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return self.name

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Job) and self.name == __o.name
