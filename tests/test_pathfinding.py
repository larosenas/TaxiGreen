import sys, json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.taxigreen.world import build_world_from_folder
from src.taxigreen.sim.pathfinding import shortest_path_by_time

def test_directed_paths():
    data = Path("data/oviedo_city")
    w = build_world_from_folder(data)
    # Existe URIA -> CATEDRAL (directo)
    p1 = shortest_path_by_time(w, "URIA", "CATEDRAL")
    assert p1 is not None and p1[0][0] == "URIA" and p1[0][-1] == "CATEDRAL"
    # No existe CATEDRAL -> URIA directo (en dataset de ejemplo), pero puede via otro nodo o no existir
    p2 = shortest_path_by_time(w, "CATEDRAL", "URIA")
    # Permitimos None si realmente no hay ruta
    assert p2 is None or (p2[0][0] == "CATEDRAL" and p2[0][-1] == "URIA")
