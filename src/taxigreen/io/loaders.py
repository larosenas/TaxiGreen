
import json
from pathlib import Path
from typing import List
from ..classes import Node, Edge, Facility, Vehicle, CostModel, Request

class DataFileError(Exception): pass
class ValidationError(Exception): pass

def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_nodes(path: Path):
    data = _load_json(path)
    nodes = {}
    for obj in data:
        n = Node.from_json(obj)
        if n.id in nodes: raise ValidationError(f"id duplicado de nodo: {n.id}")
        nodes[n.id] = n
    return nodes

def load_edges(path: Path) -> List[Edge]:
    data = _load_json(path)
    return [Edge.from_json(x) for x in data]

def load_facilities(path: Path) -> List[Facility]:
    data = _load_json(path)
    return [Facility.from_json(x) for x in data]

def load_vehicles(path: Path) -> List[Vehicle]:
    data = _load_json(path)
    return [Vehicle.from_json(x) for x in data]

def load_cost_model(path: Path) -> CostModel:
    data = _load_json(path); return CostModel.from_json(data)

def load_requests(path: Path) -> List[Request]:
    data = _load_json(path)
    return [Request.from_json(x) for x in data]
