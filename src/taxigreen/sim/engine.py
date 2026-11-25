
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from ..classes import World, Vehicle
from .energy import sum_path
from ..traffic import traffic_multiplier

@dataclass
class Evento:
    tiempo: int
    tipo: str
    vehiculo_id: str
    info: str

@dataclass
class EstadoSim:
    tiempo_sim: int = 0
    posicion_vehiculo: Dict[str, str] = field(default_factory=dict)
    vehiculo_libre_en: Dict[str, int] = field(default_factory=dict)
    eventos: List[Evento] = field(default_factory=list)
    repostajes_por_vehiculo: Dict[str, int] = field(default_factory=dict)
    tiempo_instalacion_por_vehiculo: Dict[str, float] = field(default_factory=dict)
    facility_servers: Dict[str, list] = field(default_factory=dict)
    espera_install_por_vehiculo: Dict[str, float] = field(default_factory=dict)
    viajes_por_vehiculo: Dict[str, int] = field(default_factory=dict)
    vehiculo_ultimo_fin: Dict[str, int] = field(default_factory=dict)

def iniciar_estado(world: World) -> EstadoSim:
    st = EstadoSim()
    st.posicion_vehiculo = {v.id: v.start_node for v in world.vehicles}
    st.vehiculo_libre_en = {v.id: 0 for v in world.vehicles}
    st.repostajes_por_vehiculo = {v.id: 0 for v in world.vehicles}
    st.tiempo_instalacion_por_vehiculo = {v.id: 0.0 for v in world.vehicles}
    st.espera_install_por_vehiculo = {v.id: 0.0 for v in world.vehicles}
    st.viajes_por_vehiculo = {v.id: 0 for v in world.vehicles}
    st.vehiculo_ultimo_fin = {v.id: 0 for v in world.vehicles}
    st.facility_servers = {}
    return st

def aplicar_tramo(world: World, st: EstadoSim, v: Vehicle, nodos: List[str], nota: str = "") -> Tuple[float,float,float]:
    """Aplica un tramo de ruta actualizando estado y aplicando un modelo sencillo de tráfico dinámico."""
    t_base, en, km = sum_path(world, v, nodos)
    # Hora de salida del tramo: nunca puede estar en el pasado respecto al tick actual.
    # (Si el vehículo ya estaba libre antes del tick, sale en el tick actual.)
    t_depart = max(st.vehiculo_libre_en.get(v.id, 0), st.tiempo_sim)
    factor = traffic_multiplier(t_depart)
    t_real = float(t_base) * factor
    v.energy_now -= en
    st.vehiculo_libre_en[v.id] = t_depart + int(round(t_real))
    st.posicion_vehiculo[v.id] = nodos[-1]
    st.eventos.append(Evento(st.vehiculo_libre_en[v.id], "mover", v.id, f"{nodos[0]}->{nodos[-1]} {int(round(t_real))}m {nota}"))
    return t_real, en, km
