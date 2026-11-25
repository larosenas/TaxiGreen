
from dataclasses import dataclass
from typing import Literal, Dict, Any
VehKind = Literal["EV","ICE"]
@dataclass
class Vehicle:
    id: str
    kind: VehKind
    capacity_pax: int
    start_node: str
    energy_max: float
    energy_now: float
    consumption_per_km: float
    @staticmethod
    def from_json(obj: Dict[str, Any]) -> "Vehicle":
        return Vehicle(
            id=str(obj["id"]), kind=str(obj["kind"]), capacity_pax=int(obj["capacity_pax"]),
            start_node=str(obj["start_node"]), energy_max=float(obj["energy_max"]),
            energy_now=float(obj["energy_now"]), consumption_per_km=float(obj["consumption_per_km"])
        )
