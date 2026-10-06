# Statistical discovery on locally retained history

The nine exploration folders help us decide which relationships deserve a later hypothesis. Each folder owns its `analysis.py`; common data preparation, mathematical helpers, task coordination and transfer tools live once in `discovery/`. These programs calculate associations, conditional responses, prediction errors and uncertainty. They never create positions, simulate orders or calculate portfolio P&L.

Oscar's October 3 instructions establish the operating order: write the code and download historical data on his PC, complete the package there, transfer that package to his HiPerGator storage, and run the actual studies through scheduled jobs. Local execution is limited to download/preparation and small correctness checks. Local multiprocessing remains available if deliberately chosen later.

For the development-selected CFO/CEO follow-up, read [cross-variable options discovery](cross-variable-options.md). It records the actual Massive/Databento access checks, same-filing context acquisition, extended methods, eight session horizons, revised sparse-tree handling and remaining options/timing gaps. Its new snapshot/run remain separate from the completed v3 experiment below.

[The returned follow-up findings](followup-findings.md) explain the completed v4 run, compensation overlap, unstable interaction prediction, matching balance and remaining options acquisition. The combined table retains all 1,522 measured/inconclusive comparisons.

Read [repository rules](../../AGENTS.md), [conventions](../../CONVENTIONS.md), [the exploration index](../../Hypotheses/README.md), and the chosen folder's README first. The [Massive preparation route](../massive/README.md) links the sponsor rules, dataset timing review and source material. Statistical discovery may precede hypothesis registration; a completed and committed economic plan still precedes strategy implementation and backtesting. This package does not implement the final registered S01–S12 evidence contract or authorize exposing any final holdout.

## What runs together

One local controller retrieves disclosure labels and split-adjusted daily prices into a hash-verified cache. A normalized ticker/date panel then supplies every study. Workers consume that frozen panel offline, so eight simultaneous workers never make eight competing API requests. The raw responses, normalized data and run outputs are ignored by Git. Root `.env` stays on the PC.

The task graph has three computation stages. H03–H10 can execute together. H11 then runs independent batches of date-block resampling and uses H08's actual paired validation losses when available. A reducer checks every expected task receipt, writes the combined table and preserves missing, corrupt and failed tasks. The reducer runs even after an analysis failure so that the returned package explains what went wrong.

Slurm concurrency limits apply per stage. The initial job request is one CPU and 4 GB per task, up to four tasks at once, with a two-hour ceiling. This is a bounded starting request rather than a benchmark or reservation of the entire shared allocation. A maintained Python module supplies `uv`; the project creates its own Python 3.11 environment from the shared `uv.lock`. The module's different Python/library versions are not silently substituted. No GPU is requested for these first tabular methods.

The jobs clear inherited `PYTHONHOME` and `PYTHONPATH` before invoking the project environment, including after loading the module that supplies `uv`. The first remote setup exposed why this matters: the module's 3.12 home redirected the locked 3.11 interpreter to the wrong standard library. That failed setup and its cancelled dependents remain retained; the corrected v3 run has its own manifest and Blue directory.

This follows UF's [job-array guidance](https://docs.rc.ufl.edu/scheduler/job_arrays/), which recommends concurrency caps and batching short tasks. [Slurm dependencies](https://slurm.schedmd.com/sbatch.html) express the stage ordering. A browser terminal or SSH connection submits jobs; it does not provide a compute allocation, and analyses never execute directly on a login node.

## First implemented calculations

These are bounded starting implementations of the ideas in the nine READMEs. The documents retain proposals beyond this first version. A task that completes can still produce exclusively inconclusive comparisons.

| Folder | Implemented measurements | Current limits and extensions |
| --- | --- | --- |
| H03 | Pooled Pearson/Spearman associations for each event feature, horizon and additional lag; mean of supported within-date cross-sectional correlations | Equal eligible ticker/date weighting; within-date estimates need variation and at least three rows. Separate issuer time-series meta-analysis remains to add. |
| H04 | Discrete-feature mutual information in nats and biased sample distance correlation; full eligible-panel MI and deterministic bounded distance-correlation subsample | Descriptive statistics only. No HSIC, conditional MI, dependence-preserving null p-value or direction claim. Rare-event subsamples are flagged. |
| H05 | Partial Pearson association and adjusted linear coefficient after five past-only controls and fixed issuer effects | Association, not causality; richer factors and cluster-robust model inference remain to add. Singular candidate effects are inconclusive. |
| H06 | Same-issuer ordinary-day nearest matching using past controls, prior 60 calendar days, no replacement per comparison, distance caliper; mean later-outcome difference | Early 40% scale fit and later-development measurement only; ordinary outcomes must end before the event date. Matching does not establish causal balance; dedicated matched-pair uncertainty remains to add. |
| H07 | A-recent × B ordered-sequence support and linear interaction coefficient alongside main effects/controls | First two configured categories define A/B. Strictly earlier filing date, distinct accession and earlier observed availability session required. Sparse groups/rank deficiency are inconclusive; pre-window A history is unavailable. |
| H08 | Baseline versus three feature additions: disclosure labels, ordered sequences and all event features; Ridge and histogram boosted trees; paired MSE change over three expanding development folds | Fixed model settings, no tuning search. All scaling fits inside training. Actual target-end dates purge training labels before validation. Inference can aggregate only the folds actually supported; probability/quantile targets and richer ablations remain to add. |
| H09 | Event/ordinary mean and empirical 10th/90th quantiles in low/high prior-volatility states; return below −2% frequencies | Volatility cutoff estimated from earliest 40%, measurements in remaining development dates. No smoothed future states, fitted quantile model or causal state claim. Ordinary rows may contain other event categories. |
| H10 | Early-training Pearson/Spearman feature redundancy, constant-feature inventory and standardized PCA variance/loadings | Linear descriptive redundancy; correlated columns need not be predictive substitutes. Clustering, nonlinear redundancy and refit-based conditional replacement remain to add. |
| H11 | Moving date-block bootstrap of pooled H03 correlations at all configured lags, and pooled H08 paired MSE improvements; pointwise intervals, budget-qualified Bonferroni intervals, leave-one-issuer effects | Entire observed cross-section travels with each date block. Inference conditions on observed issuers and assumes adequate block stationarity. This is not a two-way issuer population bootstrap or a null test. No resampling inference yet for H04–H07/H09/H10. |

The bootstrap distribution estimates uncertainty around the observed statistic; it is not an independence-null distribution. No bootstrap tail count is mislabeled as a null p-value. A 95% pointwise interval cannot account for trying many candidates. The reducer considers every planned correlation/paired-loss comparison, including unsupported ones, when sizing the Bonferroni family, and suppresses adjusted intervals unless at least 20 bootstrap values can resolve each extreme tail. The 999-resample first run generally cannot do this. Increasing the budget can improve numerical tail resolution, while leaving stationarity, selection and identification limitations intact. Bonferroni coverage remains approximate because the underlying bootstrap intervals are approximate. No package output labels a discovery result an independently confirmed signal.

In the returned v3 H11 table, `requested_draws` retains the first batch's 250-draw request; `valid_draws` reports the combined valid draws, which are 999 for each supported comparison. The manifest records the full 250/250/250/249 batch budget. Interpret pooled intervals using the combined valid count. All 60 supported H11 comparisons have pointwise intervals, while search-adjusted intervals are explicitly unavailable at this budget; the other 30 comparisons remain inconclusive.

Use the complete `trials.csv` to account for method, feature, horizon, lag, model, fold and failed variants. The H11 family does not purport to correct every possible adaptive search across this project. A future selection-aware confirmation plan must include other explorations and freeze its choices before new evidence.

## Data and the observation clock

`config/discovery-development.json` uses the starter's 100 distinct September 2026 tickers, SPY as an observed benchmark/session grid, two disclosure categories (`cfo_appointment`, `ceo_departure`), horizons 1/5/21 sessions and extra lags 0/1/5 sessions. It confines requests and outcomes to January 1, 2024–December 31, 2025. The starter's 2026 later window and organizer-controlled sealed window are never downloaded or analyzed by this adapter. The five-company `discovery-pilot.json` is an engineering/coverage pilot with 199 resamples; it is not a broad research sample.

The current 100-company list is not historical membership. It creates selection/survivorship concerns and is explicitly recorded in snapshot provenance. A historical issuer/universe source would be needed to remove that concern. Tickers map to CIK when supplied; missing ticker lists remain unmatched and counted. Multiple share classes can overweight one issuer under the current row weighting. Events without stable identity fields are rejected rather than silently invented.

At each observed session close, features use that date and earlier data: prior 5/20-session price return, 20-session return standard deviation, log volume and prior 5-session benchmark return. Targets use prices after that close: split-adjusted price return and RMS future daily price returns. The volatility target is RMS, without subtracting the mean or annualizing; it is explicitly separate from the historical standard-deviation control. Missing intermediate prices invalidate affected forward targets. No future value fills a missing input. Outcome-end dates remain inside the development window and are retained for purging.

The benchmark's dates form an observed data grid rather than an independently validated exchange calendar. New/missing issuer history produces missing observations; it does not shorten a horizon. Even when a close is present, this implementation has not independently audited corporate actions, bar revisions, holiday completeness or survivorship. Price returns exclude dividends and are not total returns or an executable price model.

Massive's [8-K dataset publication](https://www.massive.com/blog/tagging-8-k-disclosures-with-ai-corporate-events-labelled-by-what-actually-happened) describes next-day loading and was published after the historical study window. Labels here are retrospective. A zero feature means no mapped label in the completed queried source, not verified absence of an underlying corporate event; AI classification errors are not independently measured here. Their `available_date` is assumed to be filing date plus one calendar day and aligned to the next observed session close; original public announcement, acceptance time, vendor release time and historical service availability are unverified. Additional session lags are sensitivity calculations, not proof that any assumed clock was historically available. This dataset can help form ideas; it cannot substantiate historical tradability of the tag service.

All nine methods can start with this common stock/event panel. Historical option reference/prices or quotes, macro vintages, FINRA measurements and other data families need separate normalized adapters and timing audits before use. They are not fetched merely because the REST catalog lists them. An options-specific candidate cannot be tested from stock-only outcomes, and sponsor enrichment eligibility remains unresolved.

## Local preparation

Run commands from the repository root in PowerShell. Keep the existing Massive key in ignored root `.env` or the process environment. The standard client sends a Bearer header, permits only `api.massive.com` pagination, refuses redirects, waits at least 12.5 seconds between requests and enforces a per-invocation budget. It never uses a paid x402/wallet route or purchases a subscription. Completed endpoint/date objects are reusable across configurations; partial pagination remains partial and is retried rather than counted as an empty completed dataset.

```powershell
uv sync --locked --python 3.11
uv run --no-sync python -m unittest discover -s tests -v
uv run --no-sync python -m discovery download `
  --config config/discovery-development.json `
  --snapshot data/cache/discovery/snapshots/development-20261003 `
  --max-requests 120
```

The download produces a snapshot only after every requested object and normalization succeeds. A denial, missing price series, exhausted budget or schema problem retains the attempt report under `data/cache/discovery/downloads/<config-id>/requests/`; it does not launch analyses. Resume that command to reuse verified completed objects. An already completed snapshot is immutable: use a new name for a changed dataset/configuration.

Windows may restrict execution of newly installed compiled libraries under application-control policies. Downloads and small timing/identity tests do not import model libraries. HiPerGator's Linux environment loads the actual estimators before computation. Do not weaken PC security settings to force a local analysis; actual studies belong on HiPerGator under the requested workflow.

After the download and local checks succeed, freeze the graph and generate jobs:

```powershell
uv run --no-sync python -m discovery plan `
  --snapshot data/cache/discovery/snapshots/development-20261003 `
  --run data/cache/discovery/runs/development-20261003
uv run --no-sync python -m discovery jobs `
  --run data/cache/discovery/runs/development-20261003 `
  --remote-root /blue/ai-workshop/<UF_USERNAME>/quanthacks/discovery/development-20261003 `
  --concurrency 4 --memory-gb 4 --hours 2
uv run --no-sync python -m discovery bundle `
  --run data/cache/discovery/runs/development-20261003 `
  --output transfer-bundles/development-20261003.tar.gz
```

The manifest hashes the snapshot, settings, every study's code, shared code, manifest and lockfile. A change requires a new plan/run rather than mixing old and new outputs. The allowlisted bundle contains code, tests, the normalized historical panel and generated scheduler scripts. It excludes root `.env`, raw API response caches, Git history, Windows `.venv` and precomputed analysis results. Its SHA-256 receipt allows the remote upload to be checked before extraction. Raw history remains retained locally; compute nodes need only the normalized frozen panel.

## Transfer, scheduled execution and return

Authenticate normally to `<UF_USERNAME>@hpg.rc.ufl.edu`, using a trusted host key and your existing login/MFA. [UF's transfer guide](https://docs.rc.ufl.edu/data_transfer/overview/) supports SSH/SCP for smaller packages; a large data expansion may suit Globus. The project's PowerShell helper performs upload, submission, status and return as explicit operations:

```powershell
$run = 'data/cache/discovery/runs/development-20261003'
pwsh -File tools/HiPerGatorDiscovery.ps1 -Action Upload `
  -Run $run -Bundle transfer-bundles/development-20261003.tar.gz
pwsh -File tools/HiPerGatorDiscovery.ps1 -Action Submit -Run $run
pwsh -File tools/HiPerGatorDiscovery.ps1 -Action Status -Run $run
pwsh -File tools/HiPerGatorDiscovery.ps1 -Action Fetch -Run $run
```

Use PowerShell 7 (`pwsh`) for this helper: it uses `System.IO.Path.GetRelativePath`. The helper refuses an existing remote destination for upload and an existing submission receipt for submission, so repeated commands do not silently create duplicate attempts. A partly transferred destination remains present on failure; inspect and recover it deliberately rather than deleting it automatically. If SSH isn't configured, the same local TAR can be uploaded through an authenticated Open OnDemand Files page, extracted in the chosen Blue directory, and submitted with `bash data/cache/discovery/runs/development-20261003/hpg/submit.sh` in its terminal. The statistical programs still run only through Slurm.

`setup.sbatch` synchronizes the Python 3.11 locked runtime and runs small correctness checks on a compute node. `core.sbatch` runs H03–H10, `uncertainty.sbatch` batches H11, and `report.sbatch` validates receipts, aggregates measurements and writes `returned-results.zip`. `submission-ids.txt` contains actual job IDs only after submission. `squeue` describes queued/running jobs; `sacct -j <actual-job-id> --format=JobID,State,ExitCode,Elapsed,MaxRSS` verifies terminal outcomes. Group capacity and previous successful jobs do not guarantee this run's resource availability.

Fetch imports only files whose bytes match the return receipt, rejects path traversal/duplicates and refuses differing local attempts. It then appends the local exploration ledger and per-folder research logs once. No worker races to edit `EXPERIMENTS.csv`, and no remote program fabricates a registration/code commit. Expected outputs are `REPORT.md`, `summary.csv`, all attempted `trials.csv`, `report.json`, `manifest.json`, and `studies/H03` through `studies/H11` with measurements and task receipts. The measurements/logs distinguish synthetic engineering checks, real development statistics and unsupported/failed comparisons.

Run-specific measurements are canonically held under the local run directory; each folder's log links its own study table and the shared report. Only deliberately reviewed, permitted derived evidence should be committed later. Licensed rows and local run caches are not publication artifacts.

## Resuming and using a study independently

`python -m discovery task --run <run> --task-id <id>` reruns a failed/missing task and skips an already successful, hash-valid receipt. Keep prior failed receipts before deliberately rerunning. Submit a small retry array with the same task mapping when needed, then repeat the uncertainty/aggregation stage if its inputs changed. A changed method/config/data identity always needs a new run rather than such a retry.

Each study is also callable from its own folder, for example `python 'Hypotheses/H08 - Incremental Prediction/analysis.py' --run <run>`. H11 requires core attempt receipts first. Actual execution belongs in a scheduled allocation. For deliberately requested local computation, `python -m discovery run --run <run> --workers 4` uses a spawn-safe process pool with one numerical thread per worker and the same task graph. Repeating with a different worker count produces the same task seeds/configuration; runtime/timestamps may differ.

To inspect the aggregate, compare effect size, event/issuer/date support, matched coverage, held-development loss improvements, delay stability, concentration and qualified uncertainty. A top value on one column is insufficient to name the “best” hypothesis. A new mechanism and frozen confirmation plan should emerge from the complete evidence, including failures, rather than an automatic winner label.

## H12–H17: options and buffered connections

Read the committed [options/buffered plan](options-buffered-plan.md), [verified stage findings](options-buffered-findings.md), and the six new folder specifications in [the hypothesis index](../../Hypotheses/README.md#options-and-buffered-connections-h12h17). The plan commits are 197e8a050b15f2ca09d68b5b835b4393cfa6708f and the historical-price clarification 590ee72ca8e1475d80ade565c27a00ce2c7bc00f. These precede this stage's new acquisition and code. Earlier implementations are historical discovery rather than retroactively registered plans.

The root environment now includes Databento 0.87.0 and exchange-calendars 4.13.2. The client imported locally. No paid Databento time series was acquired; Massive provides the main study. `discovery.options_data` downloads resumable historical chains, unadjusted stock/option bars and primary-maturity pre-close quotes onto the PC. It preserves 113 event/prior ordinary anchors, three maturity targets, source identities and missing chain/mark outcomes. Quotes use the verified exchange session close, including early closes. Approximate parity uses a flat four-percent rate without dividends; premium-sum proxies are not historical vendor IV.

The [transport amendment](options-transport-plan.md), committed as a4a9684f778ae8dc67bda5b4f64d82d026e21b99 before its implementation, supersedes the blanket five-per-minute acquisition setting for this stage. Resume the same `download` command with `--minimum-interval 0.5` to use separate option/stock/reference clocks and bounded HTTP-429 slowdown. All completed request objects are reused by verified hash; every attempted retry still counts toward 2,000. This is a controlled pace observation, not proof of the account's full subscriptions. Separate S3 credentials are not configured locally. The completed implementation checkpoint is 37c645c930f53012fe4db7b297f5a39131c017cc; the transport fixtures bring local correctness coverage to 45 tests.

The [integrated final findings](options-final-findings.md) record completed acquisition, the six successful HiPerGator studies, verified local returns and five possible hypotheses to explore. The full 10,398-cell family is retained in the ledger; repeating the dense stage in the options package is integration verification rather than independent evidence.

`discovery.connections prepare` attaches six covered disclosure groups and strictly prior 5/21/63-session occurrences to the existing stock panel. Offsets 0/1/3/5 use the true exchange-session calendar and preserve gaps. The scheduled folder implementations own Pearson/Spearman input maps, issuer-controlled buffered associations, prior-context interactions, option-implied-uncertainty connections, paired option repricing, maturity/mark-quality audits, and fixed purged chronological Ridge comparisons. H17's predictions currently concern stock outcomes; option pricing is evaluated through H13–H15 descriptive/paired diagnostics rather than a separate option-prediction model.

The dense phase runs H12/H16/H17 while local option acquisition continues. The later option-enabled phase completes the fixed options matrix. Freeze a fresh manifest with `python -m discovery.connections freeze --snapshot <dense-snapshot> --run <new-run> [--options <prepared-option-sources>]`; create jobs and a bundle with `python -m discovery.connection_jobs jobs` and `bundle`. Scheduled setup precedes a capped four-worker folder array; report runs after any core outcome and exports even failed receipts. Use the generated `hpg/submit.sh` in the new Blue destination. `connection_jobs import` verifies return identity, members, hashes and local conflicts before writing. It does not automatically record the experiment ledger; do that after verified return.

The first dense attempt retained three MergeError failures caused by multiple buffered source sessions shifting past the development end. The corrected join drops those out-of-window right-side keys while preserving missing left-side observations. A synthetic fixture covers that boundary, and a fresh v2 identity preserves the correction rather than overwriting v1. All five v2 allocations completed; 11 returned files verified, with 4,632 comparisons now recorded. The options acquisition/run remains pending. A later quote-audit correction preserves observed quote evidence when a daily trade mark is unavailable; its fixture is included among 39 passing local checks, and the new option-enabled manifest must freeze that code.

Scientific suite calculations use HiPerGator allocations. PC work is limited to downloads, normalization, correctness fixtures, packaging and review arithmetic on returned evidence. All tables remain exploratory, with pointwise uncertainty, dependence/support limits and every attempted variant visible. No protected-window outcomes, orders, positions or P&L are used.
