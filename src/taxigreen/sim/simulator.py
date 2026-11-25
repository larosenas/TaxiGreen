from pathlib import Path
import time

from .clock import Clock
from .requests_repo import RepositorioPeticiones
from .dispatcher import Dispatcher
from .report import Reportero, write_stats_json
from ..io.loaders import load_requests
from ..world import build_world_from_folder
from .engine import iniciar_estado
from .validator import validate_dataset
from .pathfinding import shortest_path_by_time


def _todas_servicio_terminado(estado, vehicles) -> bool:
    t = getattr(estado, "tiempo_sim", 0)
    return all(estado.vehiculo_libre_en.get(v.id, 0) <= t for v in vehicles)


def _no_quedan_peticiones(repo) -> bool:
    if hasattr(repo, "all_done"):
        return bool(repo.all_done)
    if hasattr(repo, "has_pending"):
        return not repo.has_pending()
    if hasattr(repo, "pendientes"):
        return len(repo.pendientes) == 0
    if hasattr(repo, "pending"):
        return len(repo.pending) == 0
    # Si no se conoce la API del repo, devolvemos True solo si no hay atributos típicos
    return True


def _llegan_peticiones(repo: RepositorioPeticiones, t: int) -> None:
    llegadas = repo.release_arrivals(t)
    if llegadas:
        print(f"[t={t:>3}] Llegan: {[r.id for r in llegadas]}")


def _procesar_pendientes(
    repo: RepositorioPeticiones,
    desp: Dispatcher,
    estado,
    reloj: Clock,
    path_mode: str,
) -> bool:
    progreso = False

    for r in list(repo.pendientes):

        #ponemos una deadline para que no haya bucles infinitos
        #Si la deadline no tiene un valor dado, suponemos que son 30 minutos
        deadline = r.deadline_min if getattr(r, "deadline_min", None) is not None else 60

        if reloj.t > r.t_min + int(deadline):
            print(f"[t={reloj.t:>3}] Rechazada {r.id}: excede deadline ({deadline} min)")
            repo.mark_rejected(r)
            continue   

        # validar que hay camino dirigido origen->destino
        if shortest_path_by_time(
            desp.world,
            r.origin,
            r.destination,
            mode=path_mode,
        ) is None:
            print(
                f"[t={reloj.t:>3}] Rechazada {r.id}: "
                f"sin camino de {r.origin} a {r.destination}"
            )
            repo.mark_rejected(r)
            continue

        v = desp.pick_best_vehicle(r)
        if v is None:
            print(
                f"[t={reloj.t:>3}] Ningún vehículo disponible para petición "
                f"{r.id} ({r.origin}->{r.destination})"
            )
            continue

        asg = desp.assign_and_run(r, v)
        if asg.ok:
            print(
                f"[t~{estado.tiempo_sim:>3}] Asignada {r.id} -> {v.id}, "
                f"fin t={asg.fin}"
            )
            repo.mark_served(r)
            progreso = True
        else:
            print(
                f"[t={reloj.t:>3}] No se pudo completar la asignación de "
                f"{r.id} con {v.id}"
            )

    return progreso


def run_simulation(
    data_dir: Path,
    out_dir: Path,
    path_mode: str = "ucs",
    wall_seconds: float = 15.0,
    speed_min_per_tick: int = 5,
    sleep_per_tick: float = 0.02,
    policy: str = "fast",
    vehicles_filename: str = "vehicles.json",
) -> None:
    # Validación y carga
    validate_dataset(data_dir, out_dir, path_mode)
    mundo = build_world_from_folder(data_dir, vehicles_filename=vehicles_filename)
    estado = iniciar_estado(mundo)
    repo = RepositorioPeticiones()
    reportero = Reportero()
    lista = load_requests(data_dir / "requests.json")
    repo.load_all(lista)
    reloj = Clock(t=0)
    desp = Dispatcher(mundo, estado, path_mode=path_mode, policy=policy, reporter=reportero)

    print(f"== Simulación ({path_mode}/{policy}) hasta completar ==")

    # Bucle principal
    while not repo.all_done:
        estado.tiempo_sim = reloj.t
        _llegan_peticiones(repo, reloj.t)
        repo.sort_pending_by_priority()

        progreso_tick = _procesar_pendientes(repo, desp, estado, reloj, path_mode)

        # Fin anticipado: si no queda trabajo y todos están libres, terminamos
        if _no_quedan_peticiones(repo) and _todas_servicio_terminado(estado, mundo.vehicles):
            if reportero:
                reportero.finish(estado)
            break

        if not progreso_tick:
            # repostaje preventivo ligero: si está libre y con energía <25%
            for v in mundo.vehicles:
                if estado.vehiculo_libre_en[v.id] <= estado.tiempo_sim and v.energy_now < v.energy_max * 0.25:
                    desp.repostar_si_conviene(v)

        time.sleep(max(0.0, sleep_per_tick))
        reloj.step(max(1, speed_min_per_tick))

    # Informes
    reportero.write_json(out_dir, "trips_report.json")
    reportero.write_csv(out_dir, "trips_report.csv")
    kinds = {v.id: v.kind for v in mundo.vehicles}
    write_stats_json(
        out_dir,
        reportero.viajes,
        reloj.t,
        estado.repostajes_por_vehiculo,
        estado.tiempo_instalacion_por_vehiculo,
        estado.espera_install_por_vehiculo,
        kinds,
    )
    print(f"== Fin: t={reloj.t} | Servidas={len(repo.servidas)} Rechazadas={len(repo.rechazadas)} ==")
    print(f"Estadísticas en: {out_dir}/stats_report.json")
