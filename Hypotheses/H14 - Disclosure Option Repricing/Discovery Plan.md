# H14: completed discovery specification

Question: The type of leadership disclosure and its accompanying compensation context may distinguish the timing and persistence of option repricing.

Data: Reuse the H13 fixed contract identities. Observe pre-filing diagnostics and assumed post-label sessions at buffers 1/3/5, with outcomes ending strictly within 2024–2025 and before expiry.

Calculations: Compare same-contract call, put and premium-sum fractional changes at 1/2/3/5/10/21/42/63 sessions. Retain missing outcomes, expiration limits and leg ages. Compare event/ordinary cohorts, both raw and with issuer/past-state controls.

The [shared acquisition and analysis specification](../../docs/discovery/options-buffered-plan.md) fixes all consequential discovery choices for this folder: development interval/universe, input clocks and buffers, cohorts, maturity/selection, eight horizons, missing/stale-mark rules, sample thresholds, chronological fitting, uncertainty/search accounting, HPC execution and returned evidence. This folder adopts those choices without additional variants.

Falsification: weak support is inconclusive; concentration, inconsistent adjacent-time results, stale/asynchronous marks, or nonpositive later prediction improvement count against the relevant claim. Descriptive input dependence can remain useful without predicting outcomes. A later economic strategy needs its own complete registration before strategy code or backtesting.

Plan creation precedes new implementation and downloads. Record the real commit hash after committing; leave it absent until then. The read route is in README.md and the shared specification.
