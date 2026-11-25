
from pathlib import Path
from typing import Dict, Any, List
import json
from ..world import build_world_from_folder
from ..io.loaders import load_requests
from .pathfinding import shortest_path_by_time

def validate_dataset(data_dir: Path, out_dir: Path, path_mode: str = "ucs") -> Dict[str, Any]:
    world = build_world_from_folder(data_dir)
    reqs = load_requests(data_dir / "requests.json")
    problems: List[str] = []
    node_ids = set(world.nodes.keys())
    for e in world.edges:
        if e.src not in node_ids or e.dst not in node_ids:
            problems.append(f"Arista inválida {e.src}->{e.dst} (nodo inexistente)")
        if e.travel_min <= 0 or e.distance_km < 0:
            problems.append(f"Arista con valores no positivos {e.src}->{e.dst} (min={e.travel_min}, km={e.distance_km})")
    requests_report = []
    for r in reqs:
        path = shortest_path_by_time(world, r.origin, r.destination, mode=path_mode)
        requests_report.append({"id": r.id, "origin": r.origin, "destination": r.destination, "has_path": path is not None})
        if path is None:
            problems.append(f"Pedido {r.id}: no hay camino dirigido de {r.origin} a {r.destination}")
    summary = {
        "nodes_count": len(world.nodes),
        "edges_count": len(world.edges),
        "vehicles_count": len(world.vehicles),
        "facilities_count": len(world.facilities),
        "requests_count": len(reqs),
        "requests_path_ok": sum(1 for x in requests_report if x["has_path"]),
        "requests_path_fail": sum(1 for x in requests_report if not x["has_path"]),
    }
    report = {"summary": summary, "requests": requests_report, "problems": problems}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
