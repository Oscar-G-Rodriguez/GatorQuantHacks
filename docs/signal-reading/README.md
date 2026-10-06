# Required signal-reading methods

Read this README before writing or reviewing any hypothesis code. Each hypothesis must implement these methods in its own Webull-derived backtest and analysis **after its substantive registration commit**. They let us read what the signal predicts, measure what it adds beyond familiar exposures, and decide whether feasible trading supports the registered claim in both in-sample (IS) validation and untouched out-of-sample (OOS) data.

These are **team implementation requirements**, requested by Oscar. The organizer's rules remain in [WEBULL_RULES.md](../WEBULL_RULES.md). The [signal-testing guide](../SIGNAL_TESTING_GUIDE.md) explains the comparisons; the [evidence contract](../BACKTEST_EVIDENCE_CONTRACT.md) defines the run artifacts and verdicts. This README is the checklist we use when implementing them. No hypothesis has implemented or passed these methods merely because this document exists.

## How to use this during implementation

The registered strategy/backtest requirements in this document do not prevent earlier exploratory statistical analysis. Applicable methods can help develop a hypothesis before registration under [the discovery scope](../../AGENTS.md#statistical-discovery-before-a-hypothesis). Preserve the exploration history and development/holdout boundaries; a discovery result does not satisfy the later independent evidence requirement by itself.

Before strategy/backtest coding, register the study-specific choice for **S01–S12** in `Hypothesis.md`: formulas, outcome/horizon, controls, fitting windows, uncertainty, permitted search, and support/failure criteria. The questions below are mandatory for the registered test. Choose statistical tools that fit the instrument and prediction; an equity factor regression, rank correlation, or classification metric will not suit every study. Register any inapplicable tool with a concrete reason and the appropriate replacement comparison. A missing method is pending, not inapplicable.

After registration, map each method to its actual function/module, meaningful verification, and measured evidence. Store the run's method IDs, status (`pass`, `fail`, `pending`, or `not_applicable`), reason, implementation location, and evidence links in `validation_checks.json`. For applicable methods, distinguish **implemented** from **executed** and **criterion met**. A diagnostic can run correctly and find that the signal fails. Review this coverage before final OOS and again when reading its report.

| ID | Question the implementation must answer | Minimum readable evidence |
| --- | --- | --- |
| S01 | Could we know and trade on this input at that time? | Input/decision/order/fill timeline and actual leakage checks. |
| S02 | Did development leave a fair final test? | Exact split, chronological folds, purge/warm-up treatment, fitting windows, and exposure history. |
| S03 | What does the signal measure, and does it predict the stated outcome? | Distribution/coverage and a prediction diagnostic appropriate to the target, with counts and uncertainty. |
| S04 | Does strength and timing behave as the mechanism predicts? | Registered signal groups and horizon/delay response, including sparse or contradictory results. |
| S05 | Could market exposure or momentum explain performance? | Matched cash/market, price-only trend, and other relevant baseline comparisons. |
| S06 | What improves when we add this information? | Feature-addition/removal comparisons, paired prediction and net-return differences. |
| S07 | Does a familiar factor or instrument exposure account for it? | Applicable attribution/exposure estimates, uncertainty, and the remaining incremental claim. |
| S08 | How much could chance and our search account for? | Dependence-aware intervals/null tests, sample limitations, and complete search accounting. |
| S09 | Does the economic prediction survive a serious attempt to falsify it? | Registered mechanism tests, negative controls/placebos, and failures. |
| S10 | Is the finding stable enough for its claimed scope? | Nearby settings, chronological fold/period results, regimes, and profit concentration. |
| S11 | Can we capture the effect at realistic size and delay? | Net costs, doubled costs, extra delay, fill/risk checks, participation, impact, and capacity. |
| S12 | Can another person reproduce and judge the conclusion? | Linked summary, separate IS/OOS tables/curves, method coverage, manifest, and honest verdict. |

## S01–S02: establish a valid experiment first

Implement an availability timeline for every required input: event or bar time, publication/vendor availability, revision vintage, and processing delay. The decision must follow the latest necessary input; the order and feasible fill follow the decision. A signal using today's close trades at the next feasible bar, with actual engine behavior checked so we neither leak that close nor accidentally apply the delay twice. Audit missing/stale observations, asynchronous instruments, historical eligibility, corporate actions, and units. Reject future fills of missing data and future membership as historical input.

Verify with a boundary test: truncating or changing observations unavailable after time `T` must leave earlier features, decisions, and completed fills unchanged when their inputs and fitted state are fixed to the same eligible past. Future target labels can change; they are outcomes, not decision inputs. Include an example around a delayed release or bar close and a check that an unfillable order remains unfilled under the registered policy. Preserve permitted derived evidence rather than licensed raw data.

Lock the **most recent 20% of history or two years, whichever is shorter**, using the registered history endpoint. Development mode enforces that cutoff during loading and evaluation. Within earlier IS history, train on the past and validate chronologically, purging overlap between targets/holding periods. Fit scaling, imputation, bins, feature selection, hedge/risk estimates, and models only on eligible training data. Warm-up observations do not contribute scored returns. Record exact boundaries, counts, timezone, and any previous OOS exposure. Freeze the entire diagnostic package before one final-OOS evaluation; it cannot be used to choose among hypothesis folders.

## S03–S04: read the signal before reading portfolio P&L

Output signal coverage by time and instrument: eligible, missing, excluded, stale, duplicate, and usable observations; units, quantiles, extremes, and how often the rule activates. Keep exclusions visible. Constant inputs, empty groups, or undefined statistics need a reason rather than a replacement zero.

Align each score or event with the registered **subsequent** outcome and horizon. A tradable return target starts at the feasible entry, not before the information could be acted on. Keep a research response measured from an event time distinct from the return we could capture. Implement the appropriate reading method:

- **Continuous return-ranking signal:** report Spearman rank correlation between the score and subsequent returns, often called rank information coefficient (rank IC). For cross-sectional ranking, calculate within eligible dates and report its time series; for a time-series claim, use the registered temporal pairing. Do not pool different instruments/dates without explaining weighting and dependence. Rank IC measures ordered association, not net profitability or causality. [SciPy's definition](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html).
- **Binary event or trade trigger:** report outcome rates and mean/median outcomes for eligible triggered observations versus the registered comparable non-trigger controls. Include counts, baseline rates, effect differences, and uncertainty. For a directional classifier, compare prediction accuracy with a past-fitted base-rate rule; accuracy alone does not establish a tradable edge.
- **Magnitude, volatility, or other forecast:** report the registered prediction error/loss against a simple past-fitted forecast on the same later observations. State the target and units. Improvement in volatility prediction does not establish return-direction prediction.

Select the appropriate branch in advance; implement more only when the hypothesis makes those additional claims. Complement it with a strength/state response: registered score bins, event-severity groups, or mechanism states, showing sample size, outcome, incremental difference, and uncertainty for each. Learn any bin boundaries from training data and freeze their application to validation/OOS. Expect monotonicity only if the mechanism predicts it; retain empty bins and unexpected patterns.

Implement a small registered horizon and delay grid to reveal when the response appears, fades, or reverses. Hold the eligible cohort/comparison convention fixed where possible and disclose horizon-dependent sample changes and overlapping outcomes. A response before feasible entry cannot support captured profit. Every horizon, binning rule, or threshold used for selection belongs in the search record. Keep this package fixed for final OOS rather than adding favorable charts afterward.

## S05–S07: isolate the incremental contribution

Implement relevant simple baselines: cash/no trade, market or buy-and-hold, and **the target instrument's own price-only momentum/trend**. Add sector, carry, seasonal, curve/hedge, volatility, or other explanations when the mechanism requires them. Use comparable eligibility, dates, target horizon, information cutoff, fills, capital, and justified cost rules; fit risk matching from the past. Each strategy pays for its own turnover. Report differences in leverage, volatility, exposures, and trading rather than normalizing them using future realized risk.

Compare baseline `A` using existing information with otherwise comparable `B` adding the proposed feature. Remove the feature in a predeclared ablation, refitting on training data when the comparison requires refitting. Keep tuning budgets comparable and disclosed. Report paired differences on the same evaluation observations:

```text
net_return_increment[t] = net_return_B[t] - net_return_A[t]
forecast_loss_improvement[t] = loss_A[t] - loss_B[t]
```

The second line applies to a forecasting claim. Explain missing pairs and aggregation/weighting. Give practical effect size and dependence-aware uncertainty; compare risk/drawdown alongside returns. Feature attribution from a fitted model alone does not replace this comparison. If using permutation importance, evaluate predictive performance first and address correlated features and invalid time-series shuffling; the method describes a particular fitted model's reliance on its inputs. [scikit-learn's limitations](https://scikit-learn.org/stable/modules/permutation_importance.html).

Implement applicable factor/exposure attribution. For suitable equities, register the appropriate [Ken French](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) region/frequency and three- or five-factor family **plus separate momentum where appropriate**. This complements own-instrument trend; an equity factor model is not a generic commodity-spread benchmark. Follow the [accounting and alignment guide](../SIGNAL_TESTING_GUIDE.md#3-use-french-factors-for-appropriate-equity-attribution): net NAV versus raw price change, cash/collateral/financing, RF subtraction once, percentage/decimal units, sessions/currency, missing dates, and data vintage. Retrospective realized factors are attribution inputs, not earlier-available features. Distinguish IS-fitted coefficients assessed unchanged in OOS from a registered descriptive OOS fit. Report coefficient/residual uncertainty and limits; alpha or low correlation alone does not establish a distinct mechanism.

## S08–S10: try to break the conclusion

Implement an uncertainty procedure suited to the paired effect and dependence: registered time-block resampling, event/date/issuer grouping, or appropriate regression covariance. Record the grouping/block/lag choice, interval convention, seeds where relevant, observations, distinct events/groups, and effective-sample limitations. [HAC/Newey–West](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html) is an option for compatible time-series regressions with a justified lag. Off-the-shelf Spearman p-values have sample-size limitations; they do not resolve overlapping outcomes or serial dependence. Do not use independent-row resampling or arbitrary row permutations as the default financial null. [SciPy's p-value guidance](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html).

Account for search across hypotheses, signal definitions, horizons, baselines, and parameter choices, including failed attempts. Register an appropriate correction/selection assessment and its test family; valid inputs and disclosed adaptive choices matter. A selected winner's ordinary p-value is insufficient. No universal Sharpe, p-value, or minimum trade-count threshold is introduced here; register practical effect and uncertainty criteria that fit the study. See the [guide's search treatment](../SIGNAL_TESTING_GUIDE.md#4-check-chance-mechanism-and-feasible-execution).

Implement at least one direct test of the economic prediction and one justified negative-control/placebo comparison that could contradict it. Examples include eligible non-event windows, a mechanism-irrelevant instrument, or a valid dependence-preserving null. Define the expected contrast first. Preserve the applicable calendar, eligibility, dependence, and information clock; a control containing future information is invalid. A failed prediction stays visible even when portfolio returns look attractive.

Report nearby registered parameter settings, chronological validation folds, yearly/period results, adverse regimes, and concentration by instrument/event. Show whether one year, name, or outlier supplies most of the result. Define regimes using available inputs for trading; label retrospective descriptive breakdowns. Investigate sensitivity to large observations without deleting genuine losses or choosing an exclusion after OOS. Small or conflicting samples may warrant an inconclusive verdict rather than an exaggerated confidence claim.

## S11–S12: connect the finding to feasible trading and a decision

Implement justified commission, spread, slippage, impact, and applicable financing/borrow costs, with per-side/round-trip units and no double counting. Evaluate the registered doubled-cost and extra-delay scenarios; preserve pending/rejected/partial orders and stale quotes. Check exposure/risk limits and de-risking/re-entry behavior. Report execution-window participation, order sizes, and net performance as capital/impact increases. State where the edge is consumed and where capacity remains uncertain. Register sensitivity acceptance criteria before viewing results.

Add **`signal_diagnostics.csv`** in each `results/<run-id>/` for S03–S04. Rows identify method, phase/fold, signal/target, horizon/group, units, counts/exclusions, effect/loss/association, interval, and applicable limitations; use explicit missing-value reasons. Link readable strength/horizon figures or tables from `summary.md`. The other artifacts follow the [evidence contract](../BACKTEST_EVIDENCE_CONTRACT.md), including `baseline_comparison.csv`, `robustness.csv`, `validation_checks.json`, and the reproduction manifest. Use permitted derived outputs and keep secrets out.

The summary must answer what was predicted, what the feature added, which known exposures could explain it, what contradicted it, and whether net execution and both evaluation stages met the registered criteria. Development summaries leave final OOS pending. Use **SUPPORTED incremental signal**, **EXPLAINED by known exposure**, **REJECTED**, or **INCONCLUSIVE / not yet evaluated** as defined in the contract. Wide uncertainty alone does not establish that a known factor explains the effect. Missing required evidence or failed critical integrity checks prevent a supported verdict. Only advance a distinct signal supported by IS validation and the untouched final OOS package; preserve every other outcome.

## Implementation and final-OOS review

Complete the first six checks before final OOS; the last records its actual evaluation. Keep pending items explicit.

- [ ] The completed hypothesis and S01–S12 choices were committed before hypothesis code; the actual registration hash is recorded.
- [ ] Every applicable method has code, meaningful verification, readable IS-validation evidence, and an honest recorded outcome; any exclusion has its registered reason and replacement.
- [ ] Availability, target/fill timing, data quality, split/purge, costs, and risk checks support a valid evaluation.
- [ ] Signal response, matched baselines, incremental comparisons, attribution, uncertainty, falsification, and robustness meet the registered IS selection criteria.
- [ ] All attempts/search choices and contradictions are retained in the folder log and [shared ledger](../../Hypotheses/EXPERIMENTS.csv).
- [ ] The selected code, settings, controls, diagnostic package, thresholds, and allowed data snapshot are frozen without using OOS to choose them.
- [ ] Final-OOS mode produces the same readable evidence coverage once, records exposure/failures, and preserves the measured verdict.

These boxes are a future implementation review. Both current hypothesis folders remain unregistered scaffolds; all method execution is pending.
