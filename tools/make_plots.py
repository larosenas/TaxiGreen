import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

PLOTS_DIR = Path("experiments") / "report" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

for p in PLOTS_DIR.glob("*.png"):
    p.unlink(missing_ok=True)


BASE = Path("experiments/report/baseline/summary.csv")
FAIL = Path("experiments/report/fail/summary.csv")
OUT  = Path("experiments/report/plots")
OUT.mkdir(parents=True, exist_ok=True)

base = pd.read_csv(BASE)
fail = pd.read_csv(FAIL)
base["scenario"] = "baseline"
fail["scenario"] = "fail"
df = pd.concat([base, fail], ignore_index=True)

def save_bar(metric: str, title: str, policies=("fast","cheap","balance")):
    d = df[df["policy"].isin(policies)].copy()
    d["label"] = (
        d["scenario"].astype(str)
        .str.cat(d["strategy"].astype(str), sep=" | ")
        .str.cat(d["policy"].astype(str), sep=" | ")
    )
    d = d.sort_values(["scenario","strategy","policy"])
    ax = d.plot(kind="bar", x="label", y=metric, legend=False, rot=25)
    ax.set_title(title)
    ax.set_ylabel(metric)
    plt.tight_layout()
    plt.savefig(OUT / f"{metric}.png", dpi=200)
    plt.close()

# Operational metrics (report-ready)
save_bar("t_resp_prom", "Mean response time (min)", policies=("fast","cheap"))
save_bar("rejected", "Rejected requests", policies=("fast","cheap"))
save_bar("coste", "Total monetary cost", policies=("fast","cheap"))
save_bar("co2_kg", "Total CO2 (kg)", policies=("fast","cheap"))
save_bar("km_vacio", "Empty kilometers", policies=("fast","cheap"))

# Search effort (UCS vs A*)
save_bar("search_expansions", "Search expansions (UCS vs A*)", policies=("fast","cheap","balance"))