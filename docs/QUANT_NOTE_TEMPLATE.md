# Five-page quant note working template

Use this for the **main Systematic Trading track** after a hypothesis has been registered and its results verified. Replace every `[placeholder]` with a sourced fact or a measured result. Remove unfilled prompts before export. Do not insert values from the starter report or the page's synthetic simulators. The accompanying [rules reference](WEBULL_RULES.md) and [source register](RESEARCH_SOURCES.md) identify the underlying material.

The main PDF is limited to **five pages, including figures and tables**, with **at least 11-point font and standard margins**. References and an optional appendix are outside the limit, but keep decisive evidence in the main pages. The interactive planner suggested this adjustable budget: Summary 0.25; Economic Hypothesis 0.50; Data & Universe 0.50; Methodology 1.00; Results 1.25; Risk Management 0.50; Liquidity & Capacity 0.50; Limitations & Next Steps 0.50 pages. The total is five pages.

Use the measured output from the hypothesis's own Webull-derived backtest and the [evidence contract](BACKTEST_EVIDENCE_CONTRACT.md). The summary must reach an honest supported/explained/rejected/inconclusive decision about the claimed incremental signal, with uncertainty. Positive returns alone cannot supply that conclusion.

## 01 — Summary

In a few sentences: **[strategy/rule]** trades **[instrument and universe]** at **[frequency]**. We expect an edge because **[economic mechanism]**. On the untouched **[OOS dates]** period, after **[cost convention]**, the strategy produced **[annualized return]**, **[Sharpe]**, and **[maximum drawdown]**. State the principal qualification if it changes how those numbers should be understood: **[qualification]**.

This section feeds **Economic Foundation** and **Performance & Analytical Evidence**. Write the summary last, after the evidence is frozen.

**Signal conclusion:** [supported incremental signal / explained by known exposure / rejected / inconclusive]. **Evidence beyond momentum/market or other relevant baselines:** [measured incremental result and uncertainty]. **IS validation and untouched OOS agreement or contradiction:** [measured outcome against preregistered criteria]. Do not use the supported verdict if final OOS or a critical check is missing.

## 02 — Economic Hypothesis

State the claim as it existed **before the backtest**: “We expected **[universe]** to **[behavior]** over **[horizon]** because **[risk premium, behavioral bias, institutional/structural constraint, or liquidity need]**. **[Who takes the other side]** accepts this trade because **[reason]**. The opportunity may persist because **[barrier or compensation for risk]**. We predicted **[observable implication]**; **[observation]** would count against the hypothesis.”

Identify the pre-results registration commit: **[actual commit hash and date]**. Explain the contribution beyond any cited prior research. This section feeds **Economic Foundation** and **Innovation**.

## 03 — Data & Universe

| Item | Record for this study |
| --- | --- |
| Instruments and universe construction | [Symbols/types; selection rule; historical membership/delistings] |
| Bar/event frequency and timezone | [Frequency, exchange timezone, session convention] |
| History and final holdout | [Start/end; IS range and count; OOS range and count] |
| Sources | [Provider, exact data set/fields, retrieval/version/date, citation for every source] |
| Corporate actions | [Split/dividend adjustment and its effect] |
| Missing/stale data | [Drop/forward-fill/halts policy, maximum staleness, counts affected] |
| Point-in-time availability | [Publication/vendor lag, revisions, and decision-time fields] |
| Remaining biases | [Survivorship or other known coverage limitations] |

The OOS period must be the most recent **20% of available history or two years, whichever is shorter**. Give exact dates and counts from the data actually used, not from the page's example. Cite every market, factor, benchmark, and research source.

## 04 — Methodology

Explain the full path from observation to fill:

1. **Signal:** At **[timestamp]**, calculate **[formula/features]** using information available by that time. Explain parameter choices and any preprocessing.
2. **Portfolio:** Convert the signal to **[long/short/weight/order]**; define ranking, neutrality, constraints, and the benchmark or simple baseline.
3. **Sizing:** Use **[sizing rule]**, with **[position and exposure limits]** and a clear treatment of cash/leverage.
4. **Rebalancing:** Recompute every **[interval]**; state when orders are sent and how overlapping positions are handled.
5. **Execution:** Assume a fill at **[feasible later bar/price]**, after **[signal and data availability]**. State commission, spread, slippage, impact and any financing/borrow in bps or currency, specifying per side versus round trip. Explain partial/unfilled order handling.
6. **Validation:** Inside IS, use **[chronological fold dates/counts]**, **[purge gap with rationale]**, and **[planned parameter variants]**. Select/freeze the candidate without OOS, then make one final OOS evaluation. State the total number of tested variants across hypothesis folders and where failures were logged.

Include a small timeline if needed: `last usable observation → signal calculation → order submission → assumed execution → realized return`. Do not assume a close-based signal could fill at the same close.

## 05 — Results

All reported performance figures must be **net of justified transaction costs**. Give IS and OOS separately, with exact dates, observation/trade counts, and annualization. Include at least one **equity curve** in the five pages; label the IS/OOS boundary and compare with the selected baseline on the same time axis. Show the OOS evaluation date and whether it was the first exposure.

| Metric, net of costs | In sample | Out of sample | Baseline / explanation |
| --- | ---: | ---: | --- |
| Annualized return | [ ] | [ ] | [ ] |
| Annualized volatility | [ ] | [ ] | [ ] |
| Sharpe ratio | [ ] | [ ] | [ ] |
| Maximum drawdown | [ ] | [ ] | [ ] |
| Turnover, with definition | [ ] | [ ] | [ ] |
| Observations and executed trades | [ ] | [ ] | [ ] |

**Equity curve:** [insert measured and labeled figure]. **Cost sensitivity:** [base-cost versus double-cost metric or compact table]. **Robustness:** [nearby IS parameter outcomes without OOS retuning]. **Simple explanation checks:** [beta/momentum/value or relevant benchmark]. **Regime concentration and uncertainty:** [period breakdown, tail outcome, or honest lack of data]. This section feeds **Performance & Analytical Evidence**.

**Incremental signal tests:** [matched momentum/market/factor comparison; signal ablation; mechanism prediction and falsification; predeclared uncertainty/null checks and total search count]. Explain whether the proposed information adds beyond the baseline and which simple explanations remain. Identify the local backtest revision, frozen final configuration, and actual reproduction command. Link every headline result to the readable summary and retained evidence.

## 06 — Risk Management

Define **[per-name and per-sector limits]**, **[gross/net exposure caps]**, and **[maximum plausible single-position loss]**. The predeclared de-risking rule is **[trigger → action]**; re-entry requires **[condition]**. Show factor and correlation exposure to **[relevant benchmarks]**. Discuss what happens in **[crash, volatility spike, liquidity freeze, or signal-specific bad regime]** and whether backtest evidence covers those states. This section feeds **Risk Management Plan**.

## 07 — Liquidity & Capacity

State **[commission/fees]**, **[half-spread]**, **[slippage]**, and **[impact model]** with units, market source, and calibration or reasoned approximation. Show expected order size and participation relative to **[available volume during the actual execution window]**. With **[portfolio capital]**, **[turnover]**, and those cost assumptions, estimate **[rough dollar capacity before the edge materially erodes]**. Show at least one larger-capital or doubled-cost sensitivity. Distinguish traded order notional from held position notional. The page's capacity dial is illustrative; use study-specific inputs. This section feeds **Liquidity & Capital**.

## 08 — Limitations & Next Steps

Report **[failed ideas and variants tried]**, **[biases or missing data that remain]**, **[what could break the economic mechanism]**, and **[the strongest test to run with more time]**. State any OOS exposure, data-entitlement, execution, or reproducibility limits plainly. Separate tests proposed for the future from results already observed. This section feeds **Risk Management Plan** and **Performance & Analytical Evidence**.

## References and optional appendix

List every data source, library, borrowed strategy, paper, and benchmark with a usable citation; identify what was adapted. References may sit outside the five-page main limit. Extra charts may go in an optional appendix, but judges need not read it. The public repository should reproduce the headline table and curve from its documented setup; its code, assumptions, and note must agree.
