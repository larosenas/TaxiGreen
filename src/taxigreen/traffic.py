from __future__ import annotations

def traffic_multiplier(now_min: int | float | None) -> float:
    """Devuelve un factor multiplicador para los tiempos de viaje en función de la hora.

    now_min: tiempo actual de simulación en minutos (puede ser float). Se interpreta
    como minutos desde t=0; internamente se proyecta a una hora del día (0–23h).

    El modelo es deliberadamente simple:
      - Madrugada (0–6h): tráfico muy fluido -> 0.7
      - Hora punta mañana (7–9h): tráfico denso -> 1.5
      - Horario laboral (9–17h): tráfico algo más lento -> 1.2
      - Hora punta tarde (17–19h): tráfico muy denso -> 1.6
      - Tarde/noche (19–22h): ligero aumento -> 1.1
      - Resto (22–24h): casi normal -> 0.9

    Devolvemos siempre un factor > 0 para evitar tiempos nulos o negativos.
    """
    if now_min is None:
        return 1.0
    try:
        t = float(now_min)
    except (TypeError, ValueError):
        return 1.0
    if t < 0:
        t = 0.0
    # proyectar a hora del día
    h = int(t // 60) % 24

    if 0 <= h < 6:
        return 0.7
    if 7 <= h < 9:
        return 1.5
    if 9 <= h < 17:
        return 1.2
    if 17 <= h < 19:
        return 1.6
    if 19 <= h < 22:
        return 1.1
    return 0.9
