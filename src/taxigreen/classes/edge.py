
from dataclasses import dataclass
from typing import Dict, Any
@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    distance_km: float
    travel_min: float
    @staticmethod
    def from_json(obj: Dict[str, Any]) -> "Edge":
        for k in ("from","to","distance_km","travel_min"):
            if k not in obj: raise ValueError("Arista mal definida")
        return Edge(src=str(obj["from"]), dst=str(obj["to"]),
                    distance_km=float(obj["distance_km"]), travel_min=float(obj["travel_min"]))
