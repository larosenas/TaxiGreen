# TaxiGreen: Dynamic Fleet Dispatch and Route Planning with Search (UCS / A\*)

Project report for the Artificial Intelligence course. All numbers below can be reproduced with the commands in [Appendix A](#appendix-a-reproduction).

## Summary

This project models an urban taxi service as a search-and-simulation problem. The city is a directed graph whose edges carry travel time and distance. A mixed fleet of electric (EV) and combustion (ICE) vehicles serves requests that arrive over time, and recharges or refuels at stations that have limited capacity, service times and possible failures.

We compare two route-planning strategies, Uniform Cost Search (Dijkstra) and A\*, and three dispatch policies (`fast`, `cheap`, `balance`), in a baseline setting and under station failures. Evaluation uses operational metrics (mean response time, cost, CO₂, empty kilometres, rejections, utilisation) and search-effort metrics (node expansions, priority-queue pops and pushes). The search-effort metrics let us tell UCS and A\* apart even when both return the same optimal routes.

## 1. Problem description

TaxiGreen assigns vehicles to transport requests that arrive over time, plans routes on a road network and respects energy and range constraints. Because the fleet is mixed, the simulation includes charging and refuelling at stations with limited capacity, service times and queues. The goal is to maximise served requests while keeping response time, cost, CO₂ and empty kilometres low, under dynamic conditions such as station failures.

The system:

- loads scenarios from `data/<scenario>/` (nodes, edges, stations, requests and fleet);
- advances time with an event-driven engine (`sim_evt`);
- plans routes with UCS or A\*;
- selects vehicles with the `fast`, `cheap` or `balance` policy;
- exports aggregate metrics (`metrics.json`), per-trip traces (`trips.csv`) and experiment summaries (`summary.csv`).

## 2. Formulation as a search problem

The project has two levels of search:

1. **Route search** on the graph, a classic shortest-path problem.
2. **Dispatch decision**, choosing a vehicle for each request, which relies on estimated routes and a scoring function.

### 2.1 State

- *Route subproblem*: the current node (the vehicle's position on the graph).
- *Simulation and dispatch*: the current time `t`; for each vehicle its node, availability, type (EV/ICE), remaining energy and service status; for each request whether it is pending, served or rejected (and its deadline, if any); for each station its queue, service time and status (e.g. down until `down_until`).

### 2.2 Initial state

- Fleet from `vehicles.json`: start positions, initial energy, EV/ICE type.
- Graph and stations from `nodes.json`, `edges.json` and `facilities.json`.
- Scheduled requests from `requests.json`.
- Cost and pricing model from `cost_model.json`.

### 2.3 Goal test

- *Routes*: the destination node is reached.
- *Service*: some vehicle can reach the origin, pick up the passenger and reach the destination, charging or refuelling on the way if needed, without violating operational constraints.

### 2.4 Actions

- Traverse an edge.
- Start charging or refuelling at a station, possibly after waiting in its queue.
- Complete the empty leg (vehicle → origin) and the passenger leg (origin → destination).
- Retry a request after a cooldown.
- Reject a request that cannot be served (constraints, deadline or retry limit).

### 2.5 Solution cost

- *Routes*: accumulated travel time in minutes. UCS and A\* minimise the same objective.
- *Dispatch*: candidates are ranked by a policy-dependent score:
  - `fast` minimises estimated time;
  - `cheap` minimises an estimated monetary cost (km + minutes + energy) from the cost model;
  - `balance` combines both.

Requests arrive online, so costs are minimised per request as decisions are taken, not through a global optimisation.

## 3. Environment model

- **Nodes**: urban zones, intersections or stops.
- **Edges**: directed, with `distance_km`, `travel_min`, and a time-of-day traffic multiplier applied when driving.
- **Stations**: located at nodes, with `capacity` (parallel service slots), `service_min` (service time) and a FIFO queue when full.

Scenario used in the experiments: `data/oviedo_refuel_stress/` (6 nodes, 9 edges, 4 stations, 4 vehicles, 10 chained requests with tight energy margins).

## 4. Methods

### 4.1 Route planning

**UCS (Dijkstra).** Finds the minimum-time path from start to goal. It is complete and optimal with non-negative edge costs.

**A\*.** Uses the heuristic

```text
h(n) = hops_lb(n, goal) × min_edge_time
```

where `hops_lb` is the minimum number of edges from `n` to the goal (breadth-first search on the directed graph) and `min_edge_time` is the smallest edge travel time in the graph. Any path from `n` to the goal has at least `hops_lb` edges, each taking at least `min_edge_time`, so the heuristic never overestimates. It is admissible, and A\* returns the same optimal routes as UCS. The heuristic is simple, but it is enough to steer the search and reduce effort.

### 4.2 Dispatch policies

For each candidate vehicle the system computes the vehicle → origin and origin → destination routes, the estimated times, and an estimated cost.

- **`fast`**: score dominated by estimated time.
- **`cheap`**: score dominated by estimated monetary cost, using cost per km (`weights.per_km`), cost per minute (`weights.per_min`) and the energy price for the vehicle type (`pricing.kwh` for EV, `pricing.liter` for ICE). Kilometres and energy are estimated from the planned route.
- **`balance`**: a weighted combination of time and cost.

### 4.3 Search-effort instrumentation

Routing is instrumented with counters: `search_path_calls` (route-planning calls), `search_pops` (priority-queue pops), `search_pushes` (priority-queue pushes) and `search_expansions` (node expansions).

## 5. Dynamic simulation

### 5.1 Flow

At each relevant instant, pending requests are considered in priority order, a vehicle is selected according to the policy, and the service is executed: empty leg to the origin, passenger leg to the destination, and charging or refuelling (queue + service) when required. State and metrics are then updated.

### 5.2 Dynamics

- Requests arriving over time.
- Energy consumption, charging and refuelling.
- Station queues caused by limited capacity.
- **Station failures**, on demand: when a vehicle tries to use a station that is down (`now < down_until`), it waits until `down_until`. Otherwise, with probability `fail_p` the station fails for a duration drawn uniformly from `[fail_min, fail_max]`. Everything is reproducible through the random seed.

## 6. Metrics

- **Service**: `done` (served), `rejected`, `t_resp_prom` (mean response time, min), `t_end` (total simulated time).
- **Operations**: `km_vacio` / `km_pasajero` (empty / passenger km), `co2_kg`, `coste` (total cost), `utilization` (busy time / (horizon × fleet size)).
- **Stations**: `t_facility_wait` (queue time), `t_facility_service`, `n_refuels`, `facility_failures`, `t_facility_down_wait` (time waiting for a failed station).
- **Search effort**: `search_path_calls`, `search_pops`, `search_pushes`, `search_expansions`.

## 7. Experiments

### 7.1 Setup

- Scenario: `data/oviedo_refuel_stress`
- Strategies: `ucs`, `astar`
- Policies: `fast`, `cheap`, `balance`
- **Baseline**: `seed = 0`, `fail_p = 0`
- **Failures**: `seed = 1`, `fail_p = 0.5`, `fail_min = fail_max = 10`

### 7.2 Results

Operational metrics (identical for UCS and A\*; `balance` identical to `fast`):

| Scenario | Policy | Served | Rejected | t_end | Mean response (min) | Empty km | CO₂ (kg) | Cost (€) | Utilisation |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | fast | 8 | 2 | 77 | 11.25 | 5.8 | 0.668 | 32.53 | 0.308 |
| Baseline | cheap | 9 | 1 | 95 | 16.67 | 11.6 | 0.824 | 41.75 | 0.301 |
| Failures | fast | 8 | 2 | 77 | 18.75 | 5.8 | 0.668 | 36.53 | 0.373 |
| Failures | cheap | 9 | 1 | 95 | 23.33 | 11.6 | 0.824 | 45.75 | 0.354 |

Search effort:

| Scenario | Policy | Strategy | Expansions | Pops | Pushes | Path calls |
|---|---|---|---:|---:|---:|---:|
| Baseline | fast | UCS | 252 | 358 | 320 | 111 |
| Baseline | fast | A\* | 233 | 339 | 312 | 111 |
| Baseline | cheap | UCS | 243 | 346 | 310 | 108 |
| Baseline | cheap | A\* | 226 | 329 | 302 | 108 |
| Failures | fast | UCS | 265 | 381 | 342 | 118 |
| Failures | fast | A\* | 244 | 360 | 332 | 118 |
| Failures | cheap | UCS | 256 | 369 | 332 | 115 |
| Failures | cheap | A\* | 237 | 350 | 322 | 115 |

## 8. Discussion

**UCS vs A\*.** Both strategies produce the same operational outcome, since they find the same optimal routes and therefore the same dispatch decisions. A\* does so with less work: in every configuration it expands 7–8% fewer nodes and pops about 5% fewer entries from the priority queue (e.g. baseline/`fast`: 252 → 233 expansions, 358 → 339 pops). This matches theory, and the effect is visible even on a small graph. It would grow with the size of the network and the number of routing calls.

**`fast` vs `cheap`.** `cheap` serves one more request (9 vs 8) and rejects one fewer, but it doubles empty kilometres (5.8 → 11.6) and increases simulated time, mean response time, CO₂ and total cost. Optimising estimated cost per request can choose vehicles that make acceptance possible but lead to longer, emptier operations overall.

**`balance`.** It matches `fast` on this scenario. With few candidate vehicles, the cost term in the score was never large enough to change the ranking.

**Station failures.** Two 10-minute outages add 20 minutes of downtime waiting. Mean response time rises from 11.25 to 18.75 minutes under `fast` (+67%), cost rises from €32.53 to €36.53, and utilisation increases because vehicles spend time waiting. Served and rejected counts do not change: with these parameters, the system absorbs the failures by degrading time and cost rather than losing service.

**Limitations.** The results depend on the scenario (graph size, request pattern, station capacity). The failure experiment uses a single seed; several seeds should be evaluated to estimate variability (`experiments/report/03_run_fail_seeds.ps1` runs ten).

## 9. Conclusions

- A\* does not change the solution compared with UCS, but it reduces search effort. That makes it preferable whenever many routes must be planned, as in fleet dispatch.
- As defined, `cheap` completes more services in this scenario at the expense of time, cost and CO₂.
- Station failures clearly degrade response time and cost, and raise utilisation because of the added waiting.
- Reporting both operational and search-effort metrics is what makes the informed vs uninformed search comparison visible.

## Appendix A: Reproduction

```bash
# Baseline
python tools/run_suite.py --data data/oviedo_refuel_stress --out out_suite/baseline --quiet \
  --seed 0 --fail-p 0 --strategies ucs,astar --policies fast,cheap,balance

# Station failures
python tools/run_suite.py --data data/oviedo_refuel_stress --out out_suite/fail --quiet \
  --seed 1 --fail-p 0.5 --fail-min 10 --fail-max 10 --strategies ucs,astar --policies fast,cheap,balance
```

Each command writes `summary.csv` and `summary.json`. With `pandas` and `matplotlib` installed, plots are generated as well. On Windows, `experiments/report/00_run_all.ps1` runs the full pipeline and produces the report figures.
