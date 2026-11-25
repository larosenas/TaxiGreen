
from typing import Dict, List, Optional, Tuple
import heapq

def _adj(graph: Dict[str, Dict[str, Tuple[float,float]]] , u: str):
    return graph.get(u, {}).items()

def _build_graph(world):
    g: Dict[str, Dict[str, Tuple[float,float]]] = {}
    for e in world.edges:
        g.setdefault(e.src, {})[e.dst] = (float(e.travel_min), float(e.distance_km))
    return g

def _build_rev_graph(world):
    g: Dict[str, Dict[str, Tuple[float,float]]] = {}
    for e in world.edges:
        g.setdefault(e.dst, {})[e.src] = (float(e.travel_min), float(e.distance_km))
    return g

# Potenciales: tiempo mínimo hasta goal en grafo inverso (Dijkstra)
_heur_cache: Dict[Tuple[str,str], Dict[str,float]] = {}

def _potentials_to_goal(world, goal: str) -> Dict[str, float]:
    key = ("timepot", goal)
    if key in _heur_cache:
        return _heur_cache[key]
    rev = _build_rev_graph(world)
    dist = {goal: 0.0}
    pq = [(0.0, goal)]
    while pq:
        d,u = heapq.heappop(pq)
        if d != dist[u]:
            continue
        for v,(w,_) in rev.get(u, {}).items():
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd,v))
    _heur_cache[key] = dist
    return dist

def shortest_path_by_time(world, origin: str, goal: str, mode: str = "ucs") -> Optional[Tuple[List[str], float]]:
    graph = _build_graph(world)
    if origin == goal:
        return [origin], 0.0
    if mode not in ("ucs","astar"):
        mode = "ucs"

    def reconstruct(best, goal):
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = best[cur][1]
        path.reverse()
        return path

    if mode == "ucs":
        pq = [(0.0, origin)]
        best = {origin: (0.0, None)}
        while pq:
            d,u = heapq.heappop(pq)
            if u == goal:
                return reconstruct(best, goal), d
            if d != best[u][0]:
                continue
            for v,(w,_) in _adj(graph, u):
                nd = d + w
                if v not in best or nd < best[v][0]:
                    best[v] = (nd, u)
                    heapq.heappush(pq, (nd, v))
        return None

    # A* con h(v) = potencial a goal (minutos)
    pot = _potentials_to_goal(world, goal)
    pq = [(pot.get(origin, float('inf')), 0.0, origin)]
    best = {origin: (0.0, None)}
    while pq:
        f,g,u = heapq.heappop(pq)
        if u == goal:
            return reconstruct(best, goal), g
        if g != best[u][0]:
            continue
        for v,(w,_) in _adj(graph, u):
            ng = g + w
            if v not in best or ng < best[v][0]:
                best[v] = (ng, u)
                fv = ng + pot.get(v, float('inf'))
                heapq.heappush(pq, (fv, ng, v))
    return None
