#!/usr/bin/env python3
"""Generate the README charts as dependency-free SVG files.

Reads the summary.csv files written by tools/run_suite.py for the baseline and
station-failure experiments and writes:

  docs/img/search_effort_{light,dark}.svg    UCS vs A* node expansions
  docs/img/policy_tradeoff_{light,dark}.svg  fast vs cheap on the baseline scenario

The README picks the light or dark variant to match the GitHub theme.

Usage (from the repository root):
  python tools/run_suite.py --data data/oviedo_refuel_stress --out out_suite/baseline --quiet \
      --seed 0 --fail-p 0 --strategies ucs,astar --policies fast,cheap,balance
  python tools/run_suite.py --data data/oviedo_refuel_stress --out out_suite/fail --quiet \
      --seed 1 --fail-p 0.5 --fail-min 10 --fail-max 10 --strategies ucs,astar --policies fast,cheap,balance
  python tools/make_svg_charts.py
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {
    "light": {"text": "#1f2328", "muted": "#59636e", "grid": "#d1d9e0",
              "s0": "#8c959f", "s1": "#0969da", "s2": "#bc4c00"},
    "dark": {"text": "#e6edf3", "muted": "#9198a1", "grid": "#3d444d",
             "s0": "#6e7681", "s1": "#4493f8", "s2": "#f0883e"},
}


def style(theme: str) -> str:
    c = THEMES[theme]
    return f"""
  <style>
    .title {{ font: 600 15px {FONT}; fill: {c['text']}; }}
    .label {{ font: 12px {FONT}; fill: {c['text']}; }}
    .muted {{ font: 12px {FONT}; fill: {c['muted']}; }}
    .value {{ font: 600 11px {FONT}; fill: {c['text']}; }}
    .grid  {{ stroke: {c['grid']}; stroke-width: 1; }}
    .s0 {{ fill: {c['s0']}; }}
    .s1 {{ fill: {c['s1']}; }}
    .s2 {{ fill: {c['s2']}; }}
  </style>
"""


def read_summary(path: Path) -> dict[tuple[str, str], dict[str, float]]:
    rows = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[(r["strategy"], r["policy"])] = {
                k: float(v) for k, v in r.items()
                if k not in ("tag", "strategy", "policy", "vehicles")
            }
    return rows


def svg(width: int, height: int, body: list[str], title: str, theme: str) -> str:
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{title}">',
        f"<title>{title}</title>",
        style(theme),
        *body,
        "</svg>",
        "",
    ])


def legend(x: float, y: float, items: list[tuple[str, str]]) -> list[str]:
    out = []
    for cls, text in items:
        out.append(f'<rect x="{x}" y="{y - 10}" width="12" height="12" rx="2" class="{cls}"/>')
        out.append(f'<text x="{x + 18}" y="{y}" class="label">{text}</text>')
        x += 18 + 8 * len(text) + 24
    return out


def search_effort_chart(base, fail, theme: str) -> str:
    groups = [
        ("Baseline · fast", base, "fast"),
        ("Baseline · cheap", base, "cheap"),
        ("Failures · fast", fail, "fast"),
        ("Failures · cheap", fail, "cheap"),
    ]
    W, left, right, top = 720, 130, 120, 70
    bar_h, gap_in, gap_out = 16, 4, 18
    group_h = 2 * bar_h + gap_in
    H = top + len(groups) * (group_h + gap_out) + 10
    vmax = max(d[(s, p)]["search_expansions"] for _, d, p in groups for s in ("ucs", "astar"))
    scale = (W - left - right) / (vmax * 1.05)

    body = ['<text x="0" y="20" class="title">Search effort: A* expands fewer nodes than UCS for the same routes</text>']
    body += legend(0, 48, [("s0", "UCS (Dijkstra)"), ("s1", "A*")])
    y = top
    for name, data, pol in groups:
        u = data[("ucs", pol)]["search_expansions"]
        a = data[("astar", pol)]["search_expansions"]
        body.append(f'<text x="{left - 10}" y="{y + group_h / 2 + 4}" text-anchor="end" class="label">{name}</text>')
        for i, (cls, v) in enumerate((("s0", u), ("s1", a))):
            by = y + i * (bar_h + gap_in)
            w = v * scale
            body.append(f'<rect x="{left}" y="{by}" width="{w:.1f}" height="{bar_h}" rx="2" class="{cls}"/>')
            body.append(f'<text x="{left + w + 6:.1f}" y="{by + bar_h - 4}" class="value">{int(v)}</text>')
        red = (u - a) / u * 100
        body.append(f'<text x="{W - 4}" y="{y + group_h / 2 + 4}" text-anchor="end" class="muted">−{red:.1f}% expansions</text>')
        y += group_h + gap_out
    return svg(W, int(H), body, "Search effort: UCS vs A*", theme)


def tradeoff_chart(base, theme: str) -> str:
    metrics = [
        ("Requests served", "done", "{:.0f}"),
        ("Mean response (min)", "t_resp_prom", "{:.2f}"),
        ("Empty km", "km_vacio", "{:.1f}"),
        ("Total cost (€)", "coste", "{:.2f}"),
    ]
    W, panel_w, top, plot_h = 720, 180, 78, 150
    H = top + plot_h + 50
    body = ['<text x="0" y="20" class="title">Dispatch policy trade-off: cheap serves one more request at a higher cost</text>']
    body += legend(0, 48, [("s1", "fast"), ("s2", "cheap")])
    bar_w, gap = 44, 14
    for i, (label, key, fmt) in enumerate(metrics):
        x0 = i * panel_w
        f_v = base[("ucs", "fast")][key]
        c_v = base[("ucs", "cheap")][key]
        vmax = max(f_v, c_v) * 1.15
        base_y = top + plot_h
        body.append(f'<line x1="{x0 + 20}" y1="{base_y}" x2="{x0 + panel_w - 20}" y2="{base_y}" class="grid"/>')
        cx = x0 + panel_w / 2 - bar_w - gap / 2
        for cls, v in (("s1", f_v), ("s2", c_v)):
            h = v / vmax * plot_h
            body.append(f'<rect x="{cx:.1f}" y="{base_y - h:.1f}" width="{bar_w}" height="{h:.1f}" rx="2" class="{cls}"/>')
            body.append(f'<text x="{cx + bar_w / 2:.1f}" y="{base_y - h - 6:.1f}" text-anchor="middle" class="value">{fmt.format(v)}</text>')
            cx += bar_w + gap
        body.append(f'<text x="{x0 + panel_w / 2}" y="{base_y + 22}" text-anchor="middle" class="label">{label}</text>')
    body.append(f'<text x="0" y="{H - 6}" class="muted">Scenario oviedo_refuel_stress, no station failures. UCS and A* give identical results.</text>')
    return svg(W, H, body, "Dispatch policy trade-off: fast vs cheap", theme)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate README charts (SVG, no dependencies)")
    ap.add_argument("--baseline", default="out_suite/baseline/summary.csv")
    ap.add_argument("--fail", default="out_suite/fail/summary.csv")
    ap.add_argument("--out", default="docs/img")
    args = ap.parse_args()

    base = read_summary(Path(args.baseline))
    fail = read_summary(Path(args.fail))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        (out / f"search_effort_{theme}.svg").write_text(search_effort_chart(base, fail, theme), encoding="utf-8")
        (out / f"policy_tradeoff_{theme}.svg").write_text(tradeoff_chart(base, theme), encoding="utf-8")
    print(f"Charts written to {out}/")


if __name__ == "__main__":
    main()
