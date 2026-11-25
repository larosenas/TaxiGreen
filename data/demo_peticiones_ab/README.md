# demo_peticiones_ab

Minimal directed-graph demo.

- **R1** A → B: direct edge.
- **R2** A2 → B2: no direct edge, so the route must go through C2.
- **R3** D → A: impossible, because D has no outgoing edges.

```bash
python run_sim.py --data data/demo_peticiones_ab
```
