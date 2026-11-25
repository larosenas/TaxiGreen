
from dataclasses import dataclass
from typing import Literal, Dict, Any
NodeKind = Literal["pickup", "hub", "poi"]
@dataclass(frozen=True)
class Node:
    id: str
    name: str
    kind: NodeKind
    @staticmethod
    def from_json(obj: Dict[str, Any]) -> "Node":
        for key in ("id", "name", "kind"):
            if key not in obj or not isinstance(obj[key], str):
                raise ValueError("Nodo mal definido")
        if obj["kind"] not in ("pickup","hub","poi"):
            raise ValueError("kind debe ser pickup|hub|poi")
        return Node(id=obj["id"], name=obj["name"], kind=obj["kind"])
