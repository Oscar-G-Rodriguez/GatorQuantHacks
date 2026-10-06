# H08 — Incremental prediction

**Stage:** exploratory implementation, unregistered; first HiPerGator development run completed. See the [research log and returned evidence](Research%20Log.md). Created October 3, 2026, from the nine-idea discussion in chat `private project chat`. This folder now owns `analysis.py`; the original proposals below remain broader than the first implemented methods.

The question is which available data families improve prediction of later outcomes beyond a common, relevant baseline. This is the central comparison for ranking candidate inputs. Improvement is specific to the target, model, sample and information clock; it does not establish a profitable trading strategy.

## Target and baseline

Select one primary outcome at a time: a subsequent return, future volatility, downside-event probability or a defensible option-repricing measurement. Specify units and use a loss appropriate to that outcome. Examples are squared/absolute error for a continuous target, log loss or Brier score for probabilities, and quantile loss for a distribution-tail prediction; these are options, not selected metrics.

A baseline can use prior own-instrument returns, volatility, volume and relevant available market information. Compare it with the same model family receiving an additional candidate group, such as disclosure features or reported short measurements. Use H10 to identify substitute inputs and H05 to explain the control choices. A current snapshot cannot be inserted into historical rows as if it had been observed then.

## Proposed calculations

For the same later development-validation observations \(V\), measure:

\[
\Delta L=\frac{1}{|V|}\sum_{v\in V}\left[\ell(Y_v,\widehat f_{\mathrm{base}}(Z_v))-\ell(Y_v,\widehat f_{\mathrm{aug}}(Z_v,X_v))\right].
\]

Positive \(\Delta L\) means the augmented model has lower average loss under the specified comparison. Weighting, missing pairs and aggregation across folds require explicit treatment.

1. Fix a comparable eligible panel, primary target/horizon and availability clock. Show coverage gained/lost when a data family is added rather than hiding a change in cohort.
2. Use chronological development splits with suitable purge separation for overlapping targets. Fit scaling, imputation, selection and models inside training observations; tune through training-only inner splits when needed.
3. Compare a simple regularized model and, if sample support warrants it, a nonlinear model such as boosted trees. Keep tuning budgets comparable and record all attempts. No library or model has been installed or selected here.
4. Add/remove whole feature families and relevant substitute groups, refitting where appropriate. Compare paired losses, probability calibration where relevant and concentration by issuer/date.
5. Use H11 for uncertainty on paired improvements and selection accounting. Repeat across later development periods and neighboring choices; the final holdout remains outside this discovery comparison.

## Expected evidence and interpretation

The future output would be a baseline/augmented loss table, paired improvement estimates with intervals, period/issuer breakdowns, family-removal comparisons, sample/exclusion counts and a model/search record.

A practically meaningful, repeatable improvement could motivate a hypothesis about the candidate information. Improvement only in training, only after a much larger tuning budget, only in one issuer or only with unrealistic availability would weaken it. Model attribution is useful interpretation, but does not replace the paired comparison. No score or ranking exists yet.

## HiPerGator and open choices

Model/family/fold fits, paired resampling and bounded sensitivity calculations can run independently. CPUs may suit tabular fits; GPU use depends on the selected estimator and measured workload. More model complexity is justified by the question and sample, not by available hardware alone.

Data families, target/horizon, loss, baseline, model families, tuning budget, split dates/purge, weighting, uncertainty and practical criterion remain open. Follow the [shared discovery boundaries](../README.md#shared-discovery-boundaries).

## Reading route

- [Chronological validation reference](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html); an irregular issuer/event panel needs a compatible date-based design.
- [Signal-testing guide](../../docs/SIGNAL_TESTING_GUIDE.md) and [signal-reading requirements](../../docs/signal-reading/README.md), particularly S02 and S05–S08/S10.
- [H10: redundancy](../H10%20-%20Feature%20Redundancy/README.md) and [H11: uncertainty](../H11%20-%20Robustness%20and%20Uncertainty/README.md).

## Current implementation and execution

[analysis.py](analysis.py) implements this folder's first calculations. [The shared run guide](../../docs/discovery/README.md) identifies exactly what is implemented, open extensions, data/timing assumptions and the three-stage task graph. Author code and download history on the PC, then transfer the completed package to Blue and execute actual studies through scheduled HiPerGator jobs. [Research Log.md](Research%20Log.md) preserves preparation and subsequent runs; the shared experiment ledger records attempted comparisons after results are returned.

From the project root in a scheduled allocation, run `python "Hypotheses/H08 - Incremental Prediction/analysis.py" --run <frozen-run-directory>`. The coordinated runner is the preferred way to run all nine; H11 requires the core attempt receipts. No strategy registration, backtest or confirmed signal is asserted.


[Cross-variable follow-up](../../docs/discovery/cross-variable-options.md) specifies the October 3 extensions, actual preparation/access evidence and remaining inference/options limits. Read it before using the new configuration; the original v3 run retains its frozen code and outputs.
