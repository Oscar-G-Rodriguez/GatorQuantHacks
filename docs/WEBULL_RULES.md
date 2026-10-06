# Webull Systematic Trading rules and research checks

This is the working rule reference for the main Gator Quant Hacks Systematic Trading entry. It records the text and visible screenshots Oscar supplied on October 2, 2026. The [source register](RESEARCH_SOURCES.md) identifies each unchanged image and the organizer's Webull starter ZIP. The [quant note template](QUANT_NOTE_TEMPLATE.md) turns the required eight sections into a document we can fill after research. Illustrative values in the interactive webpage, starter report, and simulators are **not our results**.

The supplied material is evidence of the displayed rules and advice. The team's stricter requirements in [AGENTS.md](../AGENTS.md), such as committing a complete plan before hypothesis-specific code, are local workflow decisions. A fresh website read was unavailable during this update; retain and reconcile any later organizer clarification before submission.

## What can be researched

| Topic | Supplied rule or guidance | Consequence for implementation |
| --- | --- | --- |
| Market | Any liquid, publicly traded market is eligible. | Pick a universe with clean, accessible historical data; the starter does not require one asset class. |
| Data | Sponsor data is optional; free public sources are allowed. Cite every source used. | Record provider, fields, retrieval/version, dates, frequency, adjustments, and access terms. |
| Original work | Open-source libraries and published research may be used with citation. A copied strategy needs a clear extension and disclosure of what is new. | Keep upstream code attribution and write down the team's actual contribution. |
| AI | AI tools are allowed; the team is responsible for every line of code and every claim. | Review and test generated code; every member should be able to explain the strategy. |
| Costs | Every reported performance result is net of transaction costs. State and justify the cost in basis points per trade. | Define one-side versus round-trip units; model commission, spread, slippage, impact, and relevant financing/borrow where applicable. |
| Trading | Paper and live trading are not scored. | The research note and reproducible historical analysis carry the evidence. |

## Judging

Judges assign **1–10 points to each of five equally weighted criteria**, for a total of **50**. There is no P&L leaderboard. Code has no stand-alone score, but judges may run it and compare its output with the note. The rubric simulator's displayed scores are teaching examples.

| Criterion | What the entry must explain |
| --- | --- |
| Economic Foundation | The hypothesis, counterparty, reason for the edge, persistence, and supporting economic argument. |
| Innovation | The distinct idea or genuine extension of prior research/code. |
| Risk Management Plan | Limits, de-risking, exposures, adverse states, and loss controls. |
| Liquidity & Capital | Deployment, trading friction, market impact, and plausible dollar capacity. |
| Performance & Analytical Evidence | Honest historical testing, baselines, robustness, net results, and reproducibility. |

The supplied judging screenshot says **Performance & Analytical Evidence is capped at 4/10** if the judges cannot run the code and match the note, **or** if the work has lookahead or out-of-sample tuning. Its tiebreak order is Performance & Analytical Evidence, then Economic Foundation. A high return by itself does not establish the economic or analytical case.

The additional supplied judging excerpt emphasizes testing quality, a defensible rationale, and whether the result holds up over headline return size. Oscar's local TRUE SIGNAL requirement is operationalized in [BACKTEST_EVIDENCE_CONTRACT.md](BACKTEST_EVIDENCE_CONTRACT.md): each hypothesis owns a Webull-derived backtest and produces readable evidence distinguishing its claimed contribution from momentum, beta, other familiar exposures, luck, and invalid execution. The contract's artifact names and verdict categories are team requirements, not extra published judging weights.

## Fair tests and interpretation

The later supplied fair-test screenshot reinforces four expectations: write the hypothesis up front, use realistic costs and an untouched OOS period, report failures and total variants, and reproduce the note's headline numbers. Its key terms describe backtesting as a search for failure, drawdown as peak-to-later-trough loss, turnover as trading relative to capital, and one basis point as 0.01%. Its daily-Sharpe-above-three caution is a diagnostic heuristic, not a scoring threshold. The Ken French card identifies a benchmarking reference; [SIGNAL_TESTING_GUIDE.md](SIGNAL_TESTING_GUIDE.md) explains when those equity factors apply and how direct comparisons complement them.

## Hypothesis before the result

State the economic mechanism before looking at backtest outcomes. The guide presents four ways an edge might exist: a **risk premium**, **behavioral bias**, **structural or institutional constraint**, or **liquidity provision**. They are examples of mechanisms, not selected strategies. Say who is on the other side, why they would accept the trade, why the pattern might persist, the horizon, an observable prediction, and a falsification condition. The organizer guidance asks for a hypothesis commit before the first backtest. This repository also requires the complete plan to be committed before hypothesis-specific code; see [Hypotheses/README.md](../Hypotheses/README.md).

## Data and time integrity

1. **Holdout.** Reserve the most recent **20% of the available history or two years, whichever is shorter**, as out-of-sample (OOS). Record the chosen history, exact cutoff and bar counts. The pictured 2018–2026 example is illustrative, not our split.
2. **Development.** Build and tune in the earlier in-sample (IS) history. Use chronological walk-forward folds: train on past observations and validate on later observations. Purge across a fold boundary when labels or holding periods overlap. Fit transforms and models only on their training fold.
3. **Final test.** Freeze the selected rule before evaluating the locked OOS period once. An exposed OOS result cannot become untouched again. Log correction reruns and changes honestly. Do not use several hypotheses' holdouts to select a winner after seeing their final results.
4. **Availability.** Use only data actually available when a decision is made. A close-based signal cannot fill at the same close; model its next feasible fill and verify actual engine timing. Account for timezones, publication/vendor delay, revisions, incomplete bars, and joins across feeds.
5. **Universe and prices.** Avoid selecting only today's surviving symbols or current index membership for historical tests. Explain delisted coverage and residual survivorship bias. Treat splits/dividends with suitable adjusted data and state the adjustment. Explain missing, halted, stale, or bad observations; never fill a gap from future values.

The Webull example backtests the entire fetched range, so restricting `WEBULL_TODATE` to a development cutoff and keeping the OOS period locked are research responsibilities. Verify the actual bars returned rather than relying on requested dates alone.

## Backtest and reporting checks

The page's synthetic time-series-momentum lab demonstrates three checks: move a close-derived signal to the next feasible bar, increase costs, and compare IS with OOS. Its displayed returns, Sharpe values, curves, and lookback plateau are generated examples. Its separate noise demonstration tries many variants and produces an attractive IS winner with poor OOS behavior; those numerical outputs are examples of data snooping, not an edge.

For **IS and OOS separately**, report at minimum annualized return, annualized volatility, Sharpe ratio, maximum drawdown, turnover, and an equity curve. Every performance number must be net of stated costs. Define annualization and return timing; add sample and trade counts, baselines, period/regime breakdowns, and uncertainty where useful. Show what happens when costs double and whether nearby parameter values work. Disclose failed ideas and the total number of variants attempted. Test simple explanations first, including a bug, market beta, momentum, or value exposure.

The guide names nine common ways a backtest can mislead: **p-hacking/data snooping; overfitting; lookahead bias; survivorship bias; ignoring costs; leaking the test set; misleading Sharpe; regime dependence; unrealistic capacity.** Record the check and result for each relevant one in the selected hypothesis's research log.

## Risk and capacity

Specify limits by name and sector and on gross and net exposure. State the maximum plausible loss from a position, how and when risk is cut, and how it can be restored. Check factor and correlation exposure rather than assuming the return is independent alpha. Discuss crashes, volatility spikes, and a regime in which the signal ceases to work.

Estimate how much capital could be deployed **before trading friction consumes the edge**. Include fees, half-spread, slippage, and a market-impact assumption; size orders relative to the liquidity available in the intended execution window and report a rough capacity in dollars. Show sensitivity to larger capital and doubled costs. The screenshot's square-root-impact capacity dial is a rough teaching model; its dollar output and cost figures are not our estimate.

## Webull starter: what it provides and what it does not

The supplied ZIP contains a Python 3.11+ Webull/Backtrader feed, broker integration, two example strategy modules, backtest/live entry points, documentation, `pyproject.toml`, `uv.lock`, `.python-version`, and `.env.example`. Common libraries, dependency/runtime files, documentation, and examples now live once at the repository root. Each hypothesis will adapt the Webull backtest into its own local implementation after its registration commit; see [hypothesis setup](../Hypotheses/README.md). Credentials and data entitlement are needed for real API access; possession of the ZIP does not establish either.

Run `uv sync --locked` once from the repository root. Put credentials in root `.env`; use the single `Hypotheses/.env.example` for local experiment settings. After registration, implement the folder's `backtest.py`, its strategy, development/final-OOS modes, and the registered diagnostic/reporting requirements. Record actual local reproduction commands. Relevant starter controls include `WEBULL_CATEGORY`, `WEBULL_SYMBOLS`, `WEBULL_TIMESPAN`, `WEBULL_FROMDATE`, `WEBULL_TODATE`, and `WEBULL_STRATEGY`; a retained strategy interface exposes `STRATEGY_CLASS = YourClass`. Root `docs/USAGE_EN.md` preserves the upstream interface. The optional root example harness is not a completed hypothesis validation.

The example sets **no explicit transaction costs** and does **not** enforce the OOS holdout. The screenshot proposes `setcommission(commission=0.0005)` and `set_slippage_perc(0.0005)` as illustrative 5-bps-per-side examples. They are not market-calibrated defaults; verify the Backtrader accounting and justify assumptions for the chosen instrument. The shipped HTML report and strategies are upstream examples, not our results. Do not commit real `.env` files, keys, licensed raw data, or caches. Paper/live order code is unnecessary for the scored entry.

## Note and repository delivery

The quant note PDF has **at most five pages including figures and tables**, **11-point or larger type**, and **standard margins**. References and an optional appendix are outside that limit; judges need not read the appendix. The supplied note blueprint's page allocation is a suggestion, not an additional rule. Use the [eight-section working template](QUANT_NOTE_TEMPLATE.md) for the exact content and rubric mapping.

The already-retained [released track review](../../../QuantHacks%20Preparation/Competition/Released%20Tracks%20-%20Tools%20Goals%20and%20Rubrics.md) additionally records the public GitHub repository and Devpost submission requirements, with setup, dependency declaration, data access instructions, signal/backtest/analysis code, and one command or notebook reproducing headline results. Those delivery details came from the earlier page review; they are not visible in the twelve screenshots re-shared in this chat.
