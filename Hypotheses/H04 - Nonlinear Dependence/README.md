# H04 — Nonlinear dependence

**Stage:** exploratory implementation, unregistered; first HiPerGator development run completed. See the [research log and returned evidence](Research%20Log.md). Created October 3, 2026, from the nine-idea discussion in chat `private project chat`. This folder now owns `analysis.py`; the original proposals below remain broader than the first implemented methods.

The question is whether an input contains information about a future outcome that linear or rank correlation misses. A feature could relate to volatility at both positive and negative extremes, or become relevant only beyond a threshold, while its average directional correlation remains small. That is a possible pattern to investigate, not a selected mechanism.

## Data and candidate relationships

Begin with historically observable numeric features or categorical events, paired with explicitly defined subsequent outcomes. Return direction, magnitude, volatility and downside occurrence are different targets and must remain separate. A nonlinear dependence score has no inherent positive/negative direction and cannot establish that an input adds beyond existing information.

Distinguish discrete event labels from continuous measurements when choosing estimators. Apparent dependence can come from repeated values, mixed instruments, seasonal structure, common market shocks or changes in the population. Input standardization and kernel/estimator choices must use eligible training data when the procedure feeds a prediction comparison.

## Proposed calculations

1. Calculate the H03 linear/rank relationships as an interpretable reference on the same eligible observations.
2. Estimate feature-to-target mutual information with an estimator suitable for the discrete/continuous pairing. Record estimator settings and sensitivity rather than interpreting one estimated score as a precise truth.
3. Assess distance correlation or a kernel dependence statistic such as the Hilbert–Schmidt independence criterion (HSIC). Use sample sizes and computational approximations that preserve a clear interpretation.
4. Compare the statistics with appropriate dependence-preserving null simulations through H11. An independent-observation permutation test cannot simply be carried over to a dependent financial series.
5. Visualize outcome distributions across training-defined feature ranges. Check whether the detected pattern appears in later development periods, then ask H05/H08 whether it survives controls and improves prediction.

## Expected evidence and interpretation

The future outputs would be a dependence-score table with null/search treatment, response plots, estimator-setting sensitivity, sample counts and chronological period results. Estimated dependence and incremental predictive value would be reported in separate columns.

A stable nonlinear pattern that survives suitable controls could motivate a threshold, volatility or state-dependent hypothesis. A score explained by instrument mixing, a shared trend, an arbitrary bandwidth or a handful of extremes would weaken it. A zero or noisy estimated score does not establish that every possible relationship is absent.

## HiPerGator and open choices

Kernel/distance calculations and repeated null simulations can be expensive. Parallelize candidate/target/period batches; use bounded-memory approximations only after checking them against an exact smaller reference. More resamples improve numerical resolution but do not create more observations or validate an unsuitable null.

The feature family, outcome, horizon, estimator, sample representation, approximation, null assumptions, controls, discovery-search budget and meaningful effect criterion remain open. Follow the [shared discovery boundaries](../README.md#shared-discovery-boundaries).

## Reading route

- [H08: incremental prediction](../H08%20-%20Incremental%20Prediction/README.md) and [H11: uncertainty](../H11%20-%20Robustness%20and%20Uncertainty/README.md).
- [Mutual-information estimator documentation](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.mutual_info_regression.html).
- [Kernel independence testing for dependent processes](https://proceedings.mlr.press/v32/chwialkowski14.html).
- [Signal-reading requirements](../../docs/signal-reading/README.md), particularly S03, S06, S08 and S09; no implementation or evidence coverage is claimed.

## Current implementation and execution

[analysis.py](analysis.py) implements this folder's first calculations. [The shared run guide](../../docs/discovery/README.md) identifies exactly what is implemented, open extensions, data/timing assumptions and the three-stage task graph. Author code and download history on the PC, then transfer the completed package to Blue and execute actual studies through scheduled HiPerGator jobs. [Research Log.md](Research%20Log.md) preserves preparation and subsequent runs; the shared experiment ledger records attempted comparisons after results are returned.

From the project root in a scheduled allocation, run `python "Hypotheses/H04 - Nonlinear Dependence/analysis.py" --run <frozen-run-directory>`. The coordinated runner is the preferred way to run all nine; H11 requires the core attempt receipts. No strategy registration, backtest or confirmed signal is asserted.
