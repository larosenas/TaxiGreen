
from dataclasses import dataclass
from typing import Literal, Dict, Any
FacilityType = Literal["gas","charger"]
@dataclass(frozen=True)
class Facility:
    id: str
    node_id: str
    type: FacilityType
    capacity: int
    service_min: float
    price_per_unit: float
    @staticmethod
    def from_json(obj: Dict[str, Any]) -> "Facility":
        return Facility(
            id=str(obj["id"]), node_id=str(obj["node_id"]),
            type=str(obj["type"]), capacity=int(obj["capacity"]),
            service_min=float(obj["service_min"]), price_per_unit=float(obj["price_per_unit"])
        )
