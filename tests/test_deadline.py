from pathlib import Path
from types import SimpleNamespace
import io
from contextlib import redirect_stdout, redirect_stderr

from src.taxigreen.world import build_world_from_folder
from src.taxigreen.classes.request import Request
from src.taxigreen.sim.requests_repo import RepositorioPeticiones
from src.taxigreen.sim.clock import Clock
from src.taxigreen.sim.simulator import _procesar_pendientes


WORLD = build_world_from_folder(Path("data"))  # se carga una vez


class DummyDispatcher:
    def __init__(self, world):
        self.world = world

    def pick_best_vehicle(self, r):
        # Simulamos "no hay vehículos disponibles"
        return None

    def assign_and_run(self, r, v):
        raise AssertionError("No debería llamarse assign_and_run en estos tests")


def _run_once(repo: RepositorioPeticiones, t: int, path_mode: str = "ucs"):
    reloj = Clock(t=t)
    estado = SimpleNamespace(tiempo_sim=reloj.t, vehiculo_libre_en={})
    desp = DummyDispatcher(WORLD)

    # Silenciar prints del motor durante tests
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        progreso = _procesar_pendientes(repo, desp, estado, reloj, path_mode=path_mode)

    return progreso


def test_deadline_expirada_rechaza_aunque_no_haya_vehiculos():
    repo = RepositorioPeticiones()
    # t_min=0, deadline=1, t=2 => 2 > 0+1 => se rechaza
    repo.pendientes.append(Request(id="R_dead", t_min=0, origin="A", destination="B", pax=1, deadline_min=1))

    progreso = _run_once(repo, t=2)

    assert progreso is False
    assert [x.id for x in repo.rechazadas] == ["R_dead"]
    assert repo.pendientes == []


def test_deadline_en_el_limite_no_rechaza_con_mayor_estricto():
    repo = RepositorioPeticiones()
    # t_min=0, deadline=2, t=2 => 2 > 0+2 es False => NO rechaza
    repo.pendientes.append(Request(id="R_lim", t_min=0, origin="A", destination="B", pax=1, deadline_min=2))

    progreso = _run_once(repo, t=2)

    assert progreso is False
    assert repo.rechazadas == []
    assert [x.id for x in repo.pendientes] == ["R_lim"]


def test_deadline_por_defecto_30_min_si_no_se_define():
    repo = RepositorioPeticiones()
    # deadline_min=None => tu código usa default 60
    repo.pendientes.append(Request(id="R_def", t_min=0, origin="A", destination="B", pax=1, deadline_min=None))

    _run_once(repo, t=60) 
    assert [x.id for x in repo.pendientes] == ["R_def"]
    assert repo.rechazadas == []

    _run_once(repo, t=61) 
    assert repo.pendientes == []
    assert [x.id for x in repo.rechazadas] == ["R_def"]
