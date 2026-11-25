import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.taxigreen.classes import World, CostModel, Vehicle, Request
from src.taxigreen.sim.dispatcher import Dispatcher


class FixedDispatcher(Dispatcher):
    """Dispatcher que fuerza mismas rutas/costes para todos los vehículos,
    para que el desempate dependa solo de trips/idle.
    """
    def _rutas_para(self, v, origen: str, destino: str):
        # Estructura: (path, time)
        r1 = (["S", origen], 5.0)
        r2 = ([origen, destino], 5.0)
        return r1, r2

    def _energia_total_para(self, v, r1, r2):
        # (t_total, en_total, km_total, t_origen, t_dest)
        return (10.0, 1.0, 1.0, 5.0, 5.0)


def _mk_world_and_state():
    v1 = Vehicle(id="V1", kind="EV", capacity_pax=4, start_node="S",
                 energy_max=100.0, energy_now=100.0, consumption_per_km=1.0)
    v2 = Vehicle(id="V2", kind="EV", capacity_pax=4, start_node="S",
                 energy_max=100.0, energy_now=100.0, consumption_per_km=1.0)

    cm = CostModel(
        pricing={"kwh": 1.0, "liter": 1.0},
        weights={"per_km": 0.0, "per_min": 0.0},
    )
    # OJO: tu código lee esto con getattr(..., "dispatch_policy", ...)
    cm.dispatch_policy = "default"

    w = World(nodes={}, edges=[], facilities=[], vehicles=[v1, v2], cost_model=cm)

    st = SimpleNamespace(
        tiempo_sim=0,
        posicion_vehiculo={"V1": "S", "V2": "S"},
        vehiculo_libre_en={"V1": 0, "V2": 0},
        viajes_por_vehiculo={"V1": 0, "V2": 0},
        vehiculo_ultimo_fin={"V1": 0, "V2": 0},
    )
    return w, st


def test_dispatch_policy_balance_prefiere_menos_viajes():
    w, st = _mk_world_and_state()
    w.cost_model.dispatch_policy = "balance"

    # Forzamos desigualdad: V1 hizo más viajes que V2
    st.viajes_por_vehiculo["V1"] = 10
    st.viajes_por_vehiculo["V2"] = 1

    disp = FixedDispatcher(w, st, path_mode="ucs", policy="fast", reporter=None)
    req = Request(id="R", t_min=0, origin="A", destination="B", pax=1, vehicle_pref="any")

    v = disp.pick_best_vehicle(req)
    assert v is not None
    assert v.id == "V2"   # menos viajes


def test_dispatch_policy_least_idle_prefiere_menos_idle():
    w, st = _mk_world_and_state()
    w.cost_model.dispatch_policy = "least_idle"

    # t actual
    st.tiempo_sim = 100

    # idle(V1)=100-90=10 (menos idle)
    # idle(V2)=100-50=50 (más idle)
    st.vehiculo_ultimo_fin["V1"] = 90
    st.vehiculo_ultimo_fin["V2"] = 50

    disp = FixedDispatcher(w, st, path_mode="ucs", policy="fast", reporter=None)
    req = Request(id="R", t_min=0, origin="A", destination="B", pax=1, vehicle_pref="any")

    v = disp.pick_best_vehicle(req)
    assert v is not None
    assert v.id == "V1"   # menos idle
