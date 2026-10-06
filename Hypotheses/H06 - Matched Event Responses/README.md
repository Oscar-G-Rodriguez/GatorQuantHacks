# H06 — Matched event responses

**Stage:** exploratory implementation, unregistered; first HiPerGator development run completed. See the [research log and returned evidence](Research%20Log.md). Created October 3, 2026, from the nine-idea discussion in chat `private project chat`. This folder now owns `analysis.py`; the original proposals below remain broader than the first implemented methods.

The question is whether a disclosure category is followed by a different outcome from comparable ordinary observations. The purpose is to identify the kinds of events associated with distinctive return, volatility, downside or option-repricing responses before selecting a trading hypothesis. No category, direction or strategy has been chosen.

## Events, clocks and outcomes

Possible inputs are categorized 8-K disclosures and compatible historical stock or option measurements. Preserve issuer identity, accession, taxonomy version, category, supporting evidence and duplicate handling. Distinguish an underlying development from repeated filings and several labels in the same filing.

The event's occurrence, first public announcement, SEC acceptance and vendor classification availability are separate clocks. A retrospective category study can describe historical responses even when historical label delivery is unknown; it must be labeled accordingly. It cannot establish that a label was an earlier-available trading input.

For options, define the contract cohort, maturity, achieved moneyness, multiplier, price timestamp and staleness. Daily trade bars do not establish synchronized executable quotes, and a current snapshot is not historical implied volatility. Select a target the available fields can actually measure; portfolio P&L is outside this discovery question.

## Proposed calculations

1. Count distinct eligible events, issuers and dates by category, period and target horizon. Retain unresolved mappings and missing-price reasons.
2. Define comparable ordinary observations using pre-event information: issuer where feasible, calendar period, prior volatility/returns and relevant contract characteristics. State overlap/exclusion rules and whether other announcements remain in controls.
3. Check covariate balance and sample support before interpreting outcome differences. Avoid matching on a later realized outcome or selecting controls because their responses look convenient.
4. Estimate event-minus-control mean/median differences, outcome probabilities or distribution changes on the chosen target. With a matched-pair design, the basic contrast is the average paired outcome difference; alternative weighting requires an explicit estimand.
5. Examine the response across the declared horizon grid, development periods and issuers. Apply H05 for relevant controls and H11 for dependent uncertainty and category/horizon search accounting.

## Expected evidence and interpretation

The future output would be category-level response curves, event/control balance tables, effect estimates with intervals, counts at each exclusion stage and issuer/date concentration. No matched sample or response estimate has been produced in this folder.

A response that differs from balanced controls across later development periods could motivate a category-specific mechanism. Imbalance, earlier public information, stale marks, concentration or disappearance after adjustment would weaken the interpretation. Sparse categories can remain inconclusive; a broad taxonomy does not guarantee enough independent events.

## HiPerGator and open choices

Category/horizon estimates, bounded matching alternatives and grouped resampling can run in parallel. Matching and outcome calculations should share one verified eligible panel so comparisons do not silently use different data.

Category rules, universe, development dates, clock, target, matching/exclusions, option cohort if used, horizon grid, uncertainty and practical criterion remain open. Follow the [shared discovery boundaries](../README.md#shared-discovery-boundaries), including the Massive sponsor's separate OOS/sealed rules.

## Reading route

- [Massive track](../../../Massive%20Track/README.md), then its challenge, research-design and code-review references.
- [Observed coverage preparation](../../docs/massive/README.md); sampled access does not establish study-wide coverage.
- [H07: sequences](../H07%20-%20Event%20Sequences%20and%20Interactions/README.md) and [H11: uncertainty](../H11%20-%20Robustness%20and%20Uncertainty/README.md).
- [Signal-reading requirements](../../docs/signal-reading/README.md), particularly S01, S03–S04 and S08–S09; methods remain unimplemented here.

## Current implementation and execution

[analysis.py](analysis.py) implements this folder's first calculations. [The shared run guide](../../docs/discovery/README.md) identifies exactly what is implemented, open extensions, data/timing assumptions and the three-stage task graph. Author code and download history on the PC, then transfer the completed package to Blue and execute actual studies through scheduled HiPerGator jobs. [Research Log.md](Research%20Log.md) preserves preparation and subsequent runs; the shared experiment ledger records attempted comparisons after results are returned.

From the project root in a scheduled allocation, run `python "Hypotheses/H06 - Matched Event Responses/analysis.py" --run <frozen-run-directory>`. The coordinated runner is the preferred way to run all nine; H11 requires the core attempt receipts. No strategy registration, backtest or confirmed signal is asserted.


[Cross-variable follow-up](../../docs/discovery/cross-variable-options.md) specifies the October 3 extensions, actual preparation/access evidence and remaining inference/options limits. Read it before using the new configuration; the original v3 run retains its frozen code and outputs.
