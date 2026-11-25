# Architecture

This document describes how the code is organised and how a simulation runs from start to finish. For the overview and results, see the [README](../README.md).

## Two engines

The repository contains two simulation engines:

| Engine | Location | Time model | Used by |
|---|---|---|---|
| **Event-driven** (current) | `src/taxigreen/sim_evt/` | Jumps to the next event | `run_sim.py`, `tools/run_suite.py`, the report experiments |
| **Tick-based** (original) | `src/taxigreen/sim/` | Fixed steps of N simulated minutes | `tools/legacy_sweep.py` and most unit tests |

The tick-based engine was the first version of the project. The event-driven engine replaced it as the main simulator: it is self-contained, adds A\* with an admissible heuristic, search-effort counters, station failures and the traffic model. The original engine is kept because the test suite and `tools/legacy_sweep.py` still use it.

## Event-driven engine (`sim_evt/`)

### `engine.py`: world model, routing and trip execution

- **Data classes**: `Edge`, `Facility`, `Vehicle`, `Request`, `World`.
- **Routing**:
  - `dijkstra_time(world, start, goal, stats)`: UCS over `travel_min`.
  - `astar_time(world, start, goal, stats)`: A\* with `h(n) = hops_lb(n, goal) × min_edge_time`. `_hop_lb` is a BFS hop count on the directed graph and `_min_edge_time` is the smallest edge time.
  - Both functions update the shared `stats` dictionary (`path_calls`, `pops`, `pushes`, `expansions`, …).
- **Energy**: `sum_path` returns time, energy and km for a node path. Energy is `km × consumption_per_km`, in kWh for EVs and litres for ICE vehicles.
- **Stations**:
  - `nearest_reachable_facility` finds the closest station of the right type (EV → `charger`, ICE → `gas`) that the vehicle can still reach.
  - `queue_service` models `capacity` parallel slots and returns the wait and finish time for an arrival.
- **Execution**:
  - `drive_with_refuels` drives a path leg by leg, detouring to a station whenever the remaining energy is not enough. It applies the time-of-day traffic multiplier and the failure model.
  - `assign_and_execute` runs the empty leg and the passenger leg and accumulates metrics.

### `simulator.py`: loading, dispatch loop and output

1. **Loading** (`_load_world`): reads the scenario JSON and normalises field names. Several synonyms are accepted (`src`/`from`, `origin`/`from`, `t_min`/`time`, …). The cost model is merged over defaults.
2. **Main loop** (`run_simulation`):
   - move requests whose arrival time has passed into the pending list;
   - process pending requests by `(-priority, arrival time, id)`;
   - reject requests that exceeded `wait_max` / `deadline_min`;
   - filter candidate vehicles (free, enough seats, matching `vehicle_pref`);
   - for each candidate, plan vehicle → origin and origin → destination, estimate time, km, energy and cost, and score with `_score` according to the policy;
   - execute the best candidate, or schedule a retry after `cooldown_ticks` (rejecting after `max_retries`);
   - advance `t` to the next event: the next arrival, the next vehicle becoming free, or the next retry.
3. **Output**: `metrics.json` (totals, service, station, utilisation and search metrics) and `trips.csv` (one row per served request).

### Scoring (`_score`)

| Policy | Score (lower is better) |
|---|---|
| `fast` | `t_origin + t_destination` |
| `nearest_origin` | `(t_origin, t_total)` |
| `cheap` | `(estimated_cost, t_total)` |
| `balance` | `0.5 × t_total + estimated_cost` |

`estimated_cost = km × per_km + minutes × per_min + energy × energy_price`. A request with `pref_env = "eco"` adds a large penalty to ICE vehicles, so an EV is chosen whenever one is available.

### Station failures

When a vehicle arrives at a station:

1. if the station is down (`now < down_until`), the vehicle waits until it recovers (counted in `t_facility_down_wait`);
2. otherwise, with probability `fail_p`, the station fails for a random whole number of minutes in `[fail_min, fail_max]` (counted in `facility_failures`).

The random generator is seeded with `--seed`, so runs are reproducible.

### Traffic (`src/taxigreen/traffic.py`)

Driving time is `travel_min × traffic_multiplier(hour)`. The multiplier depends on the hour of the day: 0.7 at night, 1.5 in the morning rush, 1.2 during working hours, 1.6 in the evening rush, 1.1 in the evening, 0.9 otherwise. Route planning uses the base `travel_min`, so the heuristic stays admissible.

## Original engine (`sim/`)

Built on the domain model in `classes/` (`Node`, `Edge`, `Facility`, `Vehicle`, `Request`, `CostModel`, `World`), loaded by `io/loaders.py` and assembled by `world.py`.

| Module | Role |
|---|---|
| `simulator.py` | Tick loop: arrivals → dispatch → energy → execution → reports |
| `dispatcher.py` | Candidate selection and policy scoring |
| `pathfinding.py` | Shortest path by time |
| `energy.py` | Energy accounting and nearest-station search |
| `engine.py` | Vehicle state and leg execution |
| `reposition.py` | Moves idle vehicles to hubs when they get stuck |
| `requests_repo.py` | Pending and served request bookkeeping |
| `validator.py` | Pre-run check that every request has a path |
| `report.py` | `trips_report.json/csv`, `stats_report.json` |
| `clock.py` | Simulation clock |

## Tooling

- `tools/run_suite.py`: runs every strategy × policy × fleet combination for a scenario and writes `summary.csv` / `summary.json`, plus bar charts if `pandas` and `matplotlib` are available.
- `tools/make_svg_charts.py`: builds the README charts as light and dark SVGs, using only the standard library.
- `tools/make_plots.py`: builds the report figures from the baseline and failure summaries (needs `pandas` and `matplotlib`).
- `tools/legacy_sweep.py`: strategy × policy × fleet sweep on the original engine.
- `experiments/report/*.ps1`: Windows pipeline that runs the baseline, the failure scenario, an optional ten-seed batch, and the plots.
- `validate_data.py`: checks a scenario against `schemas/*.schema.json` (if `jsonschema` is installed) plus consistency checks (unique node ids, edges and requests referencing existing nodes, positive travel times).

## Scenario file format

| File | Content |
|---|---|
| `nodes.json` | `[{"id": "URIA", "name": "...", "kind": "pickup"}]`, where `kind` is `pickup`, `hub` or `poi` |
| `edges.json` | Directed edges: `{"from", "to", "distance_km", "travel_min"}` |
| `facilities.json` | `{"id", "node_id", "type": "gas"/"charger", "capacity", "service_min", "price_per_unit"}` |
| `vehicles.json` | `{"id", "kind": "EV"/"ICE", "energy_max", "energy_now", "consumption_per_km", "start_node", "capacity_pax"}` |
| `requests.json` | `{"id", "t_min", "origin", "destination", "pax", "priority", "vehicle_pref"}`, optionally `deadline_min` / `wait_max` and `pref_env` |
| `cost_model.json` | `{"weights": {"per_km", "per_min"}, "pricing": {"kwh", "liter"}, "co2_per_km_ice", "co2_per_km_ev"}` |
