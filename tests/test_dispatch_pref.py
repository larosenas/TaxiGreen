import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.taxigreen.world import build_world_from_folder
from src.taxigreen.sim.engine import iniciar_estado
from src.taxigreen.sim.dispatcher import Dispatcher
from src.taxigreen.io.loaders import load_requests

def test_vehicle_preference():
    data = Path("data/oviedo_city")
    w = build_world_from_folder(data)
    st = iniciar_estado(w)
    reqs = load_requests(data / "requests.json")
    r_ev = next(r for r in reqs if r.vehicle_pref in ("EV","any"))
    disp = Dispatcher(w, st, path_mode="ucs", policy="fast", reporter=None)
    v = disp.pick_best_vehicle(r_ev)
    assert v is not None
    if r_ev.vehicle_pref == "EV":
        assert v.kind == "EV"
