# Verified pilot evidence

These are unchanged copies of scheduled HiPerGator outputs. The source paths and SHA-256 values in evidence_manifest.json identify every copied member. This directory contains no raw vendor object or credentials.

The result is INCONCLUSIVE. Read summary.md and validation_checks.json before interpreting performance.csv. The synthetic calibration failed, paired samples are sparse, and fresh confirmation is unavailable. This delivered pilot covers four scoped tasks; it does not finish the33-task full study.

Recreate this evidence copy on the PC from the retained verified run:

```powershell
.venv/Scripts/python.exe -B scripts/package_financing_pilot_evidence.py --run data/cache/disclosure-atlas/financing-round2-pilot-acquisition-v1
```

Numerical replay requires the frozen source package and a scheduled HiPerGator allocation. Run discovery.financing_pipeline exec with --phase development, --stage run and the registered --task; then calibration, analyze and export stages. The retained source package is private. The existing receipts make completed tasks idempotent; a new scientific attempt needs a new frozen run.
