TaxiGreen – Report reproduction scripts (PowerShell)
Run from the repository root.

Quick (report mode, minimal files)
1) Baseline + Fail summaries:
   powershell -ExecutionPolicy Bypass -File experiments\report\01_run_baseline.ps1
   powershell -ExecutionPolicy Bypass -File experiments\report\02_run_fail.ps1

2) Generate report plots (PNG):
   powershell -ExecutionPolicy Bypass -File experiments\report\04_make_plots.ps1

Or run everything:
   powershell -ExecutionPolicy Bypass -File experiments\report\00_run_all.ps1


Outputs (report mode)
- experiments\report\baseline\summary.csv
- experiments\report\fail\summary.csv
- experiments\report\plots\*.png

Notes
- By default, the suite keeps only the aggregated summary and the final plots.
  Per-run folders under experiments\report\<scenario>\runs\<tag>\ are NOT kept to avoid generating hundreds of files.
- Optional detailed mode (if enabled) keeps runs/<tag>/ folders containing metrics.json and trips.csv for auditing/debugging.


Optional robustness batch (multiple seeds)
   powershell -ExecutionPolicy Bypass -File experiments\report\03_run_fail_seeds.ps1


Plot dependencies
- Required for make_plots.py: pandas + matplotlib