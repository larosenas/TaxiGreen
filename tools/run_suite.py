
#!/usr/bin/env python3
import shutil
import argparse, os, json, csv, importlib, sys
from pathlib import Path
from itertools import product

# asegurar sys.path root
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

sim = importlib.import_module("src.taxigreen.sim_evt.simulator")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/oviedo_city")
    ap.add_argument("--vehicles", default="")
    ap.add_argument("--strategies", default="ucs,astar")
    ap.add_argument("--policies", default="fast,cheap,balance")
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--cooldown", type=int, default=30)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--out", default="out_suite")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fail-p", type=float, default=0.0)
    ap.add_argument("--fail-min", type=int, default=10)
    ap.add_argument("--fail-max", type=int, default=30)
    ap.add_argument(
    "--keep-runs",
    action="store_true",
    help="Keep per-run folders under out/runs/<tag> (metrics.json, trips.csv, etc.). By default they are deleted after aggregating summary."
    )

    args = ap.parse_args()

    data_dir = Path(args.data)
    out_root = Path(args.out); ensure_dir(out_root); ensure_dir(out_root / "plots"); runs_root = out_root / "runs"; ensure_dir(runs_root)

    vehs = [v.strip() for v in args.vehicles.split(",") if v.strip()] if args.vehicles.strip() else []
    if not vehs:
        candidates = ["vehicles.json", "vehicles2.json"]
        vehs = [v for v in candidates if (data_dir / v).exists()] or ["vehicles.json"]

    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]
    policies = [p.strip() for p in args.policies.split(",") if p.strip()]

    summary = []
    for veh in vehs:
        for strat in strategies:
            for pol in policies:
                tag = f"{Path(args.data).name}_{Path(veh).stem}_{strat}_{pol}"
                out_dir = runs_root / tag
                ensure_dir(out_dir)
                res = sim.run_simulation(
                    str(data_dir), strat, pol, args.retries, args.cooldown, veh, (not args.quiet), str(out_dir),
                    seed=args.seed, fail_p=args.fail_p, fail_min=args.fail_min, fail_max=args.fail_max
                )

                metrics_path = out_dir / "metrics.json"
                metrics = json.loads(metrics_path.read_text(encoding="utf-8-sig")) if metrics_path.exists() else {}
                summary.append({
                    "tag": tag, "strategy": strat, "policy": pol, "vehicles": veh,
                    "done": res.get("done"), "rejected": res.get("rejected"), "t_end": res.get("t_end"),
                    "km_vacio": metrics.get("km_vacio"), "km_pasajero": metrics.get("km_pasajero"),
                    "co2_kg": metrics.get("co2_kg"), "coste": metrics.get("costeu"), "t_resp_prom": metrics.get("t_resp_prom"),
                    "t_facility_wait": metrics.get("t_facility_wait"),
                    "t_facility_service": metrics.get("t_facility_service"),
                    "n_refuels": metrics.get("n_refuels"),
                    "utilization": metrics.get("utilization"),
                    "facility_failures": metrics.get("facility_failures"),
                    "t_facility_down_wait": metrics.get("t_facility_down_wait"),
                    "search_expansions": metrics.get("search_expansions"),
                    "search_pops": metrics.get("search_pops"),
                    "search_pushes": metrics.get("search_pushes"),
                    "search_path_calls": metrics.get("search_path_calls")
                })
                if not args.keep_runs:
                    try:
                        shutil.rmtree(out_dir, ignore_errors=True)
                    except Exception:
                        pass

    (out_root / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(out_root / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()) if summary else ["tag"])
        w.writeheader(); w.writerows(summary)

    try:
        ensure_dir(out_root / "plots")
        import matplotlib.pyplot as plt
        tags = [r["tag"] for r in summary]
        for key, title in [
            ("done","Completadas"),
            ("rejected","Rechazadas"),
            ("t_resp_prom","Tiempo resp. prom."),
            ("coste","Coste total"),
            ("co2_kg","CO2 total (kg)"),
            ("t_facility_wait","Espera total en estaciones (min)"),
            ("t_facility_service","Servicio total en estaciones (min)"),
            ("n_refuels","Nº recargas/repostajes"),
            ("utilization", "Ocupación de la flota (0-1)"),
            ("facility_failures", "Fallos de estación"),
            ("t_facility_down_wait", "Espera por estación caída (min)"),
            ("search_expansions","Expansiones (búsqueda)"),
            ("search_pops","Pops (búsqueda)"),
            ("search_pushes","Pushes (búsqueda)")
        ]:
            vals = [r.get(key,0) or 0 for r in summary]
            plt.figure(); plt.bar(tags, vals); plt.xticks(rotation=45, ha="right"); plt.title(title); plt.tight_layout()
            plt.savefig(out_root / "plots" / f"{key}.png"); plt.close()
    except Exception as e:
        print("Aviso: no se generaron gráficas:", e)

if __name__ == "__main__":
    main()
