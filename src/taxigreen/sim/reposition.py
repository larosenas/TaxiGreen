from typing import Optional, List, Tuple

from ..classes import World, Vehicle
from .pathfinding import shortest_path_by_time
from .energy import sum_path


def nearest_hub_route(world: World, start: str, v: Vehicle, mode: str = "ucs") -> Optional[Tuple[List[str], float]]:
    """Devuelve (camino, tiempo_min) al hub más cercano distinto de la posición actual.

    Esta función queda disponible por si se quiere usar manualmente, pero la simulación principal
    ya no llama a reposicionamientos automáticos.
    """
    hubs = [nid for nid, n in world.nodes.items() if getattr(n, "kind", None) == "hub"]
    mejor: Optional[Tuple[List[str], float]] = None

    for h in hubs:
        res = shortest_path_by_time(world, start, h, mode=mode)
        if res is None:
            continue
        path, t = res

        #por si acaso devuelve una lista vacía
        if not path:
            continue

        # Si ya estamos en el hub, no tiene sentido reposicionar
        if len(path) <= 1 and path[0] == start:
            continue

        if mejor is None or t < mejor[1]:
            mejor = (path, t)

    return mejor


def reposition_to_hub_if_stuck(world: World, estado, v: Vehicle, mode: str = "ucs") -> bool:
    """Reposiciona al hub más cercano si se llama explícitamente.

    NOTA: La simulación `run_simulation` ya NO llama a esta función; los vehículos
    no se recolocan automáticamente, solo se mueven debido a pedidos o repostajes.
    """
    pos = estado.posicion_vehiculo[v.id]
    res = nearest_hub_route(world, pos, v, mode)
    if res is None:
        return False

    path, t = res

    # Si el camino no mueve realmente al vehículo, no reposicionamos
    if len(path) <= 1 or path[-1] == pos:
        return False

    # Chequear energía para ese camino
    tmin, en, km = sum_path(world, v, path)
    if tmin <= 0 or v.energy_now < en:
        return False

    from .engine import aplicar_tramo
    print(f"[t={estado.tiempo_sim:>3}] {v.id} se reposiciona a hub: {pos} -> {path[-1]} ({int(round(tmin))}m)")
    aplicar_tramo(world, estado, v, path, nota="reposicion_hub")
    return True
