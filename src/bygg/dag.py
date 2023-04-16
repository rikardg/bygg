from collections import deque
from typing import Any, Dict, Iterable, List, Set

from bygg.action import Action


class Dag:
    def __len__(self):
        return 0

    def clear(self):
        ...

    def remove_node(self, node: str):
        ...

    def build_action_graph(self, build_actions: Dict[str, Action], action: Action):
        ...

    def get_ready_jobs(
        self,
        finished_jobs: Dict[str, Any],
        running_jobs: Dict[str, Any],
    ) -> List[str]:
        ...

    def get_all_jobs(self) -> Iterable[str]:
        ...


class GraphlibDag(Dag):
    nodes: Set[str]

    def __init__(self):
        import graphlib

        self.graph = graphlib.TopologicalSorter()
        self.nodes = set()

    def __len__(self):
        return len(self.nodes)

    def clear(self):
        import graphlib

        self.graph = graphlib.TopologicalSorter()
        self.nodes = set()

    def remove_node(self, node: str):
        self.graph.done(node)
        self.nodes.remove(node)

    def build_action_graph(self, build_actions: Dict[str, Action], action: Action):
        """Build the action graph."""
        queue = deque([action])
        while len(queue) > 0:
            a = queue.popleft()
            self.graph.add(a.name)
            self.nodes.add(a.name)
            for dependency in a.dependencies:
                dependency_action = build_actions.get(dependency)
                if not dependency_action:
                    raise ValueError(f"Action '{dependency}' not found")
                queue.append(dependency_action)
                self.graph.add(a.name, dependency)
        self.graph.prepare()

    def get_ready_jobs(
        self,
        finished_jobs: Dict[str, Any],
        running_jobs: Dict[str, Any],
    ) -> List[str]:
        return list(self.graph.get_ready())

    def get_all_jobs(self) -> Iterable[str]:
        return list(self.nodes)


def create_dag() -> Dag:
    return GraphlibDag()
