param([switch]$KeepRuns)

$ErrorActionPreference = "Stop"

Remove-Item -Recurse -Force experiments\report\fail_seeds -ErrorAction SilentlyContinue | Out-Null

$keep = ""
if ($KeepRuns) { $keep = "--keep-runs" }

1..10 | ForEach-Object {
  $s = $_
  python tools/run_suite.py --data data/oviedo_refuel_stress --out ("experiments/report/fail_seeds/seed_"+$s) --quiet `
    --seed $s --fail-p 0.2 --fail-min 10 --fail-max 10 `
    --strategies ucs,astar --policies fast,cheap `
    $keep
}

Write-Host "`nFail seeds done."