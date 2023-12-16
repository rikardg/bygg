from abc import ABCMeta, abstractmethod
from collections import deque
from typing import Any, Dict, Iterable, List

from bygg.action import Action


class Dag(metaclass=ABCMeta):
    def __len__(self) -> int:
        return 0

    def clear(self):
        ...

    def remove_node(self, node: str):
        ...

    def build_action_graph(self, build_actions: Dict[str, Action], action: Action):
        ...

    @abstractmethod
    def get_ready_jobs(
        self,
        finished_jobs: Dict[str, Any],
        running_jobs: Dict[str, Any],
    ) -> List[str]:
        ...

    @abstractmethod
    def get_all_jobs(self) -> Iterable[str]:
        ...


class GtDag(Dag):
    def __init__(self):
        import graph  # type: ignore

        self.graph = graph.Graph()

    def __len__(self):
        nodes = self.graph.nodes()
        if nodes is None:
            return 0
        return len(nodes)

    def clear(self):
        nodes = self.graph.nodes()
        if nodes is None:
            return
        for n in nodes:
            self.graph.del_node(n)

    def remove_node(self, node: str):
        self.graph.del_node(node)

    def build_action_graph(self, build_actions: Dict[str, Action], action: Action):
        """Build the action graph."""
        queue = deque([action])
        while len(queue) > 0:
            a = queue.popleft()
            self.graph.add_node(a.name)
            for dependency in a.dependencies:
                dependency_action = build_actions.get(dependency)
                if not dependency_action:
                    raise ValueError(f"Action '{dependency}' not found")
                queue.append(dependency_action)
                self.graph.add_edge(a.name, dependency)

    def get_ready_jobs(
        self,
        finished_jobs: Dict[str, Any],
        running_jobs: Dict[str, Any],
    ) -> List[str]:
        nodes = self.graph.nodes()
        if nodes is None:
            return []
        if len(nodes) == 1 and (
            nodes[0] not in finished_jobs and nodes[0] not in running_jobs
        ):
            return nodes

        new_nodes = self.graph.nodes(out_degree=0)
        if new_nodes is None:
            return []

        new_jobs = [
            n for n in new_nodes if n not in finished_jobs and n not in running_jobs
        ]

        # print(f"new jobs: {len(new_jobs)}")
        return new_jobs

    def get_all_jobs(self) -> Iterable[str]:
        nodes = self.graph.nodes()
        if nodes is None:
            return []
        return nodes


def create_dag() -> Dag:
    return GtDag()
