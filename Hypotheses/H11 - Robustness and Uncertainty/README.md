# H11 — Robustness and uncertainty

**Stage:** exploratory implementation, unregistered; first HiPerGator development run completed. See the [research log and returned evidence](Research%20Log.md). Created October 3, 2026, from the nine-idea discussion in chat `private project chat`. This folder now owns `analysis.py`; the original proposals below remain broader than the first implemented methods.

The question is how much dependence, selection, information delay or concentration in a few observations could explain a discovery finding. This is a shared evidence study supporting the other folders. Its purpose is to describe what the data can establish, what contradicts a candidate and what remains uncertain; it is not an additional economic mechanism.

## Unit of evidence and search history

Identify the actual unit of measurement and the dependence structure: overlapping outcomes, repeated events within issuers, common date shocks, repeated macro releases or shared option contracts. Row counts alone do not establish independent sample size. Sparse groups and genuine extreme outcomes must remain visible.

Define the estimated quantity before choosing a procedure: an event/control difference, regression coefficient, dependence statistic or paired prediction-loss improvement. Confidence intervals, null tests and stability summaries answer different questions. An uncertainty procedure must fit the estimand and sample; generic independent-row bootstrapping is not the default.

## Proposed calculations

1. Inventory rows, distinct issuers/events/dates, overlap, concentration and all exclusions. Where useful, simulate precision or a minimum detectable effect under stated assumptions; do not turn an assumed power model into an observed sample fact.
2. Choose time-block, issuer/date-cluster or another justified uncertainty procedure. Record its assumptions, grouping/block choices, interval convention and sensitivity. Appropriate regression covariance may be preferable for some questions.
3. Construct null or placebo tests that remove the claimed relationship while preserving relevant dependence and eligibility. Simple row shuffling can invalidate a time-series test. A block bootstrap for an interval is not automatically a valid null generator.
4. Define the complete relevant search family across folders, feature definitions, horizons, controls, models and failed variants. Apply a correction or selection assessment suitable for dependent tests and valid underlying p-values. Address adaptive selection explicitly, including repeating selection inside a suitable resampling design when warranted.
5. Check nearby settings, chronological periods, issuer/date exclusions, availability delays and defensible alternative measurement conventions. Report genuine extremes with and without a documented sensitivity view; do not delete losses or inconvenient events to manufacture stability.
6. Summarize supporting evidence, contradictions and unresolved coverage. Keep discovery selection distinct from any later registered confirmation, and leave final/organizer holdouts untouched during this stage.

## Expected evidence and interpretation

The future output would include intervals and null comparisons, multiple-search treatment, concentration/leave-group-out tables, sensitivity curves, independent-support counts, a search manifest and a plain-language reliability assessment. No resample, p-value or robustness result has been produced here.

Repeated improvement under defensible checks can make a candidate worth developing. Failed availability checks, search-adjusted evidence that is weak, unstable signs or heavy concentration can explain why an attractive estimate is unreliable. Wide uncertainty can justify an inconclusive discovery result without proving that no relationship exists. This stage cannot assign the repository's final supported-signal verdict.

## HiPerGator and open choices

This folder is a strong compute candidate: substantial resampling/null batches, repeated fits and group exclusions can be distributed over a verified dataset. Choose the number of repetitions for numerical precision and the search's required resolution; no universal repetition count guarantees adequate inference. Batch short tasks and use recorded randomness/partitions where applicable. Preserve failures and permitted derived outputs.

The candidate/estimand, dependency design, resampling/null assumptions, block/group choices, search family, adaptive-selection treatment, repetition budget and practical criterion remain open. Follow the [shared discovery boundaries](../README.md#shared-discovery-boundaries).

## Reading route

- [Time-series bootstrap methods](https://arch.readthedocs.io/en/stable/bootstrap/timeseries-bootstraps.html) and [dependent-series kernel testing](https://proceedings.mlr.press/v32/chwialkowski14.html).
- [Multiple-testing correction](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.fdrcorrection.html) and [signal-testing guide](../../docs/SIGNAL_TESTING_GUIDE.md).
- [UF job arrays](https://docs.rc.ufl.edu/scheduler/job_arrays/) and [computation guidance](https://docs.rc.ufl.edu/quickstart/computation/).
- [Signal-reading requirements](../../docs/signal-reading/README.md), especially S01–S02, S08–S10 and S12; all actual implementation/execution remains pending.

## Current implementation and execution

[analysis.py](analysis.py) implements this folder's first calculations. [The shared run guide](../../docs/discovery/README.md) identifies exactly what is implemented, open extensions, data/timing assumptions and the three-stage task graph. Author code and download history on the PC, then transfer the completed package to Blue and execute actual studies through scheduled HiPerGator jobs. [Research Log.md](Research%20Log.md) preserves preparation and subsequent runs; the shared experiment ledger records attempted comparisons after results are returned.

From the project root in a scheduled allocation, run `python "Hypotheses/H11 - Robustness and Uncertainty/analysis.py" --run <frozen-run-directory>`. The coordinated runner is the preferred way to run all nine; H11 requires the core attempt receipts. No strategy registration, backtest or confirmed signal is asserted.


[Cross-variable follow-up](../../docs/discovery/cross-variable-options.md) specifies the October 3 extensions, actual preparation/access evidence and remaining inference/options limits. Read it before using the new configuration; the original v3 run retains its frozen code and outputs.
