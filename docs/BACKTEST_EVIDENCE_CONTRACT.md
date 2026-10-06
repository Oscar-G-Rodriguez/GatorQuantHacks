# Hypothesis backtests and signal evidence

Each hypothesis must own its backtest implementation, adapted from the supplied Webull/Backtrader code. Keep its `backtest.py`, strategy, experiment-specific analysis, and results in `Hypotheses/<folder>/`. Runtime/dependencies, credentials, the Webull integration, and reusable utilities remain shared at the repository root. The root `examples/backtest/main.py` is reference material and an optional example harness; it does not replace a hypothesis's experiment or establish that its signal is real.

Oscar's requirement is **TRUE SIGNAL only**: advance a claimed distinct edge only when evidence supports the registered economic prediction beyond relevant simple explanations. Momentum or a risk premium can be economically meaningful; reproducing one does not by itself demonstrate the distinct signal we claimed. Positive returns, high Sharpe, an attractive chart, or a successful program run are insufficient. A backtest provides bounded evidence, so conclusions must retain uncertainty rather than claiming proof.

These are team implementation and reporting requirements. The organizer's holdout, timing, cost, metric, and note rules remain in [WEBULL_RULES.md](WEBULL_RULES.md). The supplied additional judging excerpt emphasizes how the strategy was tested and whether its rationale holds up, rather than the size of headline returns; see [source provenance](RESEARCH_SOURCES.md).

[SIGNAL_TESTING_GUIDE.md](SIGNAL_TESTING_GUIDE.md) explains the direct comparisons, feature-removal tests, appropriate French factor attribution, return alignment, uncertainty and multiple-search treatment. Register the study-specific implementation before running it.

Use [the required signal-reading README](signal-reading/README.md) as the implementation and review checklist. Register S01–S12 choices and any justified tool exclusions/replacements, then implement the applicable methods after the substantive hypothesis commit. Method execution, criterion outcomes, and evidence must remain explicit.

## Own the experiment after registration

Complete and commit `Hypothesis.md` before implementing the trading strategy or its first backtest. Earlier exploratory statistics and analysis code are allowed under [the discovery scope](../AGENTS.md#statistical-discovery-before-a-hypothesis); retain their dates, trials and outcomes as exploratory evidence. For the registered test, specify the prediction, relevant alternative explanations, benchmark rules, matching/normalization, uncertainty method, search budget, failure conditions, and decision thresholds. There is no universal Sharpe, p-value, or return cutoff added by this contract; choose and justify the registered test's criteria before seeing its results.

After registration, adapt the Webull entry point into the hypothesis's own `backtest.py`. Reuse `webull_bt/` and appropriate common utilities. The local code must own its data cutoff, folds, lag/fills, costed portfolio, comparisons, diagnostics, and reporting. A wrapper that only runs a shared example and prints its P&L does not meet this requirement. Record the upstream source and every material adaptation. Keep the root manifest, lockfile, runtime selector, and ignore rules single copies.

Implement an explicit development mode and an explicit final-OOS mode. A proposed command interface, to be implemented after registration, is:

```powershell
uv run python 'Hypotheses/Hypothesis 1/backtest.py' --phase development
uv run python 'Hypotheses/Hypothesis 1/backtest.py' --phase final-oos
```

These are future per-hypothesis commands, not currently implemented runners. Each local runner must document its actual interface and reproduction procedure.

## Keep IS and OOS separate in code and conclusions

Reserve the shorter of the most recent **20% of history and two years** as the final holdout. Fix the available history, endpoint, precise split, timezone, boundary convention, and actual observation counts before tuning. Development mode must enforce the cutoff at data loading and evaluation, rather than merely hiding OOS charts. Earlier observations may provide a documented indicator warm-up; warm-up returns are excluded from the scored evaluation.

Use chronological train/validation folds within IS, with an appropriate purge gap for overlapping targets or holding periods. Fit transforms, feature selection, sizing/hedge estimates, and models on eligible past training observations only. Log every variant and failure in the folder log and the repository-wide ledger. Select the candidate and freeze code, settings, baselines, diagnostics, and cost/delay scenarios using IS evidence.

Final-OOS mode must require the frozen configuration and an explicit final evaluation. Evaluate the predeclared analysis once as one final evaluation package, including the registered baselines and sensitivities. Do not use final results to tune parameters, add a favorable control, switch candidates, or redefine the prediction. Preserve failed attempts and correction reruns, with the reason and exposure history. An exposed holdout is not fresh because the folder or file was renamed.

A final supported conclusion requires evidence in IS validation **and** the untouched OOS period under the registered criteria. IS success alone is a candidate finding. If OOS has not been evaluated, state that plainly. If the OOS criterion fails, retain the failed result; do not retune until it passes and describe the outcome as validated. Required IS/OOS reporting does not turn the holdout into a repeated development loop.

## Distinguish the claimed signal from simpler explanations

Every study must specify and report the comparisons appropriate to its instrument and prediction. Explain justified exclusions. Keep these choices fixed before final evaluation.

| Question | Required evidence and interpretation |
| --- | --- |
| Is it just exposure to the market? | Compare with an appropriate market/buy-and-hold baseline; show gross/net exposure and relevant beta or factor-adjusted analysis. Explain the residual claim and its uncertainty. |
| Is it just momentum or trend following? | Include an appropriate price-only momentum/trend baseline. Use the same eligible universe, dates, information cutoff, feasible fill convention, and justified cost rules; document horizon and ex-ante risk matching. Report the incremental result of the proposed feature rather than attributing the whole portfolio return to it. |
| Is another familiar exposure sufficient? | Check relevant value, sector, carry, volatility, liquidity, or other factors where applicable. State the factor source, alignment, specification, and estimation window. Do not automatically apply equity factors to an unsuitable market. |
| Does the proposed information add anything? | Run a predeclared ablation: remove or replace the proposed signal while holding the rest of the experiment comparable. Compare a baseline using only already-known price/factor information with the proposed feature added. Explain whether the mechanism's predicted effect remains. |
| Could chance or selection explain it? | Show the total search/variant count and predeclared uncertainty or null/placebo checks appropriate to the data. Respect time dependence and overlapping observations; explain the assumptions and limits. Do not present a single selected p-value as proof. |
| Does the mechanism predict the observed pattern? | Test the registered direction, horizon, event/state dependence, and falsification condition. A profitable portfolio can still fail its mechanism test. |
| Is it one lucky setting or regime? | Show nearby IS parameters, chronological validation folds, and period/regime breakdowns. Identify concentration in one year, instrument, event, or tail state. Small samples and rare events remain explicit limits. |
| Does feasible trading remove it? | Audit input availability and signal/order/fill timestamps; apply base and doubled costs and relevant extra delay. Show participation/impact limits and any unfilled-order assumptions. Reject same-bar leakage or an edge consumed by realistic execution. |

Comparisons must disclose material differences in exposure, volatility, leverage, capital, holding period, or turnover. Use matching rules estimated from eligible past data and fixed for OOS; do not normalize using future realized volatility. Charge each strategy for its actual trading under the same justified cost conventions. Baseline selection and its tuning also count toward the search record.

Factor attribution must state the return convention, estimation method, period, observation frequency, uncertainty, and treatment of serial dependence or overlap where relevant. Distinguish a model fitted on IS and assessed unchanged on OOS from a descriptive regression fitted to OOS returns. A descriptive OOS fit cannot be used to revise the portfolio or claim a previously fitted predictive model. Factor-adjusted performance alone does not establish the economic cause; combine it with the registered prediction and ablation evidence.

## Make outputs readable enough to reach a decision

Each run writes to its own `results/<run-id>/` directory. Preserve earlier runs. Put the readable conclusion first, and provide permitted structured evidence that supports every headline claim. Never commit credentials or licensed raw data. Record the actual files written; a template or planned filename is not a completed artifact.

| Artifact to implement | Content |
| --- | --- |
| `summary.md` | Plain-language prediction, phase, verdict, strongest supporting/contradicting evidence, alternative explanations, limitations, and exact links to supporting tables/figures. |
| `metrics.csv` | Separate IS and OOS rows for strategy and applicable baselines: annualized return, volatility, Sharpe, max drawdown, turnover, observation/trade counts, units, dates, and cost scenario. State when OOS is pending. |
| `signal_diagnostics.csv` and readable signal-response tables/figures | S03–S04 coverage/distribution, appropriate prediction diagnostic, registered strength/state groups and horizons/delays, with phase/fold, units, counts/exclusions, estimates/intervals, and missing-value reasons. |
| Equity/drawdown figures and permitted series | Clearly labeled strategy/baseline names, dates, units, legend, net-cost convention, IS/OOS boundary, and comparable axes. Mark the evaluation phase and avoid joining phases in a way that hides the split. |
| `baseline_comparison.csv` and factor diagnostics | Incremental comparisons, exposures, factor model specification, effect/residual estimates, uncertainty, and applicability limits. Identify known exposures that could explain the result. |
| `robustness.csv` | Registered parameter neighbors, chronological folds, cost/delay sensitivities, ablations, and appropriate placebo/null outcomes. Label IS tuning and frozen OOS diagnostics distinctly. |
| Permitted execution audit / trade summary | Auditable information, decision, order and fill timestamps; prices/cost convention; position/exposure/turnover and rejected/unfilled-order treatment. Preserve enough derived evidence to check the timing claim. |
| `validation_checks.json` | Actual pass/fail/pending results for availability, split/purge, lag/fills, costs, risk constraints, and artifact completeness, with reasons. Include S01–S12 coverage: implementation location, actual verification/execution, criterion outcome, evidence links, and any registered inapplicable tool with reason/replacement. A failed critical integrity check invalidates a signal conclusion; missing required evidence prevents support. |
| `manifest.json` | Run ID and time, hypothesis and registration/code revisions, non-secret frozen settings, source/data identity, actual split/counts, search count, randomness seeds where used, OOS exposure history, and reproduction command. Record dirty working-tree content when relevant rather than implying a commit reproduces uncommitted code. |

Use full metric names and explain specialist terms in the summary. Report missing/undefined statistics and their reasons rather than replacing them with zero. Draw attention to practical effect size, uncertainty, and the evidence against the idea. Tables and figures must agree with the summary and submission note. The decisive analysis belongs in the five-page note even if additional supporting output is retained.

## Conclude honestly and advance only supported distinct signals

Each summary must give one verdict with its evaluation scope:

| Verdict | Meaning |
| --- | --- |
| **SUPPORTED incremental signal** | Under the registered criteria, a feasible net effect supports the mechanism in IS validation and untouched OOS, adds beyond relevant frozen baselines/known exposures, and passes critical integrity checks. State uncertainty, scale, and tested scope; this is evidence, not proof of permanent alpha. |
| **EXPLAINED by known exposure** | Performance is adequately accounted for by momentum, beta, another factor, or the baseline; the claimed distinct contribution has not been established. |
| **REJECTED** | A registered failure condition occurred, including insufficient net edge, OOS failure, failed mechanism prediction, or invalid integrity/execution. Identify the decisive reason. |
| **INCONCLUSIVE / not yet evaluated** | The evidence, sample, necessary diagnostic, or untouched OOS evaluation is missing or insufficient. State what remains unresolved. |

Only the supported category qualifies as an established distinct candidate under the team's TRUE SIGNAL requirement. Development summaries may call an idea an **IS candidate pending OOS**, but must not use the final supported verdict. Rejected, explained, and inconclusive ideas remain in the record, including their costs and failed variants. Do not manufacture positive conclusions to satisfy the goal.
