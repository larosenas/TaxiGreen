
from dataclasses import dataclass, field, asdict
from typing import List
from pathlib import Path
import json
from ..classes import Request

@dataclass
class RepositorioPeticiones:
    todas: List[Request] = field(default_factory=list)
    pendientes: List[Request] = field(default_factory=list)
    servidas: List[Request] = field(default_factory=list)
    rechazadas: List[Request] = field(default_factory=list)
    def load_all(self, reqs: List[Request]) -> None:
        self.todas = sorted(reqs, key=lambda r: r.t_min)
    def release_arrivals(self, ahora: int):
        llegadas = []
        while self.todas and self.todas[0].t_min <= ahora:
            r = self.todas.pop(0)
            self.pendientes.append(r)
            llegadas.append(r)
        return llegadas
    def sort_pending_by_priority(self): self.pendientes.sort(key=lambda r: (-r.priority, r.t_min))
    def mark_served(self, r: Request): self.servidas.append(r); self.pendientes = [x for x in self.pendientes if x.id != r.id]
    def mark_rejected(self, r: Request): self.rechazadas.append(r); self.pendientes = [x for x in self.pendientes if x.id != r.id]
    @property
    def all_done(self) -> bool: return not self.todas and not self.pendientes
    def save_snapshot(self, out_dir: Path, t: int) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        snap = {"t": t, "pendientes":[asdict(x) for x in self.pendientes], "servidas":[asdict(x) for x in self.servidas], "rechazadas":[asdict(x) for x in self.rechazadas]}
        (out_dir / f"snapshot_t{t}.json").write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
