
from dataclasses import dataclass, field
from typing import Dict, List
from .node import Node
from .edge import Edge
from .facility import Facility
from .vehicle import Vehicle
from .cost_model import CostModel
@dataclass
class World:
    nodes: Dict[str, Node]
    edges: List[Edge]
    facilities: List[Facility]
    vehicles: List[Vehicle]
    cost_model: CostModel
    neighbors: Dict[str, List[Edge]] = field(default_factory=dict)
    def build_neighbors_directed(self) -> None:
        self.neighbors = {nid: [] for nid in self.nodes.keys()}
        for e in self.edges:
            self.neighbors[e.src].append(e)
