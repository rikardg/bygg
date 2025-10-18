from bygg.cmd.datastructures import (
    ByggContext,
    SubProcessIpcDataRenderTree,
    get_entrypoints,
)


def print_render_tree(
    ipc_data_render_tree: SubProcessIpcDataRenderTree, actions: list[str]
):
    actions_to_render = actions if actions else sorted(ipc_data_render_tree.actions)
    
    reachable_nodes = set()
    
    def collect_reachable(name: str):
        if name in reachable_nodes:
            return
        reachable_nodes.add(name)
        for dep in ipc_data_render_tree.actions.get(name, []):
            collect_reachable(dep)
    
    for action in actions_to_render:
        if action in ipc_data_render_tree.actions:
            collect_reachable(action)
    
    edges = []
    for action in sorted(reachable_nodes):
        dependencies = ipc_data_render_tree.actions.get(action, [])
        for dep in dependencies:
            edges.append(f'  "{action}" -> "{dep}";')
    
    if edges:
        print("digraph bygg {")
        print("\n".join(edges))
        print("}")


def render_tree_collect_for_environment(
    ctx: ByggContext, environment_name: str
) -> SubProcessIpcDataRenderTree:

    entrypoints = get_entrypoints(ctx, environment_name)
    
    graph_data: dict[str, list[str]] = {}
    
    def collect_dependencies(name: str, visited: set[str]):
        if name in visited:
            return
        visited.add(name)
        
        action = ctx.scheduler.build_actions[name]
        dependencies = sorted(action.dependencies)
        graph_data[name] = dependencies
        
        for dep in dependencies:
            collect_dependencies(dep, visited)
    
    for entrypoint in entrypoints:
        collect_dependencies(entrypoint.name, set())
    
    return SubProcessIpcDataRenderTree(actions=graph_data)
