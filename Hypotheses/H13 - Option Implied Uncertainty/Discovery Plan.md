# H13: completed discovery specification

Question: Leadership changes may be associated with a different amount of subsequent movement relative to the uncertainty already contained in option premiums.

Data: Historical paired call/put contracts at a shared strike and expiry, selected using information at the pre-filing session. Acquire the 30-, 60- and 120-calendar-day target buckets for every mapped CFO/CEO lead filing and its prior ordinary anchor.

Calculations: Describe call/put premiums, premium sum relative to parity-derived spot and sqrt-maturity-normalized uncertainty; compare later absolute stock movement and option-premium changes across all eight horizons. These are pricing diagnostics, not implied volatility estimates or option-strategy P&L.

The [shared acquisition and analysis specification](../../docs/discovery/options-buffered-plan.md) fixes all consequential discovery choices for this folder: development interval/universe, input clocks and buffers, cohorts, maturity/selection, eight horizons, missing/stale-mark rules, sample thresholds, chronological fitting, uncertainty/search accounting, HPC execution and returned evidence. This folder adopts those choices without additional variants.

Falsification: weak support is inconclusive; concentration, inconsistent adjacent-time results, stale/asynchronous marks, or nonpositive later prediction improvement count against the relevant claim. Descriptive input dependence can remain useful without predicting outcomes. A later economic strategy needs its own complete registration before strategy code or backtesting.

Plan creation precedes new implementation and downloads. Record the real commit hash after committing; leave it absent until then. The read route is in README.md and the shared specification.
