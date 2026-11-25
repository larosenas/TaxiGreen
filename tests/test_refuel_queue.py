import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.taxigreen.world import build_world_from_folder
from src.taxigreen.sim.engine import iniciar_estado
from src.taxigreen.sim.dispatcher import Dispatcher
from src.taxigreen.io.loaders import load_requests

def test_refuel_when_low():
    data = Path("data/oviedo_refuel_easy")
    w = build_world_from_folder(data)
    st = iniciar_estado(w)
    disp = Dispatcher(w, st, path_mode="ucs", policy="fast", reporter=None)
    # baja a repostar si energía < 25%
    low = next(v for v in w.vehicles if v.energy_now < v.energy_max*0.25)
    ok = disp.repostar_si_conviene(low)
    assert ok is True
    assert low.energy_now == low.energy_max
