
"""Strategy x policy x fleet sweep on the original tick-based engine (src/taxigreen/sim).

Usage (from the repository root):  python tools/legacy_sweep.py
Writes out/experiments_summary.csv.
"""
from pathlib import Path
import itertools, json, csv, time, sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.taxigreen.sim.simulator import run_simulation

def correr(data_dir: Path, out_dir: Path, strategies, policies, fleet_files):
    resultados = []
    for strat, pol, fleet in itertools.product(strategies, policies, fleet_files):
        t0 = time.time()
        run_simulation(
            data_dir=data_dir,
            out_dir=out_dir,
            path_mode=strat,
            policy=pol,
            vehicles_filename=fleet,
            speed_min_per_tick=8,
            sleep_per_tick=0.0,
        )
        t1 = time.time()
        stats_path = out_dir / "stats_report.json"
        trips_path = out_dir / "trips_report.json"
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        viajes = json.loads(trips_path.read_text(encoding="utf-8"))
        n_serv = len([v for v in viajes if v.get("ok", True)])
        n_rech = stats.get("rejected", 0)
        tiempo = stats.get("sim_minutes_total", 0)
        coste = stats.get("cost_total", 0)
        km_vacios = stats.get("km_empty", 0)
        resultados.append({
            "strategy": strat,
            "policy": pol,
            "fleet": "2" if fleet.endswith("2.json") else "1",
            "served": n_serv,
            "rejected": n_rech,
            "sim_minutes": tiempo,
            "total_cost": coste,
            "empty_km": km_vacios,
            "wall_sec": round(t1 - t0, 2),
        })
    return resultados

def guardar_csv(fila_dicts, path: Path):
    if not fila_dicts:
        return
    campos = list(fila_dicts[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in fila_dicts:
            w.writerow(r)

def main():
    base = Path("data/oviedo_city")
    out = Path("out")
    out.mkdir(exist_ok=True)
    estrategias = ["ucs", "astar"]
    politicas = ["fast", "cheap", "balance", "least_idle", "nearest_origin"]
    flotas = ["vehicles.json"] + (["vehicles2.json"] if (base / "vehicles2.json").exists() else [])
    res = correr(base, out, estrategias, politicas, flotas)
    guardar_csv(res, Path("out/experiments_summary.csv"))
    print("Experimentos listos en out/experiments_summary.csv")

if __name__ == "__main__":
    main()
