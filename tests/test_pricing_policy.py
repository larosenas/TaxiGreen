import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.taxigreen.world import build_world_from_folder
from src.taxigreen.sim.engine import iniciar_estado
from src.taxigreen.sim.dispatcher import Dispatcher
from src.taxigreen.io.loaders import load_requests

def test_cheap_not_crash():
    data = Path("data/oviedo_city")
    w = build_world_from_folder(data)
    st = iniciar_estado(w)
    disp = Dispatcher(w, st, path_mode="ucs", policy="cheap", reporter=None)
    # Coge una request y verifica que no crashea el scoring
    r = next(iter(load_requests(data / "requests.json")))
    v = disp.pick_best_vehicle(r)
    # Puede no haber vehículo apto en el primer tick; lo importante es que la política no rompa
    assert v is None or v.id
