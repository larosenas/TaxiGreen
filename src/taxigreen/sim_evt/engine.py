
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional, TypeAlias
import heapq, math, random
from ..traffic import traffic_multiplier

SearchStats: TypeAlias = Dict[str, int]

def _bump(stats: Optional[SearchStats], key: str, inc: int = 1) -> None:
    if stats is not None:
        stats[key] = int(stats.get(key, 0)) + inc

@dataclass
class Edge:
    src: str
    dst: str
    distance_km: float
    travel_min: float

@dataclass
class Facility:
    id: str
    node_id: str
    type: str         # "gas" | "charger"
    service_min: int  # minutos de servicio
    capacity: int = 1
    down_until: int = 0  # si now < down_until => estación caída
    price_per_unit: Optional[float] = None

@dataclass
class Vehicle:
    id: str
    kind: str                 # "EV" | "ICE"
    energy_max: float
    energy_now: float
    consumption_per_km: float
    pos: str
    capacity: int = 4
    free_at: int = 0

@dataclass
class Request:
    id: str
    time: int
    origin: str
    destination: str
    vehicle_pref: str
    # Higher means more urgent. Used to order pending requests.
    priority: int = 0
    passengers: int = 1
    wait_max: Optional[int] = None
    pref_env: Optional[str] = None
    status: str = "scheduled"
    attempts: int = 0
    next_try: int = 0

@dataclass
class World:
    nodes: List[str]
    adj: Dict[str, List[Edge]]
    facilities: List[Facility]
    vehicles: List[Vehicle]
    cost: Dict[str, Any]
    policy: str = "fast"
    path_mode: str = "ucs"
    # Estado de ocupación de estaciones: facility_id -> lista de tiempos de fin de servicio
    facility_servers: Dict[str, List[int]] = field(default_factory=dict)
    search_stats: Dict[str, int] = field(default_factory=dict)  

def dijkstra_time(world: World, start: str, goal: str, stats: Optional[SearchStats] = None) -> Optional[Tuple[List[str], float]]:
    if start == goal:
        return ([start], 0.0)
    if start not in world.adj or goal not in world.nodes:
        return None   
    _bump(stats, "path_calls")
    dist = {start: 0.0}
    prev = {}
    pq = [(0.0, start)]
    while pq:
        d,u = heapq.heappop(pq)
        _bump(stats, "pops")
        if u == goal:
            break
        if d > dist.get(u, math.inf):
            continue
        _bump(stats, "expansions")
        for e in world.adj.get(u, []):
            v = e.dst
            nd = d + float(e.travel_min)
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                _bump(stats, "pushes")
                heapq.heappush(pq, (nd, v))
    if goal not in dist:
        return None
    # reconstrucción
    path = [goal]
    cur = goal
    while cur != start:
        cur = prev[cur]
        path.append(cur)
    path.reverse()
    return (path, dist[goal])

def _min_edge_time(world: World) -> float:
    m = math.inf
    for edges in world.adj.values():
        for e in edges:
            if e.travel_min > 0:
                m = min(m, float(e.travel_min))
    return 0.0 if m is math.inf else m

def _hop_lb(world: World, start: str, goal: str) -> Optional[int]:
    from collections import deque
    if start == goal:
        return 0
    q = deque([start]); seen={start}; depth={start:0}
    while q:
        u=q.popleft()
        for e in world.adj.get(u, []):
            v=e.dst
            if v in seen: 
                continue
            seen.add(v); depth[v]=depth[u]+1
            if v==goal: return depth[v]
            q.append(v)
    return None

def astar_time(world: World, start: str, goal: str, stats: Optional[SearchStats] = None) -> Optional[Tuple[List[str], float]]:
    if start == goal:
        return ([start], 0.0)
    _bump(stats, "path_calls")
    mmin = _min_edge_time(world)
    hop_cache = {}
    def h(n: str) -> float:
        _bump(stats, "heuristic_calls")
        hops = hop_cache.get(n)
        if hops is None:
            _bump(stats, "hop_lb_calls")
            hops = _hop_lb(world, n, goal)
            hop_cache[n] = hops
        if hops is None:
            return 0.0
        return hops * mmin
    
    openpq: List[Tuple[float, float, str, Optional[str]]] = [(h(start), 0.0, start, None)]

    g = {start: 0.0}
    prev = {}
    seen = set()

    while openpq:
        f, cost, u, par = heapq.heappop(openpq)
        _bump(stats, "pops")
        if u in seen: 
            continue
        prev[u] = par
        if u == goal: 
            break
        seen.add(u)
        _bump(stats, "expansions")
        for e in world.adj.get(u, []):
            v = e.dst
            ng = cost + float(e.travel_min)
            if ng < g.get(v, math.inf):
                g[v] = ng
                _bump(stats, "pushes")
                heapq.heappush(openpq, (ng + h(v), ng, v, u))

    if goal not in prev and goal not in g:
        return None

    path = [goal]
    cur = goal
    while cur != start:
        cur = prev.get(cur)
        if cur is None:
            return None
        path.append(cur)
    path.reverse()
    return (path, g.get(goal, 0.0))

def sum_path(world: World, v: Vehicle, nodes: List[str]) -> Tuple[float,float,float]:
    t = 0.0; km = 0.0
    for i in range(len(nodes)-1):
        found = None
        for e in world.adj.get(nodes[i], []):
            if e.dst == nodes[i+1]: 
                found = e; break
        if not found:
            raise ValueError("arista inexistente en ruta")
        t += float(found.travel_min)
        km += float(found.distance_km)
    en = km * float(v.consumption_per_km)
    return (t, en, km)

def energy_unit(v: Vehicle) -> str:
    return "kwh" if v.kind == "EV" else "liter"

def fac_kind_for(v: Vehicle) -> str:
    return "charger" if v.kind == "EV" else "gas"

def _shortest(world: World, a: str, b: str, mode: str):
    stats = getattr(world, "search_stats", None)
    return astar_time(world, a, b, stats=stats) if mode == "astar" else dijkstra_time(world, a, b, stats=stats)

def nearest_reachable_facility(world: World, v: Vehicle, mode: str):
    best = None
    for f in world.facilities:
        if f.type != fac_kind_for(v): 
            continue
        sp = _shortest(world, v.pos, f.node_id, mode)
        if sp is None: 
            continue
        nodes, t = sp
        try:
            _, en, _ = sum_path(world, v, nodes)
        except:
            continue
        if en <= v.energy_now:
            if best is None or t < best[1]:
                best = (nodes, t, f)
    return best

# Reserva un 'puesto' en la estación respetando capacidad.
# Devuelve (wait_min, end_t).
def queue_service(world: World, fac: Facility, arrival_t: int) -> Tuple[int, int]:
    ends = world.facility_servers.setdefault(fac.id, [])
    # liberar puestos que ya terminaron antes (o justo) de llegar
    ends[:] = [t for t in ends if t > arrival_t]

    cap = int(fac.capacity or 1)
    service = int(fac.service_min or 0)

    if len(ends) < cap:
        start = arrival_t
    else:
        start = min(ends)
        # liberar los que terminan exactamente en start
        ends[:] = [t for t in ends if t > start]

    wait = max(0, start - arrival_t)
    end_t = start + service
    ends.append(end_t)
    return wait, end_t

def drive_with_refuels(
    world: World, v: Vehicle, target: str, mode: str, now: int, metrics: dict, with_passenger: bool,
    rng: Optional[random.Random] = None, fail_p: float = 0.0, fail_min: int = 10, fail_max: int = 30
):
    while True:
        if v.pos == target:
            return True, now
        sp = _shortest(world, v.pos, target, mode)
        if sp is None:
            return False, now
        nodes, t_need = sp
        factor = traffic_multiplier(now)
        t_need_real = float(t_need) * factor
        try:
            _, e_need, km_need = sum_path(world, v, nodes)
        except:
            return False, now
        if e_need <= v.energy_now:
            v.pos = target
            v.energy_now -= e_need
            now += int(round(t_need_real))
            if with_passenger:
                metrics["km_pasajero"] += km_need; metrics["t_pasajero"] += t_need_real
            else:
                metrics["km_vacio"] += km_need; metrics["t_vacio"] += t_need_real
            metrics["energia_total"] += e_need
            return True, now
        best = nearest_reachable_facility(world, v, mode)
        if best is None:
            return False, now
        fac_nodes, t_fac, fac = best
        factor_fac = traffic_multiplier(now)
        t_fac_real = float(t_fac) * factor_fac
        try:
            _, e_fac, km_fac = sum_path(world, v, fac_nodes)
        except:
            return False, now
        v.pos = fac.node_id
        v.energy_now -= e_fac
        now += int(round(t_fac_real))
        metrics["km_vacio"] += km_fac; metrics["t_vacio"] += t_fac_real; metrics["energia_total"] += e_fac

        # 1) si la estación ya está caída, esperar a que vuelva
        down_until = int(getattr(fac, "down_until", 0))
        if now < down_until:
            dt = down_until - now
            metrics["t_facility_down_wait"] += float(dt)
            now = down_until

        # 2) fallo probabilístico al intentar usarla (solo si está UP)
        if fail_p > 0.0 and rng is not None and rng.random() < fail_p:
            dur = int(rng.randint(fail_min, fail_max))
            fac.down_until = now + dur
            metrics["facility_failures"] += 1
            metrics["t_facility_down_wait"] += float(dur)
            now = fac.down_until
        # 3) esperar turno en la estación    
        wait_min, end_t = queue_service(world, fac, now)

        # métricas nuevas
        metrics["t_facility_wait"] += float(wait_min)
        metrics["t_facility_service"] += float(getattr(fac, "service_min", 25))
        metrics["n_refuels"] += 1

        now = int(end_t)
        v.energy_now = float(v.energy_max)

def assign_and_execute(
    world: World, req: Request, v: Vehicle, mode: str, now: int,
    cost: Dict[str, Any], metrics_out: dict, response_start: int,
    rng: Optional[random.Random] = None, fail_p: float = 0.0, fail_min: int = 10, fail_max: int = 30
):
    m = {
    "km_vacio": 0.0, "km_pasajero": 0.0,
    "t_vacio": 0.0, "t_pasajero": 0.0,
    "t_facility_wait": 0.0, "t_facility_service": 0.0,
    "n_refuels": 0,
    "energia_total": 0.0, "co2_kg": 0.0, "costeu": 0.0,
    "t_facility_down_wait": 0.0,
    "facility_failures": 0
    }
    ok, now = drive_with_refuels(world, v, req.origin, mode, now, m, with_passenger=False,
                                 rng=rng, fail_p=fail_p, fail_min=fail_min, fail_max=fail_max)                                 
    if not ok: 
        return False, now, m
    ok, now = drive_with_refuels(world, v, req.destination, mode, now, m, with_passenger=True,
                                 rng=rng, fail_p=fail_p, fail_min=fail_min, fail_max=fail_max)
    if not ok:
        return False, now, m
    per_km = float(cost.get("weights", {}).get("per_km", 0.8))
    per_min = float(cost.get("weights", {}).get("per_min", 0.1))
    p_energy = float(cost.get("pricing", {}).get(energy_unit(v), 0.25 if v.kind=='EV' else 1.7))
    co2_ice = float(cost.get("co2_per_km_ice", 0.12))
    co2_ev  = float(cost.get("co2_per_km_ev", 0.02))
    t_total = (m["t_vacio"] + m["t_pasajero"] +
               m["t_facility_wait"] + m["t_facility_service"] +
               m["t_facility_down_wait"])
    km_total = m["km_vacio"] + m["km_pasajero"]
    coste = km_total*per_km + t_total*per_min + m["energia_total"]*p_energy
    m["costeu"] = coste
    m["co2_kg"] = (m["km_vacio"]+m["km_pasajero"]) * (co2_ice if v.kind=='ICE' else co2_ev)
    v.free_at = now
    metrics_out["viajes"] += 1
    for k in ["km_vacio","km_pasajero","t_vacio","t_pasajero",
            "t_facility_wait","t_facility_service","n_refuels",
            "t_facility_down_wait","facility_failures",
            "energia_total","co2_kg","costeu"]:     
        metrics_out[k] += m[k]
    metrics_out["tiempos_respuesta"].append(max(0, response_start - req.time))
    return True, now, m
