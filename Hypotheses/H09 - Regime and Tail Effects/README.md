# H09 — Regime and tail effects

**Stage:** exploratory implementation, unregistered; first HiPerGator development run completed. See the [research log and returned evidence](Research%20Log.md). Created October 3, 2026, from the nine-idea discussion in chat `private project chat`. This folder now owns `analysis.py`; the original proposals below remain broader than the first implemented methods.

The question is whether a candidate's relationship changes with an observable market state or affects extreme outcomes even when its average effect is small. Possible states include past volatility, liquidity, trend or a historically observable curve configuration. The purpose is to develop a conditional or risk-focused hypothesis with an explicit scope.

## State and target definitions

Separate three questions: whether a feature predicts the average outcome, whether it predicts a distribution tail, and whether either relationship changes with a state. A downside-probability improvement is not a return-direction claim, and a volatility relationship is not automatically mispricing.

A predictive state must be defined from available information. Thresholds, normalization and any state model are fitted on training observations. A retrospectively named crisis can support a descriptive breakdown, but cannot become an earlier-known forecast feature. For hidden-state models, distinguish real-time filtered probabilities from smoothed assignments that use later data. Rare states require their own independent counts.

## Proposed calculations

1. Define a limited state vocabulary and target/horizon, with a consistent eligible cohort. Record why each state could modify the relationship instead of searching arbitrary partitions silently.
2. Estimate conditional means, volatility or event rates and compare their uncertainty across states. Fit feature-by-state interaction terms where an interpretable regression suits the question.
3. Use quantile regression for chosen parts of the outcome distribution. Compare later-validation quantile loss against a baseline lacking the candidate; report calibration and tail-event counts where relevant.
4. If justified, examine structural breaks or a state model in chronological training/development data. Label retrospective diagnostics and count break/model searches as variants.
5. Check whether differences arise from issuer composition, missing coverage, exposure or stale prices. Use H05/H08 for controlled and incremental comparisons, and H11 for dependent uncertainty and state/horizon search accounting.

## Expected evidence and interpretation

The future output would include state-conditioned effect tables, response curves across quantiles, baseline/augmented loss comparisons, state definitions and independent counts, transition summaries where applicable and period/issuer concentration.

A repeatable effect in a state observable before the target could motivate a conditional hypothesis. An effect requiring future-smoothed labels, one isolated crisis, an outcome-selected threshold or almost no independent tail events would weaken that interpretation. A genuine rare-state association can still remain too uncertain for a strong claim. No state or quantile has been selected and no result exists.

## HiPerGator and open choices

Quantile/state/period fits, bounded model alternatives and uncertainty batches can be parallelized. Complex regime models should be compared with transparent state rules; available hardware does not resolve weak identification or rare-event support.

The input family, target/horizon, state information, thresholds/model, quantiles, development periods, control set, uncertainty and practical criterion remain open. Follow the [shared discovery boundaries](../README.md#shared-discovery-boundaries).

## Reading route

- [H05: controls](../H05%20-%20Controlled%20Relationships/README.md), [H08: prediction](../H08%20-%20Incremental%20Prediction/README.md) and [H11: uncertainty](../H11%20-%20Robustness%20and%20Uncertainty/README.md).
- [Signal-reading requirements](../../docs/signal-reading/README.md), particularly S04 and S08–S10; no required method has been executed here.
- [Quantile regression reference](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.QuantileRegressor.html).

## Current implementation and execution

[analysis.py](analysis.py) implements this folder's first calculations. [The shared run guide](../../docs/discovery/README.md) identifies exactly what is implemented, open extensions, data/timing assumptions and the three-stage task graph. Author code and download history on the PC, then transfer the completed package to Blue and execute actual studies through scheduled HiPerGator jobs. [Research Log.md](Research%20Log.md) preserves preparation and subsequent runs; the shared experiment ledger records attempted comparisons after results are returned.

From the project root in a scheduled allocation, run `python "Hypotheses/H09 - Regime and Tail Effects/analysis.py" --run <frozen-run-directory>`. The coordinated runner is the preferred way to run all nine; H11 requires the core attempt receipts. No strategy registration, backtest or confirmed signal is asserted.
