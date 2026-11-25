param([switch]$KeepRuns)

$ErrorActionPreference = "Stop"

Remove-Item -Recurse -Force experiments\report\fail -ErrorAction SilentlyContinue | Out-Null

$keep = ""
if ($KeepRuns) { $keep = "--keep-runs" }

python tools/run_suite.py --data data/oviedo_refuel_stress --out experiments/report/fail --quiet `
  --seed 1 --fail-p 0.5 --fail-min 10 --fail-max 10 `
  --strategies ucs,astar --policies fast,cheap,balance `
  $keep

Write-Host "`nFailure scenario done. Summary:"
Get-Content experiments\report\fail\summary.csv