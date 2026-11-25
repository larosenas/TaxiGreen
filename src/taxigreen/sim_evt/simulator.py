from __future__ import annotations
from typing import List, Dict, Tuple, Optional
import json, os, csv, copy, random

from .engine import World, Vehicle, Facility, Edge, Request, dijkstra_time, astar_time, assign_and_execute, energy_unit , sum_path

def _load_json(path: str):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

DEFAULT_COST = {
  "weights": {"per_km": 0.8, "per_min": 0.1},
  "pricing": {"kwh": 0.25, "liter": 1.7},
  "co2_per_km_ice": 0.12,
  "co2_per_km_ev": 0.02
}

def _load_world(data_dir: str, vehicles_filename: str | None):
    
    nodes_raw = _load_json(os.path.join(data_dir, "nodes.json"))

    # nodes.json puede ser ["A","B",...] o [{"id":"A"}, {"id":"B"}, ...]
    if not isinstance(nodes_raw, list) or not nodes_raw:
        raise ValueError("nodes.json must be a non-empty list")

    if isinstance(nodes_raw[0], str):
        node_ids = nodes_raw
    elif isinstance(nodes_raw[0], dict):
        node_ids = []
        for n in nodes_raw:
            nid = n.get("id") or n.get("node_id") or n.get("name")
            if not isinstance(nid, str):
                raise ValueError(f"Invalid node entry (missing string id): {n!r}")
            node_ids.append(nid)
    else:
        raise ValueError(f"Unsupported nodes.json element type: {type(nodes_raw[0])}")

    edges_raw = _load_json(os.path.join(data_dir, "edges.json"))

    def key(d, k, alt):
        if k in d: return d[k]
        for a in alt:
            if a in d: return d[a]
        return None

    adj = {nid: [] for nid in node_ids}
    for e in edges_raw:
        src = e.get("src") or e.get("from")
        dst = e.get("dst") or e.get("to")

        if not isinstance(src, str) or not isinstance(dst, str):
            raise ValueError(f"Edge missing/invalid src/dst (expected src/dst or from/to): {e!r}")

        dk = float(e.get("distance_km", 1.0))
        tm = float(e.get("travel_min", 1.0))

        if src not in adj:
            raise ValueError(f"Edge src {src!r} not in nodes.json")
        if dst not in adj:
            raise ValueError(f"Edge dst {dst!r} not in nodes.json")

        adj[src].append(Edge(src, dst, dk, tm))

    facs = []
    fac_file = os.path.join(data_dir, "facilities.json")

    fr = []
    if os.path.exists(fac_file):
        fr = _load_json(fac_file)
    for idx, it in enumerate(fr):
        facs.append(Facility(
            id = it.get("id") or f"fac_{idx}",
            node_id = it.get("node_id") or it.get("node") or it.get("at"),
            type = it.get("type") or it.get("kind"),
            service_min = int(it.get("service_min", 25)),
            capacity = int(it.get("capacity", 1) or 1),
            price_per_unit = float(it["price_per_unit"]) if it.get("price_per_unit") is not None else None,
        ))


    vf = vehicles_filename or "vehicles.json"
    vr = _load_json(os.path.join(data_dir, vf))

    vehicles = []
    for it in vr:
        vehicles.append(Vehicle(
            id = it["id"],
            kind = it.get("kind") or it.get("type") or "EV",
            energy_max = float(it.get("energy_max", 10.0)),
            energy_now = float(it.get("energy_now", it.get("energy_max", 10.0))),
            consumption_per_km = float(it.get("consumption_per_km", 0.5)),
            pos = it.get("start_node") or it.get("node") or it.get("pos") or node_ids[0],
            # data/schemas use capacity_pax; keep backward-compat with capacity
            capacity = int(it.get("capacity_pax", it.get("capacity", 4))),
            free_at = 0
        ))

    # accept cost_model.json and cost.json)
    cost = copy.deepcopy(DEFAULT_COST)

    def merge(d, u):
        for k, v in u.items():
            if isinstance(v, dict):
                base = d.get(k, {})
                if not isinstance(base, dict):
                    base = {}
                d[k] = merge(base, v)
            else:
                d[k] = v
        return d

    for fname in ("cost_model.json", "cost.json"):
        cf = os.path.join(data_dir, fname)
        if os.path.exists(cf):
            try:
                loaded = _load_json(cf)
                cost = merge(copy.deepcopy(DEFAULT_COST), loaded)
            except Exception:
                cost = copy.deepcopy(DEFAULT_COST)
            break

    rr = _load_json(os.path.join(data_dir, "requests.json"))

    requests = []
    for it in rr:
        # data/schemas use t_min/pax/deadline_min; keep backward-compat with time/passengers/wait_max
        origin = it.get("origin") or it.get("src") or it.get("from")
        destination = it.get("destination") or it.get("dst") or it.get("to")
        raw_wait = it.get("deadline_min", it.get("wait_max"))

        requests.append(Request(
            id = it["id"],
            time = int(it.get("t_min", it.get("time", 0))),
            origin = origin,
            destination = destination,
            vehicle_pref = it.get("vehicle_pref", it.get("pref_vehicle", "any")),
            priority = int(it.get("priority", 0)),
            passengers = int(it.get("pax", it.get("passengers", 1))),
            wait_max = int(raw_wait) if raw_wait is not None else None,
            pref_env = it.get("pref_env")
        ))

    world = World(nodes=node_ids, adj=adj, facilities=facs, vehicles=vehicles, cost=cost)
    return world, requests

def _score(world: World, v: Vehicle, r: Request, t_origen: float, t_destino: float, coste_est: float):
    eco_penalty = 0.0
    if r.pref_env == "eco" and v.kind == "ICE":
        eco_penalty = 1000.0
    if world.policy == "cheap":
        return (coste_est + eco_penalty, t_origen + t_destino)
    if world.policy == "balance":
        return (0.5*(t_origen+t_destino) + coste_est + eco_penalty, )
    if world.policy == "nearest_origin":
        return (t_origen + eco_penalty, t_origen + t_destino)
    return (t_origen + t_destino + eco_penalty, )

def run_simulation(data_dir: str, path_mode: str = "ucs", policy: str = "fast",
                   max_retries: int = 3, cooldown_ticks: int = 30, vehicles_filename: str | None = None,
                   print_logs: bool = True, out_dir: Optional[str] = None,
                   seed: int = 0, fail_p: float = 0.0, fail_min: int = 10, fail_max: int = 30):
    world, scheduled = _load_world(data_dir, vehicles_filename)
    world.search_stats = {
    "path_calls": 0, "pops": 0, "pushes": 0, "expansions": 0,
    "heuristic_calls": 0, "hop_lb_calls": 0
    }
    rng = random.Random(seed)
    busy_time = {v.id: 0.0 for v in world.vehicles}
    world.policy = policy
    world.path_mode = path_mode

    metrics = {
        "viajes": 0, "km_vacio": 0.0, "km_pasajero": 0.0, "t_vacio": 0.0, "t_pasajero": 0.0,
        "energia_total": 0.0, "co2_kg": 0.0, "costeu": 0.0,
        "tiempos_respuesta": [],
        "t_facility_wait": 0.0,
        "t_facility_service": 0.0,
        "n_refuels": 0,
        "t_facility_down_wait": 0.0,
        "facility_failures": 0,
    }
    trips_log = []

    t = 0
    # If multiple requests arrive at the same time, serve higher priority first.
    arrivals = sorted(scheduled, key=lambda r: (r.time, -getattr(r, "priority", 0)))
    pending = []
    done = []
    rejected = []

    logs = []

    while True:
        while arrivals and arrivals[0].time <= t:
            r = arrivals.pop(0)
            r.status = "pending"
            r.next_try = t
            pending.append(r)
            if print_logs:
                logs.append(
                    f"[t={t:3d}] Llega {r.id}: {r.origin}->{r.destination} pref={r.vehicle_pref} "
                    f"pax={r.passengers} pr={getattr(r, 'priority', 0)}"
                )
        hubo_cambios = False
        # Process pending by priority (desc), then by request time.
        for r in sorted(pending, key=lambda x: (-getattr(x, "priority", 0), x.time, x.id)):
            if r.status != "pending" or r.next_try > t:
                continue
            if r.wait_max is not None and t > r.time + r.wait_max:
                r.status = "rejected"
                pending.remove(r); rejected.append(r)
                if print_logs: logs.append(f"[t={t:3d}] {r.id} RECHAZADA por espera máxima")
                continue

            cand = [v for v in world.vehicles if v.free_at <= t and (r.vehicle_pref == "any" or v.kind == r.vehicle_pref) and v.capacity >= r.passengers]
            if not cand:
                r.attempts += 1
                r.next_try = t + cooldown_ticks
                if print_logs: logs.append(f"[t={t:3d}] {r.id} sin candidatos; intento {r.attempts}/{max_retries}, reint t={r.next_try}")
                if r.attempts >= max_retries:
                    r.status = "rejected"
                    pending.remove(r); rejected.append(r)
                    if print_logs: logs.append(f"[t={t:3d}] {r.id} RECHAZADA tras {r.attempts} intentos")
                continue

            best = None
            for v in cand:
                if world.path_mode == "astar":
                    p1 = astar_time(world, v.pos, r.origin, stats=world.search_stats)
                    p2 = astar_time(world, r.origin, r.destination, stats=world.search_stats)
                else:
                    p1 = dijkstra_time(world, v.pos, r.origin, stats=world.search_stats)
                    p2 = dijkstra_time(world, r.origin, r.destination, stats=world.search_stats)
                if p1 is None or p2 is None:
                    continue
                # Estimar tiempo+km+energía para: (vehículo -> origen) y (origen -> destino)
                try:
                    t1, en1, km1 = sum_path(world, v, p1[0])
                    t2, en2, km2 = sum_path(world, v, p2[0])
                except Exception:
                    continue

                per_km = float(world.cost.get("weights", {}).get("per_km", 0.8))
                per_min = float(world.cost.get("weights", {}).get("per_min", 0.1))
                p_energy = float(world.cost.get("pricing", {}).get(
                    energy_unit(v),
                    0.25 if v.kind == "EV" else 1.7
                ))

                coste_est = (km1 + km2) * per_km + (t1 + t2) * per_min + (en1 + en2) * p_energy
                sc = _score(world, v, r, t1, t2, coste_est)

                if (best is None) or (sc < best[0]):
                    best = (sc, v)

            if best is None:
                r.attempts += 1
                r.next_try = t + cooldown_ticks
                if print_logs: logs.append(f"[t={t:3d}] {r.id} sin rutas; intento {r.attempts}/{max_retries}, reint t={r.next_try}")
                if r.attempts >= max_retries:
                    r.status = "rejected"
                    pending.remove(r); rejected.append(r)
                    if print_logs: logs.append(f"[t={t:3d}] {r.id} RECHAZADA tras {r.attempts} intentos")
                continue

            _, v = best
            if print_logs: logs.append(f"[t={t:3d}] {v.id} asignado a {r.id} ({r.origin}->{r.destination})")
            ok, tfin, m = assign_and_execute(              
                world, r, v,
                mode=world.path_mode, now=t,
                cost=world.cost, metrics_out=metrics, response_start=t,
                rng=rng, fail_p=fail_p, fail_min=fail_min, fail_max=fail_max
            )
            if ok:
                r.status = "done"
                pending.remove(r); done.append(r)
                hubo_cambios = True
                trips_log.append({
                    "req": r.id, "veh": v.id, "kind": v.kind, "pax": r.passengers,
                    "start_t": t, "end_t": tfin,
                    "km_vacio": round(m["km_vacio"],3), "km_pasajero": round(m["km_pasajero"],3),
                    "t_vacio": round(m["t_vacio"],3), "t_pasajero": round(m["t_pasajero"],3),
                    "energia": round(m["energia_total"],3), "co2_kg": round(m["co2_kg"],3), "coste": round(m["costeu"],3),
                    "t_facility_wait": round(m["t_facility_wait"], 3),
                    "t_facility_service": round(m["t_facility_service"], 3),
                    "n_refuels": int(m["n_refuels"]),
                    "t_facility_down_wait": round(m.get("t_facility_down_wait", 0.0), 3),
                    "facility_failures": int(m.get("facility_failures", 0)),
                })
                busy_time[v.id] += (
                    float(m.get("t_vacio", 0.0)) +
                    float(m.get("t_pasajero", 0.0)) +
                    float(m.get("t_facility_wait", 0.0)) +
                    float(m.get("t_facility_service", 0.0)) +
                    float(m.get("t_facility_down_wait", 0.0))
                )

                if print_logs: logs.append(f"[t={tfin:3d}] {r.id} COMPLETADA por {v.id}")
            else:
                r.attempts += 1
                r.next_try = t + cooldown_ticks
                if print_logs: logs.append(f"[t={t:3d}] {r.id} fallo ejecución; intento {r.attempts}/{max_retries}, reint t={r.next_try}")
                if r.attempts >= max_retries:
                    r.status = "rejected"
                    pending.remove(r); rejected.append(r)
                    if print_logs: logs.append(f"[t={t:3d}] {r.id} RECHAZADA tras {r.attempts} intentos")

        if not arrivals and not pending and all(v.free_at <= t for v in world.vehicles):
            break

        t_candidates = [t+1]
        if arrivals: t_candidates.append(arrivals[0].time)
        t_candidates.append(min([v.free_at for v in world.vehicles if v.free_at > t], default=t+1))
        nr = min([r.next_try for r in pending if r.status=='pending' and r.next_try>t], default=t+1)
        t_candidates.append(nr)
        t = min([x for x in t_candidates if x>t], default=t+1)

    resumen = {"done": len(done), "rejected": len(rejected), "t_end": t}
    if print_logs:
        print("== RESUMEN ==")
        print(json.dumps(resumen, indent=2))
        prom_resp = (sum(metrics["tiempos_respuesta"])/len(metrics["tiempos_respuesta"])) if metrics["tiempos_respuesta"] else 0.0
        print(f"Viajes={metrics['viajes']}  Km_vacio={metrics['km_vacio']:.2f}  Km_pasajero={metrics['km_pasajero']:.2f}  CO2(kg)={metrics['co2_kg']:.2f}  Coste={metrics['costeu']:.2f}  Tresp_prom={prom_resp:.2f}")

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as f:
            out = dict(metrics)
            out["t_end"] = t
            out["done"] = len(done)
            out["rejected"] = len(rejected)
            out["t_resp_prom"] = (sum(metrics["tiempos_respuesta"])/len(metrics["tiempos_respuesta"])) if metrics["tiempos_respuesta"] else 0.0

            out["busy_time_total"] = float(sum(busy_time.values()))
            nveh = len(world.vehicles)
            out["utilization"] = (out["busy_time_total"] / (nveh * t)) if (t > 0 and nveh > 0) else 0.0

            out["search_path_calls"] = int(world.search_stats.get("path_calls", 0))

            out["search_pops"] = int(world.search_stats.get("pops", 0))
            out["search_pushes"] = int(world.search_stats.get("pushes", 0))
            out["search_expansions"] = int(world.search_stats.get("expansions", 0))
            out["search_heuristic_calls"] = int(world.search_stats.get("heuristic_calls", 0))
            out["search_hop_lb_calls"] = int(world.search_stats.get("hop_lb_calls", 0))

            json.dump(out, f, indent=2, ensure_ascii=False)
        with open(os.path.join(out_dir, "trips.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "req","veh","kind","pax","start_t","end_t",
                "km_vacio","km_pasajero","t_vacio","t_pasajero",
                "t_facility_wait","t_facility_service","n_refuels",
                "t_facility_down_wait","facility_failures",
                "energia","co2_kg","coste"
            ])
            w.writeheader()
            w.writerows(trips_log)

    return resumen
