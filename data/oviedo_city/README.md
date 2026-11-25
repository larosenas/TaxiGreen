# oviedo_city

Directed graph of central Oviedo. Nodes: URIA, CALATRAVA, MILAN, CATEDRAL, ESTACION, HUCA.

Requests worth noting:

- **R1** URIA → CATEDRAL: a direct edge exists.
- **R2** MILAN → CALATRAVA: needs a multi-hop route.
- **R3** CATEDRAL → HUCA: impossible with this graph, so it exercises rejection.

Fleets:

- `vehicles.json`: 1 EV + 1 ICE
- `vehicles2.json`: 3 EV + 3 ICE
- `vehicles3.json`: alternative fleet
