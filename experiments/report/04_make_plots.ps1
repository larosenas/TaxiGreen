$ErrorActionPreference = "Stop"

if (!(Test-Path experiments\report\baseline\summary.csv)) { throw "Missing baseline summary. Run 01_run_baseline.ps1 first." }
if (!(Test-Path experiments\report\fail\summary.csv)) { throw "Missing fail summary. Run 02_run_fail.ps1 first." }

# Clean previous plots to avoid accumulation
Remove-Item -Force -ErrorAction SilentlyContinue experiments\report\plots\*.png

python tools\make_plots.py

Write-Host "`nPlots saved in: experiments\report\plots"
Get-ChildItem experiments\report\plots