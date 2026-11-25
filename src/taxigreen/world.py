
from pathlib import Path
from typing import Dict, List, Set
from .classes import World, Node, Edge, Facility, Vehicle
from .io.loaders import load_nodes, load_edges, load_facilities, load_vehicles, load_cost_model

class ValidationError(Exception): pass

def _validate(nodes: Dict[str, Node], edges: List[Edge], facilities: List[Facility], vehicles: List[Vehicle]) -> None:
    ids_nodos: Set[str] = set(nodes.keys())
    for e in edges:
        if e.src not in ids_nodos or e.dst not in ids_nodos:
            raise ValidationError(f"edge mal: {e.src}->{e.dst}")
    for f in facilities:
        if f.node_id not in ids_nodos:
            raise ValidationError(f"facility en nodo inexistente: {f.node_id}")
    for v in vehicles:
        if v.start_node not in ids_nodos:
            raise ValidationError(f"vehiculo {v.id} en nodo inexistente: {v.start_node}")

def build_world_from_folder(data_dir: Path, vehicles_filename: str = "vehicles.json") -> World:
    nodos = load_nodes(data_dir / "nodes.json")
    edges = load_edges(data_dir / "edges.json")
    facilities = load_facilities(data_dir / "facilities.json")
    vehicles = load_vehicles(data_dir / vehicles_filename)
    cost = load_cost_model(data_dir / "cost_model.json")
    _validate(nodos, edges, facilities, vehicles)
    w = World(nodes=nodos, edges=edges, facilities=facilities, vehicles=vehicles, cost_model=cost)
    w.build_neighbors_directed()
    return w
