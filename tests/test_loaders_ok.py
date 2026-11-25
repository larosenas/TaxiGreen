from pathlib import Path
from src.taxigreen.world import build_world_from_folder
from src.taxigreen.io.loaders import load_requests

def test_world_loads_with_real_data():
    data_dir = Path("data")
    w = build_world_from_folder(data_dir)

    # Existencia básica
    assert len(w.nodes) >= 5
    assert len(w.edges) > 0
    assert len(w.vehicles) > 0
    assert len(w.facilities) >= 1

    # Peticiones se cargan desde el JSON principal
    reqs = list(load_requests(data_dir / "requests.json"))
    assert len(reqs) >= 1

    # Vecindad construida
    for nid, node in w.nodes.items():
        assert nid in w.neighbors
        break

def test_neighbors_have_valid_refs():
    data_dir = Path("data")
    w = build_world_from_folder(data_dir)
    for src, edges in w.neighbors.items():
        assert src in w.nodes
        for e in edges:
            assert e.dst in w.nodes
            assert e.distance_km > 0
            assert e.travel_min > 0
