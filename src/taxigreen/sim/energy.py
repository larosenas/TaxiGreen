from typing import Tuple, List

from ..classes import World, Vehicle, Facility
from .pathfinding import shortest_path_by_time


def edge_lookup(world: World, a: str, b: str):
    """Devuelve la arista a->b si existe en neighbors, o None en caso contrario."""
    return next((e for e in world.neighbors.get(a, []) if e.dst == b), None)


def sum_path(world: World, v: Vehicle, path_nodes: List[str]) -> Tuple[float, float, float]:
    """Suma tiempo (min), energía y kilómetros de un camino de nodos para el vehículo v."""
    t = 0.0
    en = 0.0
    km = 0.0
    for i in range(len(path_nodes) - 1):
        e = edge_lookup(world, path_nodes[i], path_nodes[i + 1])
        if e is None:
            raise ValueError("arista inexistente en ruta")
        t += float(e.travel_min)
        km += float(e.distance_km)
        en += float(e.distance_km) * v.consumption_per_km
    return t, en, km


def nearest_facility_path(world: World, start_node: str, v: Vehicle, mode: str):
    """Devuelve (path, t, en, km, facility) a la instalación más cercana adecuada al tipo de vehículo."""
    tipo = "charger" if v.kind == "EV" else "gas"
    mejor = None
    for f in world.facilities:
        if f.type != tipo:
            continue
        res = shortest_path_by_time(world, start_node, f.node_id, mode=mode)
        if res is None:
            continue
        path, _ = res
        t, en, km = sum_path(world, v, path)
        if mejor is None or t < mejor[1]:
            mejor = (path, t, en, km, f)
    return mejor


# === ensure_energy_for y normalización defensiva ===

def _normalize_nodes(nodes):
    if not nodes:
        return []
    out = [nodes[0]]
    for n in nodes[1:]:
        if n != out[-1]:
            out.append(n)
    return out


def _energia_para(world, veh, ruta_nodes):
    ruta_nodes = _normalize_nodes(ruta_nodes)
    t, en, km = sum_path(world, veh, ruta_nodes)
    return en


def _nearest_reachable_facility(world, estado, veh, path_mode: str = "ucs"):
    origen = estado.posicion_vehiculo[veh.id]
    tipo_necesario = "charger" if getattr(veh, "kind", "ICE") == "EV" else "gas"
    mejor = None
    for fac in world.facilities:
        if fac.type != tipo_necesario:
            continue
        ruta = shortest_path_by_time(world, origen, fac.node_id, mode=path_mode)
        if ruta is None:
            continue
        nodes, minutos = ruta
        en_nec = _energia_para(world, veh, nodes)
        if en_nec <= veh.energy_now:
            if (mejor is None) or (minutos < mejor[1]):
                mejor = (nodes, minutos, fac)
    return mejor


def ensure_energy_for(world, estado, veh, full_route_nodes, path_mode: str = "ucs"):
    """Garantiza que el vehículo tiene energía para seguir la ruta completa.

    Si no tiene energía suficiente, intenta ir a una instalación alcanzable (gasolinera / cargador),
    repostar / recargar, y luego vuelve a validar la ruta.

    Esta versión añade logs de depuración para entender por qué puede fallar.
    """
    # Import diferido para evitar import circular con engine.py
    from .engine import aplicar_tramo

    print(
        f"[DEBUG] ensure_energy_for: veh={veh.id}, energy_now={veh.energy_now:.2f}, "
        f"nodos_ruta={len(full_route_nodes)}"
    )

    ruta_ok = _validate_and_fix_route(world, list(full_route_nodes), mode=path_mode)
    if ruta_ok is None:
        print(f"[DEBUG] ensure_energy_for: ruta inválida para veh={veh.id}")
        return False

    en_total = _energia_para(world, veh, ruta_ok)
    print(f"[DEBUG] ensure_energy_for: energía necesaria en_total={en_total:.2f}")
    if en_total <= veh.energy_now:
        print(f"[DEBUG] ensure_energy_for: energía suficiente sin repostar para veh={veh.id}")
        return True

    # Buscar instalación alcanzable
    mejor = _nearest_reachable_facility(world, estado, veh, path_mode=path_mode)
    if mejor is None:
        print(f"[DEBUG] ensure_energy_for: ninguna instalación alcanzable para veh={veh.id}")
        return False

    nodes, minutos, fac = mejor
    print(
        f"[DEBUG] ensure_energy_for: enviando veh={veh.id} a instalación {fac.id} en nodo "
        f"{fac.node_id}, minutos={minutos:.1f}, nodos_tramo={len(nodes)}"
    )
    aplicar_tramo(world, estado, veh, nodes, nota=f"repostaje/recarga en {fac.node_id}")

    # === Cola / capacidad de la instalación ===
    t_arr = max(estado.vehiculo_libre_en.get(veh.id, 0), estado.tiempo_sim)
    servers = estado.facility_servers.setdefault(fac.id, [])
    # liberar servidores que ya terminaron antes de la llegada
    servers[:] = [t_end for t_end in servers if t_end > t_arr]

    if getattr(fac, "capacity", 1) <= 0:
        cap = 1
    else:
        cap = int(getattr(fac, "capacity", 1))

    if len(servers) < cap:
        t_start = t_arr
    else:
        t_start = min(servers)
        # al empezar en el mínimo fin, liberamos todos los que terminan en ese instante
        servers[:] = [t_end for t_end in servers if t_end > t_start]

    wait = max(0.0, float(t_start) - float(t_arr))
    t_end = float(t_start) + float(getattr(fac, "service_min", 0.0))
    servers.append(t_end)

    # actualizar métricas/estado
    estado.vehiculo_libre_en[veh.id] = t_end
    if hasattr(estado, "tiempo_instalacion_por_vehiculo"):
        estado.tiempo_instalacion_por_vehiculo[veh.id] = estado.tiempo_instalacion_por_vehiculo.get(veh.id, 0.0) + float(getattr(fac, "service_min", 0.0))
    if hasattr(estado, "espera_install_por_vehiculo"):
        estado.espera_install_por_vehiculo[veh.id] = estado.espera_install_por_vehiculo.get(veh.id, 0.0) + wait
    veh.energy_now = veh.energy_max
    print(f"[DEBUG] ensure_energy_for: veh={veh.id} recargado a energy_now={veh.energy_now:.2f}")

    ruta_ok = _validate_and_fix_route(world, list(full_route_nodes), mode=path_mode)
    if ruta_ok is None:
        print(f"[DEBUG] ensure_energy_for: ruta inválida incluso tras repostar para veh={veh.id}")
        return False

    en_total = _energia_para(world, veh, ruta_ok)
    print(
        f"[DEBUG] ensure_energy_for: energía necesaria tras repostar en_total={en_total:.2f}, "
        f"energy_now={veh.energy_now:.2f}"
    )
    ok = en_total <= veh.energy_now
    if not ok:
        print(
            f"[DEBUG] ensure_energy_for: todavía insuficiente energía para veh={veh.id} "
            f"después de repostar"
        )
    return ok
def _edge_exists(world, a: str, b: str) -> bool:
    for e in world.edges:
        if e.src == a and e.dst == b:
            return True
    return False


def _repair_gap(world, a: str, b: str, mode: str):
    if a == b:
        return [a]
    r = shortest_path_by_time(world, a, b, mode=mode)
    if r is None:
        return None
    return r[0]


def _validate_and_fix_route(world, nodes: List[str], mode: str = "ucs"):
    if not nodes:
        return []
    fixed = [nodes[0]]
    for nxt in nodes[1:]:
        cur = fixed[-1]
        if _edge_exists(world, cur, nxt):
            fixed.append(nxt)
            continue
        sub = _repair_gap(world, cur, nxt, mode)
        if sub is None or len(sub) < 2:
            return None
        # sub incluye cur como primero; añadimos el resto
        fixed.extend(sub[1:])
    return fixed