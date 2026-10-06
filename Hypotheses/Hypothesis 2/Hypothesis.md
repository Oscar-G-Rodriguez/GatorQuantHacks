# Hypothesis 2 registration

Internal hypothesis ID: **H02**. Registration: **draft / unregistered**. Economic idea: **TBD**. This is a template; no backtest or performance claim exists.

Complete the substantive fields and commit this file before writing code for this hypothesis or running any backtest. A blank-template or starter commit is preparation only. See [the shared workflow](../README.md) and [judging/research rules](../../README.md).

## Economic claim

We expect **[universe: TBD]** to **[behavior: TBD]** over **[horizon: TBD]** because **[economic mechanism and other side: TBD]**. The edge persists because **[reason: TBD]**. If true, we should see **[testable prediction: TBD]**. It fails if **[falsification condition: TBD]**.

- Working title and purpose: TBD.
- Edge source (risk premium, behavior, structural constraint, liquidity provision, or justified alternative): TBD.
- Who takes the other side, and why: TBD.
- Evidence supporting the mechanism and its persistence: TBD.
- Borrowed strategy/research, citations, and our distinct extension: TBD.
- Simpler explanations and the comparison that would distinguish them: TBD.

## Data and universe contract

- Market, instruments, historical membership, eligibility, and liquidity filters: TBD.
- Sources, access/entitlement requirements, fields, and citations: TBD.
- Dataset version/retrieval identity and permitted evidence retention: TBD.
- Available history start/end, bar frequency, and timezone: TBD.
- Point-in-time/delisted coverage; any survivorship limitation and its likely effect: TBD.
- Splits/dividends, adjusted returns versus executable prices, and volume treatment: TBD.
- Missing data, halts, stale prints, asynchronous feeds, and exclusion/fill policy: TBD.
- Event publication time, vendor availability, revisions, and availability approximations: TBD.

## Signal, delay, and execution contract

- Signal formula and inputs: TBD.
- Information cutoff / feature availability timestamp: TBD.
- Decision timestamp and timezone: TBD.
- Order timestamp, type, holding/rebalance period, and executable market session: TBD.
- Fill timestamp/convention and minimum lag in bars/time: TBD. Close-based signals must fill at the next feasible bar, never the same close.
- Engine delay versus any explicit signal shift; how the actual timeline will be verified: TBD.
- Extra latency/delay sensitivity and expected effect: TBD.
- Unfilled/rejected orders, pending orders, liquidity, and stale-bar behavior: TBD.

## Frozen split and validation plan

- Final data endpoint and exact available history used to determine the split: TBD.
- Final holdout length: shorter of the most recent 20% of history and two years; calculated dates: TBD.
- In-sample start/end, OOS start/end, inclusive/exclusive boundary convention, and expected bar counts: TBD.
- Chronological walk-forward train/validation windows: TBD.
- Purge gap length and rationale from overlap/target/holding horizon: TBD.
- Train-only transformations, feature selection, and model fitting: TBD.
- Baselines/factors, primary selection metric, and candidate-selection rule: TBD.
- Nearby-parameter robustness grid, permitted search budget, and maximum planned variants: TBD.
- Repository-wide comparison plan that keeps OOS out of strategy selection: TBD.
- Known prior inspection/exposure to these dates, if any: TBD (state none only if true).
- Final OOS evaluation procedure and frozen configuration: TBD.

## Planned parameters and experiments

| Choice | Registered default | Permitted IS variants | Reason |
| --- | --- | --- | --- |
| Signal/lookback/model choices | TBD | TBD | TBD |
| Holding/rebalance choices | TBD | TBD | TBD |
| Sizing/risk choices | TBD | TBD | TBD |

Every tested variant and failed attempt must be retained in `Research Log.md` and `../EXPERIMENTS.csv`. State the total across folders when reporting. Material changes become dated amendments rather than rewritten prior expectations.

## Costs and sizing

- Commissions/fees in bps per side and round-trip equivalent, with evidence: TBD.
- Spread, slippage, and impact assumptions; how double counting is avoided: TBD.
- Borrow, financing, or instrument-specific costs: TBD.
- Turnover definition/units and implementation checks: TBD.
- Doubled-cost scenario and acceptance/failure criterion: TBD.
- Initial capital and position sizing/volatility target: TBD.
- Maximum per-name, per-sector, gross/net, concentration, and leverage exposures: TBD.
- Maximum plausible single-position loss and portfolio risk budget: TBD.
- De-risking trigger/action and conditions for scaling back in: TBD.

## Risk and capacity checks

- Market beta, momentum, value, or other applicable factor comparisons: TBD.
- Crash, volatility spike, non-trending market, and other adverse regimes: TBD.
- Annual/period attribution and concentration-of-profit check: TBD.
- Tail-loss, worst-period, skew, overlapping-return, and Sharpe-uncertainty checks: TBD.
- Number of names, ADV measure/window, execution-window liquidity, and participation limit: TBD.
- Order notional versus position notional and turnover convention: TBD.
- Impact equation, coefficients, units, rationale/calibration limits: TBD.
- Capacity in dollars: estimation procedure and capital-sensitivity grid TBD; no estimate exists yet.

## Decision and evidence contract

- Required [S01–S12 signal-reading methods](../../docs/signal-reading/README.md): study-specific choices, planned code/check/evidence coverage, and justified tool exclusions with replacements: TBD; implementation/execution pending.
- Signal coverage/distribution, prediction diagnostic (rank IC, event/trigger comparison, or target-specific forecast loss), strength/state groups, training-only bin rules, horizon/delay grid, and `signal_diagnostics.csv` output plan: TBD.
- Own Webull-derived runner and local analysis paths: `backtest.py` and experiment-specific helpers, implemented after registration.
- Development/final-OOS command interface and cutoff enforcement: TBD.
- Matched market/buy-and-hold and price-only momentum/trend baselines, relevant factors, and justified exclusions: TBD.
- Past-only exposure/risk matching, cost conventions, benchmark estimation windows, and incremental effect measure: TBD.
- Factor specification where applicable, including separate momentum; data/version, frequency/currency/session alignment, units, cash/RF convention, IS-fitted versus descriptive attribution, and justified exclusions: TBD; see [signal-testing guide](../../docs/SIGNAL_TESTING_GUIDE.md).
- Signal ablation and mechanism-specific prediction/falsification tests: TBD.
- Uncertainty/null or placebo method, dependence/overlap treatment, and total-search disclosure: TBD.
- Frozen OOS comparison/diagnostic package and criteria for supported/explained/rejected/inconclusive: TBD.
- Readable `results/<run-id>/` summary, measured tables/figures, integrity checks, and reproduction manifest: follow [BACKTEST_EVIDENCE_CONTRACT.md](../../docs/BACKTEST_EVIDENCE_CONTRACT.md); exact study output plan TBD.

- Net-of-cost prediction that would support the mechanism: TBD.
- Economic/statistical failure conditions and rejection thresholds: TBD.
- Conditions under which we would decline to continue: TBD.
- Separate IS/OOS annualized return, volatility, Sharpe, max drawdown, turnover, and equity curves: planned; no values yet.
- Observation/trade counts, sample frequency, and annualization conventions: TBD.
- Reproduction command/notebook and data-access instructions to be implemented after registration: TBD.
- Five-page note allocation and decisive figures: TBD; see root README.

## Registration checklist

- [ ] The mechanism, other side, persistence, and prediction are concrete.
- [ ] Data access and point-in-time limitations are understood and documented.
- [ ] Signal timing, execution lag, costs, risk, and capacity assumptions are explicit.
- [ ] The split, purge plan, search budget, and selection/failure rules are fixed.
- [ ] The local backtest plan and incremental-signal tests distinguish the claimed effect from momentum, market, and other relevant alternatives, with readable evidence and honest verdict rules.
- [ ] S01–S12 method choices, signal/target readings, strength/horizon checks, and planned implementation/verification/evidence coverage are registered; tool exclusions and replacements are justified.
- [ ] Every consequential TBD above is resolved or explicitly justified as inapplicable.
- [ ] This substantive plan is committed before hypothesis-specific implementation or backtesting; the later research log records its actual hash.
