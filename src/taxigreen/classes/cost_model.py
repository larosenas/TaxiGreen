
from dataclasses import dataclass, field
from typing import Dict, Any
@dataclass
class CostModel:
    time_step_min: int = 1
    pricing: Dict[str, float] = field(default_factory=dict)
    externalities: Dict[str, float] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    queues: Dict[str, float] = field(default_factory=dict)
    @staticmethod
    def from_json(obj: Dict[str, Any]) -> "CostModel":
        return CostModel(
            time_step_min=int(obj.get("time_step_min",1)),
            pricing=dict(obj.get("pricing",{})),
            externalities=dict(obj.get("externalities",{})),
            weights=dict(obj.get("weights",{})),
            queues=dict(obj.get("queues",{})),
        )
