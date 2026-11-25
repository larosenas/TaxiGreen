
import argparse
from src.taxigreen.sim_evt.simulator import run_simulation

def main():
    parser = argparse.ArgumentParser(description="Simulador TaxiGreen (motor evento)")
    parser.add_argument("--data", default="data/oviedo_city", help="Carpeta de datos")
    parser.add_argument("--strategy", choices=["ucs","astar"], default="ucs", help="Estrategia de pathfinding")
    parser.add_argument("--policy", choices=["fast","balance","nearest_origin","cheap"], default="fast", help="Política de asignación")
    parser.add_argument("--max-retries", type=int, default=3, help="Intentos máximos por petición")
    parser.add_argument("--cooldown-ticks", type=int, default=30, help="Ticks de espera entre reintentos")
    parser.add_argument("--vehicles", default=None, help="Nombre de JSON de vehículos (por defecto vehicles.json)")
    parser.add_argument("--out", default="out", help="Carpeta de resultados (metrics.json, trips.csv)")
    parser.add_argument("--quiet", action="store_true", help="No imprimir logs de detalle")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--fail-p", type=float, default=0.0)
    parser.add_argument("--fail-min", type=int, default=10)
    parser.add_argument("--fail-max", type=int, default=30)
    args = parser.parse_args()

    run_simulation(args.data, path_mode=args.strategy, policy=args.policy,
                   max_retries=args.max_retries, cooldown_ticks=args.cooldown_ticks,
                   vehicles_filename=args.vehicles, print_logs=(not args.quiet), out_dir=args.out,
                   seed=args.seed, fail_p=args.fail_p, fail_min=args.fail_min, fail_max=args.fail_max)

if __name__ == "__main__":
    main()
