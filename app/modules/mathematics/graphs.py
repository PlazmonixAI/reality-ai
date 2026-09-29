"""Graph algorithms: shortest paths (Dijkstra, or Bellman-Ford when weights are negative) and minimum
spanning trees (Kruskal), with the step order for animation."""
import heapq
import math

from app.core.registry import tool


def _edges(edges: list, directed: bool) -> tuple[set, list[tuple]]:
    nodes, out = set(), []
    for e in edges:
        if len(e) not in (2, 3):
            raise ValueError("each edge is [from, to] or [from, to, weight]")
        u, v = str(e[0]), str(e[1])
        w = float(e[2]) if len(e) == 3 else 1.0
        if not math.isfinite(w):
            raise ValueError("edge weights must be finite")
        nodes |= {u, v}
        out.append((u, v, w))
        if not directed:
            out.append((v, u, w))
    return nodes, out


@tool(
    domain="mathematics",
    name="shortest_path",
    description=(
        "Shortest paths in a weighted graph. edges: list of [from, to, weight]; directed or undirected. Uses "
        "Dijkstra for non-negative weights and Bellman-Ford otherwise (detects negative cycles). Returns the "
        "distance and path to target (if given), all distances, predecessors and the order nodes were settled. "
        "Example: edges=[['A','B',4],['A','C',2],['C','B',1],['B','D',5]], source='A', target='D'."
    ),
)
def shortest_path(edges: list, source: str, target: str | None = None, directed: bool = False) -> dict:
    if not edges:
        raise ValueError("give at least one edge")
    if len(edges) > 20_000:
        raise ValueError("at most 20000 edges")
    nodes, arcs = _edges(edges, directed)
    source = str(source)
    if source not in nodes:
        raise ValueError(f"source {source!r} is not in the graph")
    if target is not None and str(target) not in nodes:
        raise ValueError(f"target {target!r} is not in the graph")
    dist = {n: math.inf for n in nodes}
    prev: dict[str, str | None] = {n: None for n in nodes}
    dist[source] = 0.0
    order: list[dict] = []
    negative = any(w < 0 for _, _, w in arcs)
    if negative:
        if not directed:
            raise ValueError("an undirected negative edge is a negative cycle; shortest paths are undefined")
        algorithm = "bellman-ford"
        for _ in range(len(nodes) - 1):
            changed = False
            for u, v, w in arcs:
                if dist[u] + w < dist[v]:
                    dist[v], prev[v], changed = dist[u] + w, u, True
            if not changed:
                break
        for u, v, w in arcs:
            if dist[u] + w < dist[v] - 1e-12:
                raise ValueError("the graph has a negative cycle reachable from the source; shortest paths are undefined")
        order = [{"node": n, "distance": dist[n]} for n in sorted(nodes, key=lambda n: dist[n]) if dist[n] < math.inf]
    else:
        algorithm = "dijkstra"
        adj: dict[str, list] = {n: [] for n in nodes}
        for u, v, w in arcs:
            adj[u].append((v, w))
        heap, done = [(0.0, source)], set()
        while heap:
            d, u = heapq.heappop(heap)
            if u in done:
                continue
            done.add(u)
            order.append({"node": u, "distance": d, "via": prev[u]})
            for v, w in adj[u]:
                if d + w < dist[v]:
                    dist[v], prev[v] = d + w, u
                    heapq.heappush(heap, (dist[v], v))
    path, total = None, None
    if target is not None:
        t = str(target)
        if dist[t] < math.inf:
            path, n = [], t
            while n is not None:
                path.append(n)
                n = prev[n]
            path.reverse()
            total = dist[t]
    return {
        "result": {
            "algorithm": algorithm,
            "distance": total,
            "path": path,
            "reachable": target is None or total is not None,
            "distances": {n: (d if d < math.inf else None) for n, d in sorted(dist.items())},
            "predecessors": dict(sorted(prev.items())),
        },
        "order": order,
        "units": "same units as the edge weights",
        "assumptions": ["Path length is the sum of edge weights; unreachable nodes have distance null"],
    }


@tool(
    domain="mathematics",
    name="minimum_spanning_tree",
    description=(
        "Minimum spanning tree (forest, if disconnected) of an undirected weighted graph by Kruskal's algorithm. "
        "edges: list of [a, b, weight]. Returns the chosen edges in the order added and the total weight. "
        "Example: edges=[['A','B',1],['B','C',2],['A','C',3]]."
    ),
)
def minimum_spanning_tree(edges: list) -> dict:
    if not edges:
        raise ValueError("give at least one edge")
    nodes, arcs = _edges(edges, directed=True)
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    chosen, rejected = [], []
    for u, v, w in sorted(arcs, key=lambda e: e[2]):
        ru, rv = find(u), find(v)
        if ru == rv:
            rejected.append([u, v, w])
            continue
        parent[ru] = rv
        chosen.append([u, v, w])
    components = len({find(n) for n in nodes})
    return {
        "result": {
            "total_weight": sum(w for *_, w in chosen),
            "edges": chosen,
            "n_nodes": len(nodes),
            "components": components,
            "spanning_tree": components == 1,
        },
        "rejected": rejected,
        "units": "same units as the edge weights",
        "assumptions": ["Undirected graph; ties broken by input order (the total weight is unique either way)"],
    }
