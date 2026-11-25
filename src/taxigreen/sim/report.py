
from dataclasses import dataclass, asdict, field
from typing import List, Dict
from pathlib import Path
import json

@dataclass
class RegistroViaje:
    request_id: str
    vehicle_id: str
    t_start: int
    t_finish: int
    origin: str
    destination: str
    route_to_pickup: List[str]
    route_trip: List[str]
    dist_to_pickup_km: float
    dist_trip_km: float
    time_to_pickup_min: float
    time_trip_min: float
    energy_used: float
    price: float

@dataclass
class Reportero:
    viajes: List[RegistroViaje] = field(default_factory=list)
    def log(self, r: RegistroViaje): self.viajes.append(r)

    def finish(self, estado=None):
        """Hook de compatibilidad.

        El simulador puede llamar a finish() al terminar; actualmente no necesitamos
        hacer nada especial aquí, pero mantenemos el método para evitar errores.
        """
        return

    def write_json(self, out_dir: Path, name: str = "trips_report.json"):
        out_dir.mkdir(parents=True, exist_ok=True)
        data = [asdict(x) for x in self.viajes]
        (out_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    def write_csv(self, out_dir: Path, name: str = "trips_report.csv"):
        out_dir.mkdir(parents=True, exist_ok=True)
        if not self.viajes:
            (out_dir / name).write_text("", encoding="utf-8"); return
        import csv
        keys = list(asdict(self.viajes[0]).keys())
        with (out_dir / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
            for v in self.viajes: w.writerow(asdict(v))

    def add_trip(self, req, v, r1, r2, fin):
        """Registra un viaje (para luego sacar CSV/JSON/gráficas)."""
        if not hasattr(self, "trips"):
            self.trips = []

        self.trips.append({
            "req_id": req.id,
            "t_min": req.t_min,
            "origin": req.origin,
            "destination": req.destination,
            "pax": getattr(req, "pax", None),
            "priority": getattr(req, "priority", None),
            "vehicle_id": v.id,
            "vehicle_kind": getattr(v, "kind", None),
            "finish_t": fin,
            "pickup_nodes": list(r1),
            "trip_nodes": list(r2),
            "pickup_len": len(r1),
            "trip_len": len(r2),
        })

    

def _sum(xs): 
    return sum(xs) if xs else 0.0

def _avg(xs):
    return (_sum(xs) / len(xs)) if xs else 0.0

def write_stats_json(out_dir: Path, viajes: list, sim_end_time: int, repostajes_por_vehiculo: dict = None, tiempo_instalacion_por_vehiculo: dict = None, espera_instalacion_por_vehiculo: dict = None, vehicle_kinds: Dict[str,str] = None):
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(viajes)
    tiempos_recogida = [v.time_to_pickup_min for v in viajes]
    tiempos_tramo = [v.time_trip_min for v in viajes]
    dist_recogida = [v.dist_to_pickup_km for v in viajes]
    dist_tramo = [v.dist_trip_km for v in viajes]
    energia = [v.energy_used for v in viajes]
    ingresos = [v.price for v in viajes]

    por_vehiculo = {}
    for v in viajes:
        vv = por_vehiculo.setdefault(v.vehicle_id, {"viajes":0,"min_ocupado":0.0,"km":0.0,"energia":0.0,"ingresos":0.0})
        vv["viajes"] += 1
        vv["min_ocupado"] += (v.time_to_pickup_min + v.time_trip_min)
        vv["km"] += (v.dist_to_pickup_km + v.dist_trip_km)
        vv["energia"] += v.energy_used
        vv["ingresos"] += v.price

    utilizacion = {vid: round(d["min_ocupado"] / max(1.0, sim_end_time), 4) for vid, d in por_vehiculo.items()}

    # EV/ICE breakdown
    kinds = vehicle_kinds or {}
    by_kind = {"EV":{"viajes":0,"km":0.0,"energia":0.0,"ingresos":0.0},
               "ICE":{"viajes":0,"km":0.0,"energia":0.0,"ingresos":0.0}}
    for v in viajes:
        k = kinds.get(v.vehicle_id, "ICE")
        km = v.dist_to_pickup_km + v.dist_trip_km
        by_kind[k]["viajes"] += 1
        by_kind[k]["km"] += km
        by_kind[k]["energia"] += v.energy_used
        by_kind[k]["ingresos"] += v.price

    stats = {
        "total_viajes": total,
        "media_espera_recogida_min": round(_avg(tiempos_recogida), 3),
        "media_tiempo_viaje_min": round(_avg(tiempos_tramo), 3),
        "km_totales": round(_sum(dist_recogida) + _sum(dist_tramo), 3),
        "energia_total": round(_sum(energia), 3),
        "ingresos_totales": round(_sum(ingresos), 2),
        "vehiculos": por_vehiculo,
        "utilizacion_min_por_tick": utilizacion,
        "tiempo_sim_final_min": sim_end_time,
        "repostajes_por_vehiculo": repostajes_por_vehiculo or {},
        "tiempo_instalacion_por_vehiculo_min": tiempo_instalacion_por_vehiculo or {},
        "espera_instalacion_por_vehiculo_min": espera_instalacion_por_vehiculo or {},
        "ev_ice_breakdown": by_kind
    }
    (out_dir / "stats_report.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
