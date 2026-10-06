# Testing whether a proposed signal adds information

Our question is whether the registered information improves a defensible prediction and a feasible trading decision beyond relevant existing explanations. A positive backtest can reflect market exposure, trend, leverage, a favorable period, or a timing error. We therefore need several independent kinds of evidence. This guide explains how to implement the comparisons required by [the evidence contract](BACKTEST_EVIDENCE_CONTRACT.md); it does not select a hypothesis or report a tested edge.

## 1. Define the claim and its alternatives before looking at outcomes

Use [the required signal-reading README](signal-reading/README.md) alongside this explanation when implementing or reviewing code. Its S01–S12 checklist specifies mandatory method coverage, appropriate signal/target readings, and the evidence each run must retain.

Exploratory statistics, including analysis of subsequent outcomes in development data, may help form a candidate hypothesis under [the discovery rules](../AGENTS.md#statistical-discovery-before-a-hypothesis). Record that exploration and its selection history. When advancing to a registered test, state the participant, constraint or economic mechanism, what information becomes observable, which instrument it should affect, the direction and horizon, and what would falsify the prediction. Inspect provider schemas and market rules for feasibility. Commit the completed plan before strategy implementation or backtesting.

Register a small set of relevant comparisons. For an equity idea, these might include cash, market/buy-and-hold, price-only momentum, relevant sector/factor exposures, and the same strategy without the proposed information. For a corn calendar-spread idea, own-spread momentum, contract-seasonality and a curve/hedge baseline are more relevant than an equity size/value model. For a cross-market corn-to-equity claim, compare the equity target's own price information with the same model plus the corn information. These are examples of test design, not ideas selected for implementation.

Choose the primary outcome, practical minimum effect, uncertainty method, trial budget, benchmark tuning budget, and failure criteria in advance. A feature can help predict volatility without predicting return direction. Forecast improvement and net trading improvement are separate claims and need their own evidence.

## 2. Compare the same experiment with and without the information

Construct a simple baseline **A** using the information that could already explain the result, then an otherwise comparable model/rule **B** that also receives the proposed feature. Include the simpler stand-alone market and momentum strategies where applicable. Fit each using eligible past data and apply the registered rules to later validation periods.

Match the eligible universe, evaluation dates, target horizon, information cutoff, feasible fills, capital convention, and cost rules. Estimate risk scaling and hedge ratios from past training data. Charge each strategy for its own actual turnover; identical cost rules do not imply identical dollar costs. Disclose differences in volatility, leverage, exposure, position count, holding period and participation. More risk or trading is not automatically more information.

For a daily costed portfolio comparison, record the paired difference:

```text
incremental_return[t] = net_return_with_feature[t] - net_return_baseline[t]
```

Measure its practical size and uncertainty, alongside both portfolios' risk and drawdown. For forecasting, compare a predeclared loss on the same later observations; for event studies, define eligible matched controls before outcomes, using only pre-event information. Retain every attempted variant, including baseline tuning, in the experiment ledger. A model with the feature removed is an ablation: it tests whether the proposed information contributes to the observed result. It does not establish causality by itself.

## 3. Use French factors for appropriate equity attribution

The [Ken French library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) supplies daily/monthly equity factor series. We would start with an appropriate region and frequency, the Fama–French three- or five-factor family, and a separately downloaded momentum series when justified. The five-factor set does **not** include momentum.

| Series | Exposure represented |
| --- | --- |
| Mkt-RF | Equity market excess return |
| SMB | Small versus large companies |
| HML | Value versus growth |
| RMW | Robust versus weak profitability |
| CMA | Conservative versus aggressive investment |
| Mom | Higher versus lower prior-return stocks |
| RF | Risk-free return for the matching period |

The official [five-factor definitions](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html) describe the first five; [daily momentum](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor_daily.html) is a cross-sectional stock portfolio based on prior returns. It differs from a rule trading our instrument on its own recent trend. Use both diagnostics when relevant; a low Mom coefficient does not rule out every kind of momentum.

For a fully funded portfolio with net returns including cash, one registered attribution model could be:

```text
net_strategy_return[t] - RF[t]
    = alpha + beta_market * Mkt-RF[t]
      + beta_size * SMB[t] + beta_value * HML[t]
      + beta_profitability * RMW[t] + beta_investment * CMA[t]
      + beta_momentum * Mom[t] + residual[t]
```

The beta coefficients describe measured exposures. Alpha is the model's estimated average return left unexplained by these factors, conditional on this specification. Its estimate and interval are useful evidence; an omitted factor, changing exposure or bad accounting can still produce apparent alpha. Correlation, R-squared or alpha alone cannot establish a new economic mechanism. Report factor attribution alongside the direct baseline and ablation comparisons.

Treat published factor series as attribution references, not as proof of a benchmark that our account can trade at those returns. Any executable factor/hedge portfolio claimed as a trading comparison needs its own feasible positions, fills, costs and capital accounting. Keep the hypothetical reference and the implementable net-cost baseline clearly labeled.

Specify whether coefficients are estimated on IS and held fixed to assess OOS unexplained returns, or estimated separately for descriptive attribution in a predeclared OOS diagnostic. With fixed IS coefficients, distinguish a residual mean from a newly fitted OOS alpha. Do not fit on OOS and use the result to change trades or select a factor model. Register the specification and diagnostics before final evaluation.

### Align returns carefully

Use realized net NAV returns on a declared capital base. For a spread/futures portfolio, account for collateral cash, financing and contract multipliers; raw price changes are not automatically portfolio returns. Establish whether a series is already excess return before subtracting RF. Mkt-RF is already market excess return. Do not subtract a full RF return separately from every leg or subtract it twice from an already-excess series.

Confirm percentage-versus-decimal units from the chosen file: a value reported as 1.2 percent becomes 0.012 in a decimal-return calculation. Use consistent factor-family files, exact dates and compatible currency/session conventions. Compound strategy returns to the intended comparison period; do not repeat a daily factor across minute observations and treat those copies as independent samples. A daily equity model is a daily diagnostic and cannot establish a seconds-scale execution effect.

Audit missing dates, duplicate rows, missing-value codes, and sample reduction. Do not fill missing factor returns using future values. Keep availability/release timestamps separate from the date the factor describes. Contemporaneous realized factors can be used for retrospective attribution; they are not inputs known at an earlier trading decision.

Save the dataset URL, retrieval time, file hash, coverage and construction/version notes when a study actually acquires factors. French notes historical revisions and a January 2025 switch from FIZ to CIZ construction. A current download is not automatically a historical point-in-time vintage. [Library data notes](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).

No factor-return files were downloaded or regression run for this guide. The listed methods remain an implementation plan.

## 4. Check chance, mechanism and feasible execution

Estimate uncertainty on paired outcomes using a method that respects the data's dependence. A registered block resampling method can preserve local time structure; an event study may need grouping by issuer and date. Decide the resampling unit, block rule and interval procedure before viewing the final result. Arbitrary row shuffling or treating overlapping trades as independent can give misleading precision.

For a regular time-series regression, Newey–West/HAC covariance is one option for uncertainty with serial correlation and changing variance. It needs a justified lag choice and compatible observations; it does not fix biased data, a wrong factor model or a small sample. The [statsmodels HAC documentation](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html) describes the estimator and its equally spaced time-series assumption. A later implementation must verify the chosen library/version and numerical behavior.

Account for the complete search, across folders and parameter choices. Register a multiple-testing procedure appropriate to the study, rather than reporting the selected variant's ordinary p-value as decisive. [Harvey, Liu and Zhu's research](https://www.nber.org/papers/w20592) motivates this concern in factor discovery; it does not create a universal competition cutoff. The [statsmodels multiple-test reference](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html) lists correction methods. Such corrections require valid underlying tests and the appropriate test family; they do not repair undisclosed adaptive searching.

Use mechanism-specific falsification and negative controls. For example, predeclare whether unrelated instruments or comparable non-event windows should lack the predicted effect. A placebo must preserve the relevant dependence, seasonality and eligibility and remove the claimed relation; a careless randomization can create an unfair null. Test nearby settings and chronological regimes, including where the mechanism should fail. Preserve contradictions instead of selecting the explanation that best fits the result.

Finally, audit source/decision/order/fill timestamps, spread, commissions, slippage, impact, borrowing/financing, risk limits and capacity. Apply the registered doubled-cost and extra-delay scenarios. The supplied screenshot's warning about daily Sharpe above three is a reason to inspect the calculation and assumptions, not an automatic pass/fail threshold or proof that a strategy is invalid. Backtesting should locate the idea's failure conditions.

## 5. Require IS validation and one frozen final OOS package

Use the most recent 20% of history or two years, whichever is shorter, as the locked final holdout. Register exact history, endpoint, split convention and observation counts before tuning. Develop with chronological train/validation folds inside IS, purge overlapping labels/holding periods, and fit all transformations and matching on past training observations. This rule comes from the supplied track guidance in [WEBULL_RULES.md](WEBULL_RULES.md).

Freeze the candidate, code, settings, controls, factor specification, uncertainty procedure and cost/delay diagnostics using IS. Then evaluate the registered package once on final OOS. Do not try all hypotheses on OOS and pick the best, add controls because final results look weak, or keep retuning until both periods appear profitable. Record every exposure and corrective rerun.

Require the registered practical and uncertainty criteria in IS validation and untouched OOS for a supported distinct-signal conclusion. A positive average with an interval too wide to establish the registered effect may be inconclusive. An adequately explained known exposure does not establish our distinct contribution. Insufficient sample size, invalid timestamps or infeasible trading can prevent support even when the chart rises.

## 6. Make the answer visible in the report

The summary should answer: **What was predicted? What did the feature add? What could explain it? Did it survive both evaluation stages and feasible execution? What evidence contradicts it?** Link the supporting rows/figures and keep separate IS/OOS outputs. The [evidence contract](BACKTEST_EVIDENCE_CONTRACT.md) defines the actual files each local backtest must produce.

Use a comparison table such as this; replace placeholders only with measured results:

| Evaluation | Net strategy result | Matched momentum/baseline result | Incremental estimate and interval | Factor explanation | Costs/delay and integrity | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| IS chronological validation | Not run | Not run | Not estimated | Not assessed | Not checked | Not evaluated |
| Frozen final OOS | Locked/pending | Locked/pending | Not estimated | Not assessed | Not checked | Not evaluated |

Reports must distinguish **SUPPORTED incremental signal**, **EXPLAINED by known exposure**, **REJECTED**, and **INCONCLUSIVE / not yet evaluated**. Weak evidence is not evidence of no effect; profitable gross returns are not evidence of executable alpha. Only a supported distinct contribution advances under our TRUE SIGNAL rule, with its uncertainty and tested scope intact.
