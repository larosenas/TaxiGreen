param([switch]$KeepRuns)

$ErrorActionPreference = "Stop"

Remove-Item -Recurse -Force experiments\report\baseline -ErrorAction SilentlyContinue | Out-Null

$keep = ""
if ($KeepRuns) { $keep = "--keep-runs" }

python tools/run_suite.py --data data/oviedo_refuel_stress --out experiments/report/baseline --quiet `
  --seed 0 --fail-p 0 `
  --strategies ucs,astar --policies fast,cheap,balance `
  $keep

Write-Host "`nBaseline done. Summary:"
Get-Content experiments\report\baseline\summary.csv