# H15: completed discovery specification

Question: An apparent disclosure relationship may be explained by contract maturity, moneyness or asynchronous/illiquid daily marks.

Data: Reuse all three H13 maturity buckets. Retain achieved DTE/moneyness, each leg's last-trade age and volume, and a bounded historical quote audit where entitled.

Calculations: Study cross-maturity input relationships, response contrasts and quality sensitivities with same-cohort comparisons. Fixed stale-mark maximums 0/1/3 sessions and maturity buckets are all retained; no favorable filter is selected silently.

The [shared acquisition and analysis specification](../../docs/discovery/options-buffered-plan.md) fixes all consequential discovery choices for this folder: development interval/universe, input clocks and buffers, cohorts, maturity/selection, eight horizons, missing/stale-mark rules, sample thresholds, chronological fitting, uncertainty/search accounting, HPC execution and returned evidence. This folder adopts those choices without additional variants.

Falsification: weak support is inconclusive; concentration, inconsistent adjacent-time results, stale/asynchronous marks, or nonpositive later prediction improvement count against the relevant claim. Descriptive input dependence can remain useful without predicting outcomes. A later economic strategy needs its own complete registration before strategy code or backtesting.

Plan creation precedes new implementation and downloads. Record the real commit hash after committing; leave it absent until then. The read route is in README.md and the shared specification.
