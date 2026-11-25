from typing import List, Tuple, Optional
from .pathfinding import shortest_path_by_time
from .energy import sum_path, ensure_energy_for, nearest_facility_path
from .engine import aplicar_tramo


def _join_paths(a: List[str], b: List[str]) -> List[str]:
    if not a:
        return b[:] if b else []
    if not b:
        return a[:]
    return a + b[1:] if a[-1] == b[0] else a + b


class Dispatcher:
    def __init__(self, world, estado, path_mode: str = "ucs", policy: str = "fast", reporter=None):
        self.world = world
        self.estado = estado
        self.path_mode = path_mode
        self.policy = policy
        self.reporter = reporter

    def _score(self, v, t_origen: float, t_destino: float, km: float, en: float, precio_estimado: float):
        t_total = t_origen + t_destino
        if self.policy == "fast":
            return (t_total,)
        if self.policy == "nearest_origin":
            return (t_origen, t_total)
        if self.policy == "least_idle":
            idle = max(0, self.estado.tiempo_sim - self.estado.vehiculo_ultimo_fin.get(v.id, 0))
            return (idle, t_total)
        if self.policy == "balance":
            used = self.estado.viajes_por_vehiculo.get(v.id, 0)
            return (used, t_total)
        # cheap u otras: ponderamos por precio estimado
        return (precio_estimado, t_total)

    def _rutas_para(self, v, origen: str, destino: str):
        pos = self.estado.posicion_vehiculo[v.id]
        r1 = shortest_path_by_time(self.world, pos, origen, mode=self.path_mode)
        if r1 is None:
            return None
        r2 = shortest_path_by_time(self.world, origen, destino, mode=self.path_mode)
        if r2 is None:
            return None
        return r1, r2

    def _energia_total_para(self, v, r1, r2):
        t1, en1, km1 = sum_path(self.world, v, r1[0])
        t2, en2, km2 = sum_path(self.world, v, r2[0])
        return (t1 + t2, en1 + en2, km1 + km2, t1, t2)

    def pick_best_vehicle(self, req) -> Optional[object]:
        candidatos: List[Tuple[tuple, object, tuple]] = []
        for v in self.world.vehicles:
            if req.vehicle_pref != "any" and v.kind != req.vehicle_pref:
                continue

            # Respect passenger capacity.
            req_pax = getattr(req, "pax", getattr(req, "passengers", 1))
            v_cap = getattr(v, "capacity_pax", getattr(v, "capacity", 4))
            if int(req_pax) > int(v_cap):
                continue
            
            if self.estado.vehiculo_libre_en[v.id] > self.estado.tiempo_sim:
                continue
            rutas = self._rutas_para(v, req.origin, req.destination)
            if rutas is None:
                continue
            (r1, _), (r2, _) = (rutas[0], rutas[1])
            t_total, en_total, km_total, t_origen, t_dest = self._energia_total_para(v, rutas[0], rutas[1])

            pricing = self.world.cost_model.pricing or {}
            weights = self.world.cost_model.weights or {}
            p_en = pricing.get("kwh" if v.kind == "EV" else "liter", 0.0)
            precio_estimado = (
                en_total * p_en
                + km_total * weights.get("per_km", 0.0)
                + t_total * weights.get("per_min", 0.0)
            )

            score = self._score(v, t_origen, t_dest, km_total, en_total, precio_estimado)
            policy = getattr(self.world.cost_model, "dispatch_policy", "default")

            if policy == "balance":
                trips = self.estado.viajes_por_vehiculo.get(v.id, 0)
                score = (score, trips)  # menos viajes = mejor

            elif policy == "least_idle":
                last = self.estado.vehiculo_ultimo_fin.get(v.id, 0)
                idle = self.estado.tiempo_sim - last
                score = (score, idle)   # menos idle = mejor

            else:
                score = (score,)
            candidatos.append((score, v, (rutas, (t_total, en_total, km_total))))

        if not candidatos:
            return None
        candidatos.sort(key=lambda x: x[0])
        return candidatos[0][1]

    def assign_and_run(self, req, v):
        """Asigna la petición `req` al vehículo `v` y ejecuta los tramos si es posible.

        Añade logs descriptivos para ver claramente:
          - Cuándo se elige/agencia un vehículo para una petición.
          - Cuándo se realiza el traslado (recogida + viaje).
        """
        rutas = self._rutas_para(v, req.origin, req.destination)
        if rutas is None:
            print(f"[t={self.estado.tiempo_sim:>3}] No hay rutas válidas para {req.id} con {v.id}")
            return type("Asig", (), {"ok": False, "fin": self.estado.tiempo_sim})
        (r1, _), (r2, _) = rutas

        r_total = _join_paths(r1, r2)
        print(
            f"[t={self.estado.tiempo_sim:>3}] "
            f"Intentando asignar petición {req.id} ({req.origin}->{req.destination}) al vehículo {v.id} "
            f"(nodos totales ruta={len(r_total)})"
        )
        ok = ensure_energy_for(self.world, self.estado, v, r_total, path_mode=self.path_mode)
        
        if not ok:
            print(
                f"[t={self.estado.tiempo_sim:>3}] "
                f"FALLO de energía/ruta: no se puede asignar {req.id} al vehículo {v.id}"
            )
            return type("Asig", (), {"ok": False, "fin": self.estado.tiempo_sim})

        # Si llegamos aquí, tenemos energía suficiente (posiblemente tras repostar)
        print(
            f"[t={self.estado.tiempo_sim:>3}] "
            f"Asignación CONFIRMADA: {req.id} -> {v.id}. Ejecutando recogida y viaje..."
        )
        aplicar_tramo(self.world, self.estado, v, r1, nota=f"recogida {req.id}")
        aplicar_tramo(self.world, self.estado, v, r2, nota=f"viaje {req.id}")

        fin = self.estado.vehiculo_libre_en[v.id]
        self.estado.viajes_por_vehiculo[v.id] = self.estado.viajes_por_vehiculo.get(v.id, 0) + 1
        self.estado.vehiculo_ultimo_fin[v.id] = fin

        # Reporting (CSV/JSON + stats). Prefer the structured RegistroViaje used by sim/report.py.
        if self.reporter is not None:
            try:
                from .report import RegistroViaje

                # Recompute route aggregates (time, energy, km) for pickup and trip.
                t_pick, en_pick, km_pick = sum_path(self.world, v, r1)
                t_trip, en_trip, km_trip = sum_path(self.world, v, r2)

                pricing = self.world.cost_model.pricing or {}
                weights = self.world.cost_model.weights or {}
                p_en = pricing.get("kwh" if v.kind == "EV" else "liter", 0.0)
                price = (
                    (en_pick + en_trip) * p_en
                    + (km_pick + km_trip) * weights.get("per_km", 0.0)
                    + (t_pick + t_trip) * weights.get("per_min", 0.0)
                )

                t_start = int(getattr(self.estado, "tiempo_sim", 0))
                self.reporter.log(RegistroViaje(
                    request_id=req.id,
                    vehicle_id=v.id,
                    t_start=t_start,
                    t_finish=int(fin),
                    origin=req.origin,
                    destination=req.destination,
                    route_to_pickup=list(r1),
                    route_trip=list(r2),
                    dist_to_pickup_km=float(km_pick),
                    dist_trip_km=float(km_trip),
                    time_to_pickup_min=float(t_pick),
                    time_trip_min=float(t_trip),
                    energy_used=float(en_pick + en_trip),
                    price=float(price),
                ))
            except Exception:
                # Fallback to legacy dictionary logger if present.
                if hasattr(self.reporter, "add_trip"):
                    self.reporter.add_trip(req, v, r1, r2, fin)

        print(
            f"[t~{fin:>3}] Vehículo {v.id} ha COMPLETADO la petición {req.id} "
            f"(origen={req.origin}, destino={req.destination})"
        )
        return type("Asig", (), {"ok": True, "fin": fin})

    def repostar_si_conviene(self, v) -> bool:
        """Repostaje preventivo ligero si al vehículo le conviene.

        Se asume que el simulador ya ha comprobado que el vehículo está libre en el tiempo actual
        y que su energía es menor de un umbral. Aquí solo buscamos una instalación alcanzable cercana
        y aplicamos el tramo si es viable.
        """
        t_actual = getattr(self.estado, "tiempo_sim", 0)
        libre_en = self.estado.vehiculo_libre_en.get(v.id, 0)
        if libre_en > t_actual:
            # No está libre todavía
            return False

        pos = self.estado.posicion_vehiculo[v.id]

        res = nearest_facility_path(self.world, pos, v, mode=self.path_mode)
        if res is None:
            return False

        path, tmin, en, km, fac = res

        # Si la ruta no implica movimiento real, no tiene sentido repostar
        if not path or len(path) <= 1 or path[-1] == pos:
            return False

        # Si no tiene suficiente energía ni siquiera para llegar a la instalación, no hacemos nada aquí
        if v.energy_now < en or tmin <= 0:
            return False

        from .engine import aplicar_tramo
        print(f"[t={t_actual:>3}] {v.id} repostaje preventivo en {fac.node_id}")
        aplicar_tramo(self.world, self.estado, v, path, nota=f"repostaje preventivo en {fac.node_id}")

        # Actualizar tiempo libre del vehículo con el tiempo de servicio de la instalación
        self.estado.vehiculo_libre_en[v.id] = max(
            self.estado.vehiculo_libre_en[v.id],
            self.estado.tiempo_sim,
        ) + fac.service_min

        # Recargar / repostar
        v.energy_now = v.energy_max

        # Contador de repostajes (si se quiere usar en estadísticas)
        if hasattr(self.estado, "repostajes_por_vehiculo"):
            self.estado.repostajes_por_vehiculo[v.id] = (
                self.estado.repostajes_por_vehiculo.get(v.id, 0) + 1
            )

        return True
