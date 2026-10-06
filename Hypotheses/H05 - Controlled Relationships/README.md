# H05 — Controlled relationships

**Stage:** exploratory implementation, unregistered; first HiPerGator development run completed. See the [research log and returned evidence](Research%20Log.md). Created October 3, 2026, from the nine-idea discussion in chat `private project chat`. This folder now owns `analysis.py`; the original proposals below remain broader than the first implemented methods.

The question is whether a candidate's association with a subsequent outcome remains after accounting for simpler information that could explain it. The purpose is to distinguish a new measurement from a proxy for past price behavior, volatility, liquidity or common market movements. A conditional relationship is evidence to investigate, not proof of causation or an economic edge.

## Inputs and comparisons

Choose a candidate input, a subsequent outcome and a small economically relevant control set. Own-instrument momentum, past volatility, volume, market/sector information or curve/seasonal controls may be appropriate depending on the instrument. Equity factors are not automatically suitable for a futures spread, currency or option-price change.

Separate a predictive specification using information available at the decision from retrospective attribution using realized contemporaneous factors. A later realized factor can explain an outcome retrospectively but cannot be treated as an earlier-known forecast input. Also avoid adjusting for a post-event variable that is itself part of the response without explaining the changed question.

## Proposed calculations

One exploratory specification is:

\[
Y_{i,t,h}=\alpha+\beta X_{i,t}+\theta^\top Z_{i,t}+\varepsilon_{i,t,h}.
\]

Here, \(X\) is the candidate, \(Z\) the selected controls, and \(Y\) the subsequent outcome over horizon \(h\). Any issuer/time effects, coefficient pooling and covariance method need their own justification.

1. Report the unadjusted relationship on an explicit cohort, with units and sample counts.
2. Fit a bounded sequence of control specifications on comparable observations; show how the candidate estimate changes rather than searching for a favorable control set.
3. Examine partial correlations and residual relationships as diagnostics, including multicollinearity and control sensitivity. For predictive residualization, fit both nuisance relationships on eligible training data.
4. Assess later development periods and perform a paired baseline-versus-candidate prediction comparison through H08. In-sample fit improvement does not establish later prediction improvement.
5. Use H11 for uncertainty appropriate to serial, issuer and date dependence, with all tested specifications included in search accounting.

## Expected evidence and interpretation

The future output would include unadjusted/adjusted effect tables, units and intervals, control definitions, missingness/cohort changes, period/issuer breakdowns and paired prediction evidence where applicable.

A stable conditional effect could motivate a more specific information claim. Disappearance under a relevant baseline would support a simpler explanation. Sensitivity to one control or a large cohort change requires investigation; remaining omitted information prevents a causal conclusion. No direction or support threshold has been selected.

## HiPerGator and open choices

Repeated specifications, chronological fits, issuer exclusions and covariance/resampling calculations can run independently. The control family should remain interpretable and recorded even if abundant compute makes a larger search possible.

The instrument, candidate, target/horizon, controls, predictive-versus-attribution purpose, weighting, fixed effects, covariance method and practical criterion remain open. Follow the [shared discovery boundaries](../README.md#shared-discovery-boundaries).

## Reading route

- [Signal-testing guide](../../docs/SIGNAL_TESTING_GUIDE.md), including factor applicability, units and attribution limits.
- [Signal-reading requirements](../../docs/signal-reading/README.md), particularly S05–S08; this is a reading map, not a completion receipt.
- [H08: incremental prediction](../H08%20-%20Incremental%20Prediction/README.md) and [H11: uncertainty](../H11%20-%20Robustness%20and%20Uncertainty/README.md).

## Current implementation and execution

[analysis.py](analysis.py) implements this folder's first calculations. [The shared run guide](../../docs/discovery/README.md) identifies exactly what is implemented, open extensions, data/timing assumptions and the three-stage task graph. Author code and download history on the PC, then transfer the completed package to Blue and execute actual studies through scheduled HiPerGator jobs. [Research Log.md](Research%20Log.md) preserves preparation and subsequent runs; the shared experiment ledger records attempted comparisons after results are returned.

From the project root in a scheduled allocation, run `python "Hypotheses/H05 - Controlled Relationships/analysis.py" --run <frozen-run-directory>`. The coordinated runner is the preferred way to run all nine; H11 requires the core attempt receipts. No strategy registration, backtest or confirmed signal is asserted.
