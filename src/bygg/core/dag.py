from abc import ABCMeta, abstractmethod
from collections import deque
from typing import Any, Iterable

from bygg.core.action import Action


class Dag(metaclass=ABCMeta):
    def __len__(self) -> int:
        return 0

    def clear(self): ...

    def remove_node(self, node: str): ...

    def build_action_graph(self, build_actions: dict[str, Action], action: Action): ...

    @abstractmethod
    def get_ready_jobs(
        self,
        finished_jobs: dict[str, Any],
        running_jobs: dict[str, Any],
    ) -> list[str]: ...

    @abstractmethod
    def get_all_jobs(self) -> Iterable[str]: ...


class ByggDag(Dag):
    nodes: dict[str, set[str]]

    def __init__(self):
        self.nodes = {}

    def __len__(self) -> int:
        return len(self.nodes)

    def clear(self):
        self.nodes.clear()

    def remove_node(self, node: str):
        self.nodes.pop(node, None)

    def build_action_graph(self, build_actions: dict[str, Action], action: Action):
        """Build the action graph."""
        queue = deque([action])
        while len(queue) > 0:
            a = queue.popleft()
            self.nodes[a.name] = set()
            for dependency in a.dependencies:
                dependency_action = build_actions.get(dependency)
                if not dependency_action:
                    raise ValueError(f"Action '{dependency}' not found")
                queue.append(dependency_action)
                self.nodes[a.name].add(dependency)

    def get_ready_jobs(
        self,
        finished_jobs: dict[str, Any],
        running_jobs: dict[str, Any],
    ) -> list[str]:
        nodes = set(self.nodes.keys())
        ready_jobs = []

        for node, dependencies in self.nodes.items():
            # Successful and skipped jobs will have been removed from the graph, while
            # failed jobs remain.
            if node in finished_jobs or node in running_jobs:
                continue
            # The job is ready to run if its dependencies are no longer in the graph.
            if len(nodes & dependencies) == 0:
                ready_jobs.append(node)
        return ready_jobs

    def get_all_jobs(self) -> Iterable[str]:
        return self.nodes.keys()


def create_dag() -> Dag:
    return ByggDag()
