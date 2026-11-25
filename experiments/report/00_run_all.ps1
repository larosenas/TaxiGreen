$ErrorActionPreference = "Stop"

# Toggle this to run the multi-seed robustness batch
$RUN_SEEDS = $false

# Toggle this to keep per-run folders (runs/<tag>/...) for auditing
$DETAILED = $false

Write-Host "== TaxiGreen report pipeline =="

# Ensure folders exist
New-Item -ItemType Directory -Force experiments\report | Out-Null
New-Item -ItemType Directory -Force experiments\report\plots | Out-Null

$keepArg = @()
if ($DETAILED) { $keepArg = @("-KeepRuns") }

Write-Host "`n[1/4] Running baseline..."
powershell -ExecutionPolicy Bypass -File experiments\report\01_run_baseline.ps1 @keepArg

Write-Host "`n[2/4] Running failure scenario..."
powershell -ExecutionPolicy Bypass -File experiments\report\02_run_fail.ps1 @keepArg

if ($RUN_SEEDS) {
  Write-Host "`n[3/4] Running multi-seed robustness batch..."
  powershell -ExecutionPolicy Bypass -File experiments\report\03_run_fail_seeds.ps1 @keepArg
} else {
  Write-Host "`n[3/4] Skipping multi-seed batch (set `$RUN_SEEDS = `$true to enable)."
}

Write-Host "`n[4/4] Generating plots..."
powershell -ExecutionPolicy Bypass -File experiments\report\04_make_plots.ps1

Write-Host "`nAll done."
Write-Host "Baseline summary: experiments\report\baseline\summary.csv"
Write-Host "Fail summary:     experiments\report\fail\summary.csv"
Write-Host "Plots folder:     experiments\report\plots\"
Write-Host "Detailed mode:    $DETAILED"