# Scenarios

Each subfolder is a self-contained scenario that can be passed to `run_sim.py --data <folder>`.
See the [README](../README.md#scenarios) for a summary and [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md#scenario-file-format) for the file format.

| Folder | Purpose |
|---|---|
| `oviedo_city/` | Main Oviedo scenario |
| `oviedo_city_directed/` | Same city, every edge with its reverse |
| `oviedo_refuel_easy/` | Vehicles that must charge or refuel before their first trip |
| `oviedo_refuel_stress/` | Chained requests that force repeated refuelling (used in the report) |
| `demo_peticiones_ab/` | Minimal directed-graph demo |

The JSON files directly in `data/` are a small fixture used by the unit tests (`tests/test_loaders_*.py`, `tests/test_deadline.py`). Do not remove them.
