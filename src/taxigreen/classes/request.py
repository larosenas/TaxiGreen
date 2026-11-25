
from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal
VehPref = Literal["EV","ICE","any"]
@dataclass(frozen=True)
class Request:
    id: str
    t_min: int
    origin: str
    destination: str
    pax: int
    priority: int = 0
    vehicle_pref: VehPref = "any"
    deadline_min: Optional[int] = None
    @staticmethod
    def from_json(obj: Dict[str, Any]) -> "Request":
        pref = obj.get("vehicle_pref","any")
        return Request(
            id=str(obj["id"]), t_min=int(obj["t_min"]), origin=str(obj["origin"]),
            destination=str(obj["destination"]), pax=int(obj["pax"]),
            priority=int(obj.get("priority",0)), vehicle_pref=pref,
            deadline_min=(int(obj["deadline_min"]) if obj.get("deadline_min") is not None else None)
        )
