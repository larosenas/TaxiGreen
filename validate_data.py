#!/usr/bin/env python3
from pathlib import Path
import json, sys

def _load_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def _try_jsonschema_validate(instance, schema):
    try:
        import jsonschema  # type: ignore
        jsonschema.validate(instance=instance, schema=schema)
        return []
    except ModuleNotFoundError:
        return None  # jsonschema es opcional: se hace solo la validación básica
    except Exception as e:
        return [f"Error de JSON Schema: {e}"]

def _basic_check_nodes(nodes):
    errs = []
    ids = set()
    for i, n in enumerate(nodes):
        if not isinstance(n.get("id"), str) or not n["id"]:
            errs.append(f"nodes[{i}].id inválido")
        if n.get("id") in ids:
            errs.append(f"id de nodo duplicado: {n['id']}")
        ids.add(n.get("id"))
        if n.get("kind") not in ("pickup","hub","poi"):
            errs.append(f"nodes[{i}].kind inválido: {n.get('kind')}")
    return errs

def _basic_check_edges(edges, node_ids):
    errs = []
    for i, e in enumerate(edges):
        a, b = e.get("from"), e.get("to")
        if a not in node_ids or b not in node_ids:
            errs.append(f"edge[{i}] refiere nodos inexistentes: {a}->{b}")
        if float(e.get("travel_min", 0)) <= 0 or float(e.get("distance_km", 0)) < 0:
            errs.append(f"edge[{i}] tiempos/distancias inválidos")
    return errs

def _basic_check_requests(reqs, node_ids):
    errs = []
    for i, r in enumerate(reqs):
        if r.get("origin") not in node_ids or r.get("destination") not in node_ids:
            errs.append(f"request[{i}] nodos inexistentes: {r.get('origin')}->{r.get('destination')}")
    return errs

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Validador de datasets TaxiGreen")
    ap.add_argument("--data", required=True, help="Carpeta de datos (contiene *.json)")
    ap.add_argument("--schemas", required=True, help="Carpeta con schemas *.schema.json")
    args = ap.parse_args()

    data = Path(args.data); sch = Path(args.schemas)
    files = {
        "nodes.json":"nodes.schema.json",
        "edges.json":"edges.schema.json",
        "facilities.json":"facilities.schema.json",
        "vehicles.json":"vehicles.schema.json",
        "cost_model.json":"cost_model.schema.json",
        "requests.json":"requests.schema.json"
    }

    problems = []
    cache = {}
    schema_skipped = False
    for fname, sname in files.items():
        fp = data / fname
        sp = sch / sname
        if not fp.exists():
            problems.append(f"Falta {fp}")
            continue
        inst = _load_json(fp); cache[fname] = inst
        schema = _load_json(sp)
        schema_errs = _try_jsonschema_validate(inst, schema)
        if schema_errs is None:
            schema_skipped = True
        else:
            problems.extend(schema_errs)

    if schema_skipped:
        print("Aviso: jsonschema no está instalado; usando solo validación básica")

    # Validación básica enlazada (sin jsonschema)
    if "nodes.json" in cache:
        node_ids = {n["id"] for n in cache["nodes.json"] if isinstance(n.get("id"), str)}
        problems.extend(_basic_check_nodes(cache["nodes.json"]))
        if "edges.json" in cache:
            problems.extend(_basic_check_edges(cache["edges.json"], node_ids))
        if "requests.json" in cache:
            problems.extend(_basic_check_requests(cache["requests.json"], node_ids))

    if problems:
        print("VALIDACIÓN: HAY PROBLEMAS")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("VALIDACIÓN: OK")

if __name__ == "__main__":
    main()
