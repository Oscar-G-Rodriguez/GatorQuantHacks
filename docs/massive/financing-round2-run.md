# Financing round 2: preparation, scheduled runs and papers

This guide describes the implemented shared interfaces for H23, H24 and H25. The [registered experiment plan](financing-round2-plan.md) and [configuration](../../config/financing-round2.json) own all scientific settings. Registration `b4159e2917248d588072ef5d9ae55bd88c3f8063` preceded the new implementation. This guide records an evidence checkpoint; it is not a passing backtest or submission receipt.

## Verified preparation checkpoint: October 4, 2026

The full preparation job `44691291` and return job `44691292` were observed as `COMPLETED`, exit `0:0`. Their returned archive was imported on the PC with whole-archive and member verification: **11 members**, SHA-256 `42c841e6e57766724dfb7e4ff439e1b48362cb795358f35bc8dd23544bf8bf13`. The run is `data/cache/disclosure-atlas/financing-round2-prepare-v1`, manifest `b1c2011f7683b497615d3bdc7509cd30d347a7fa99200117a7d6959551b6b6e6`, code commit `79753b64af2e313d0791f2c635be51c612b619ec`.

Read its private `prepared/summary.json`, `prepared/coverage.csv`, `prepared/exclusions.csv`, `receipts/prepare.json`, `return.json`, `import-receipt.json` and `scheduler-observation.json` together. The preparation retained **3,509 source filings** and built **37,250 acquisition anchors**. An anchor requests one study/variant/shape/comparison observation; it is not an executed trade, independent event or matched usable pair.

| Standard-label cohort | 2022 | 2023 | 2024 | 2025 | Total filings | Wording exclusions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H23: debt issuance | 137 | 115 | 115 | 159 | 526 | 0 |
| H24: credit facility | 45 | 48 | 26 | 35 | 154 | 0 |
| H25: same-filing debt and underwriting | 56 | 61 | 48 | 81 | 246 | 0 |

The cohorts overlap. H25's 246 is its complete 2022-2025 raw conjunction cohort; the earlier 61/48/81 figures described 2023-2025 activations only. Neither count establishes complete option coverage, valid execution prices or profitability. Pilot preparation `44691937` and its dependent return `44691938` were pending at this checkpoint. No round-2 option acquisition or measured trading output had been verified here.

## Where each operation belongs

On the PC, author code, run synthetic correctness checks, acquire entitled API objects, reuse matching hash-verified cache entries, create immutable packages and import returns. Keep credentials in the existing local environment; packages and Git contain no key or `.env`.

HiPerGator login-node work is limited to upload, archive/member verification, installation, environment checks and scheduler control. Scheduled compute-node jobs construct real-data cohorts, match ordinary periods, run funded-share simulations and perform statistical calculations. The execution interfaces refuse real calculations without `SLURM_JOB_ID`; setting that variable manually on a PC or login node does not authorize an analysis run.

The current shared modules are [packaging/scheduler control](../../discovery/financing_pipeline.py), [scheduled preparation](../../discovery/financing_research.py), [local acquisition](../../discovery/financing_acquire.py), [funded strategy calculations](../../discovery/financing_strategy.py) and [statistical analysis](../../discovery/financing_analysis.py). Folder-level wrappers and complete later-stage orchestration must be checked against the actual implementation before use. A recognized command name alone does not prove that its stage has completed or passed.

## PC preparation and immutable transfer

Run commands from the repository root using its existing Python environment. Examples below name new run directories: do not overwrite or refreeze the verified preparation run. Change the run suffix for a new attempt and preserve failed attempts.

```powershell
python -B -m discovery.financing_pipeline freeze --phase prepare --scope pilot --run data/cache/disclosure-atlas/financing-round2-pilot-prepare-v1
python -B -m discovery.financing_pipeline bundle --run data/cache/disclosure-atlas/financing-round2-pilot-prepare-v1 --output data/cache/transfer-bundles/financing-round2-pilot-prepare-v1.tar.gz
```

Use `--scope full` with a distinct directory for a full preparation manifest. Freeze checks the actual registration in Git, records code/settings/input/job hashes and refuses an existing frozen directory. The bundle step verifies those hashes and writes a companion installer plus `transfer.json`. Read the **actual printed installer path** rather than guessing its name.

Upload the archive and its generated installer together through the authenticated HiPerGator session. Run the installer on Blue; it checks the whole archive, exact member set, safe paths and every member hash before installation. It rejects conflicting bytes at the immutable destination. The registered remote base is `/blue/ai-workshop/<UF_USERNAME>/quanthacks/discovery`. Generated jobs use the already provisioned `atlas-v3/.venv/bin/python`; verify its availability without moving computation to a login node.

## Scheduled preparation and return

From the installed package root on Blue, submit the generated preparation script. Use the run-relative path contained in its manifest; files are nested beneath that package root.

```bash
sbatch data/cache/disclosure-atlas/financing-round2-pilot-prepare-v1/hpg/prepare.sbatch
sbatch --dependency=afterok:<PREPARATION_JOB_ID> data/cache/disclosure-atlas/financing-round2-pilot-prepare-v1/hpg/return.sbatch
sacct -j <PREPARATION_JOB_ID>,<RETURN_JOB_ID> --format=JobID,State,ExitCode,Elapsed,MaxRSS
```

Replace the bracketed tokens with actual scheduler IDs. Preserve the observation in the run's `scheduler-observation.json` as `observed_at` and `jobs` containing `job_id`, `state`, `exit_code`, `elapsed` and `max_rss`. An archive appearing is not enough: inspect terminal scheduler states, stage receipts and hashes. Failed or cancelled attempts remain in the evidence record.

Export writes `returned-<run-name>.zip` and its `.sha256` alongside the installed repository root. Download those unchanged bytes to the PC, then import using the exact exported archive hash:

```powershell
python -B -m discovery.financing_pipeline import --run data/cache/disclosure-atlas/financing-round2-pilot-prepare-v1 --archive <DOWNLOADED_ZIP> --sha256 <EXPORTED_SHA256>
```

Import checks the whole archive, manifest identity, exact member set, every member hash and conflicts with existing outputs. It stores the retained archive under `returned/` and writes `import-receipt.json`. Keep the scheduler observation alongside these receipts. Scientific interpretation waits for the evidence appropriate to that stage.

## PC option acquisition and the separate backtest freeze

Use a **verified returned** preparation directory as the acquisition input. A pilot uses its coverage-only pilot anchors: first four events per study/year under deterministic issuer/accession ordering and the four predeclared study/variant tasks. A pilot must never inherit a full-run interpretation.

```powershell
python -B -m discovery.financing_acquire --prepared data/cache/disclosure-atlas/financing-round2-pilot-prepare-v1/prepared --output data/cache/disclosure-atlas/financing-round2-pilot-v1/acquisition
```

The downloader resumes against the same prepared/settings hashes, verifies reused object bytes, retains attempts/failures and writes `acquisition/source.json`. It uses the registered eight workers, aggregate pacing and bounded request budget. Reaching the budget or leaving failed requests gives partial status. A terminal `missing_nominal_decision_bar` or `no_standard_contract_within_rules` is recorded coverage information, not a successful eligible trade. The `complete` flag means required acquisition requests have terminal states; subsequent scientific eligibility remains separate.

`--request-cap` may impose a smaller phase budget, never increase the registered cap. `--skip-quotes` is an explicit limited-evidence acquisition mode; it cannot support an executable-price claim. Required complete-source and anchor/settings checks must pass before freezing an actual backtest package:

```powershell
python -B -m discovery.financing_pipeline freeze --phase backtest --scope pilot --prepared data/cache/disclosure-atlas/financing-round2-pilot-prepare-v1 --run data/cache/disclosure-atlas/financing-round2-pilot-v1
python -B -m discovery.financing_pipeline bundle --run data/cache/disclosure-atlas/financing-round2-pilot-v1 --output data/cache/transfer-bundles/financing-round2-pilot-v1.tar.gz
```

For the full package, use the full returned preparation, a new full acquisition directory and `--scope full`. Freeze requires complete acquisition with the exact anchor/configuration identities. Once frozen, changing code, logs included in the manifest, settings or data requires a new manifest/package rather than editing the transferred run.

## Pilot, full tasks and remaining scientific stages

The generated backtest scripts are `pilot.sbatch`, `run.sbatch`, `analyze.sbatch`, `calibration.sbatch` and `return.sbatch`. The pilot array covers the four declared tasks; the full task mapping is three studies by eleven variants. A single task measures both option shapes and retains all registered horizons. Task outputs include coverage, unit trades, signal diagnostics, NAV and a measured wall-time/RSS record under `results/tasks/<task>/`.

Submit `pilot.sbatch` first. Measure wall time, memory, valid coverage and ledger completeness. These outputs assess resource needs and implementation; they do not select favorable studies or replace full results. Initial scripts request one CPU, eight GB and two hours with single-thread libraries. Pilot concurrency is four; the generated full array initially caps concurrency at sixteen. Scale only after fresh account/QoS checks and measured evidence, within the registered maximum of 64. Scheduler waiting and data acquisition time are separate from compute time.

Completed task receipts are hash-checked checkpoints. Retry only missing or failed tasks under the same verified immutable package, preserving attempts. The generated arrays do not themselves identify a retry subset: prepare a reviewed list of missing task IDs before resubmission.

Analysis must wait for required task receipts and include the registered common-observation checks, family ledger, both block lengths and calibration status. Calibration is a separate scheduled stage. The focused 199 timing placebos require shifted bundles, repeated matching/selection, the corresponding PC acquisition, separately frozen scheduled calculations and comparison evidence; `placebo-prepare` alone only prepares a replica. At this checkpoint there was no verified complete placebo orchestration or result. Do not call the atlas's unfinished 499 broader searches complete from these focused tests.

Export validates its required stage receipts and member hashes. It does not certify scientific adequacy or automatically prove every separately required calibration/placebo stage passed. Complete scheduler records, scientific receipts, support, uncertainty and limitations must reconcile before a claim. `--phase final-oos` execution is intentionally refused because no attested unseen confirmation exists. All 2022-2025 remains development and the previously exposed 2026 interval remains exposed.

## Overleaf papers and verified result updates

The user selected Overleaf for compilation/export. The source generator performs presentation only; it does not run a local PDF compiler or calculate market outcomes.

```powershell
python -B scripts/build_financing_paper_sources.py
python -B scripts/build_financing_paper_sources.py --run <VERIFIED_RETURNED_RUN>
```

Without `--run`, it produces an honest registered pending draft. With `--run`, it requires matching manifest/return/import identities, registration/code identity, archive-import receipt, agreeing member maps and observed successful scheduler states; displayed source tables and NAV members are checked against returned hashes. Missing studies or quantities remain explicit. The current expected per-study files are `results/H23/summary.json`, `performance.csv`, `baseline_comparison.csv`, `robustness.csv`, with the analogous H24/H25 paths. Raw task NAV is embedded only when the verified schema supplies an eligible primary series. A preparation-only return has no strategy result to display.

Each folder owns `Paper.tex` and `Paper.md`; the ignored import ZIPs are under `data/cache/transfer-bundles/financing-papers/`, each containing only `main.tex` with identical bytes. Upload a ZIP as a separate Overleaf project. For an existing project, replace its **main.tex** with the current standalone source; merely adding `Paper.tex` can leave an old root file compiling. Preserve the unrelated existing submission outline. The actual projects are H23 (private Overleaf copy), H24 (private Overleaf copy) and H25 (private Overleaf copy).

Compile in Overleaf, inspect the error/log panel, export the actual PDF and retain its project URL/source hash/compile status. Then render **every exported page** for visual QA. Check no clipping or table overflow, readable curves, at least 11pt body/tables/captions, Letter size, one-inch margins and at most five main pages including figures/tables. References follow; six total pages can be valid if page six begins references. Update [the paper verification receipt](financing-round2-paper-verification.json) with actual exported PDF hashes, page counts and inspection evidence. Source generation or an error-free compile alone does not complete visual QA or establish organizer submission compliance.

The first actual Overleaf exports were six pages each, with five main pages and references on page six. All 18 individual pages and three contact sheets were inspected: no clipping, overlap, broken tables or footer issues were found. Their body/table/footer text measured **10.9091 PDF points**, so they failed the literal 11-point minimum despite the nominal `article[11pt]` option. These first-export bytes, source/PDF hashes, compile observations and failed QA remain in the receipt history and `output/pdf/qa/first-overleaf-export/`. They are superseded drafts. The corrected sources explicitly define normal and small body/footnote text as `11bp`, with 13.6bp leading. Figure ticks, axis labels, legends and captions retain the same body minimum; conventional mathematical superscripts/subscripts are assessed separately. The corrected source still requires a fresh Overleaf compile/export and all-page QA, which may follow the measured pilot update. No PDF was compiled locally.

## Evidence acceptance

Keep registration, prior exposure, exact attempts, manifests, acquisition failures, exclusions, scientific checks, scheduler observations, return hashes and paper exports linked. A raw event count, positive stock return or visually appealing curve does not establish a net disclosure-timing benefit. Report unsupported, rejected and inconclusive cells as recorded. Earlier H18-H22 outcomes remain intact; no issuer such as Pepsi is selected from its observed profit. Later advancement requires an interpretable mechanism, all required development checks and genuinely unseen evidence.
