# GatorQuantHacks

This repository keeps independent Systematic Trading hypotheses, their implementations, and the evidence needed to defend them. Each idea lives in its own folder under `Hypotheses/` and owns a backtest adapted from the Webull code. Plans, backtest/strategy code, settings, logs, and results stay separate; dependencies, the Webull integration, and reusable infrastructure are maintained once at the root.

This public release is a privacy-clean snapshot of a longer local development history. Historical commit IDs in research logs and manifests identify preserved development commits; they are not part of this public Git history. The public files show the plans, implementation and returned evidence, but this snapshot alone cannot independently prove the timing of an earlier registration commit.

**Write and commit a complete hypothesis before implementing its trading strategy or running its first backtest.** Exploratory statistics and analysis code may come first to help develop that hypothesis, including correlations, regressions, event studies and prediction comparisons on development data. Oscar clarified this scope on October 3, 2026; [the discovery rules](AGENTS.md#statistical-discovery-before-a-hypothesis) preserve holdouts and exploration history. The supplied judging guide specifically asks for the hypothesis commit before the first backtest. The starter's example strategies and shipped report do not establish a registered hypothesis or a result.

[The statistical discovery guide](docs/discovery/README.md) documents the nine implemented exploration studies: download historical data and write code locally, transfer the completed package to Blue, run through HiPerGator job arrays, and verify returned result tables. These studies preserve development/final-holdout separation and exploration history without simulating trades.

The competition guidance below was transcribed from the original 16 screenshots supplied on October 2, 2026, an additional judging excerpt emphasizing testing rigor over large returns, and two October 3 screenshots on benchmarking and fair tests. [Research sources](docs/RESEARCH_SOURCES.md) records the attachments and starter provenance. Rules labeled **team rule** are our operational choices. Guidance and simulator numbers are distinguished from scored evidence. Future organizer clarifications should be retained and reconciled explicitly.

For a focused reference while coding, use [Webull track rules and research checks](docs/WEBULL_RULES.md). Use the [five-page quant note working template](docs/QUANT_NOTE_TEMPLATE.md) when turning a verified hypothesis into the submission note. Both documents keep the supplied rules separate from our own results and from local workflow choices.

**Team priority: TRUE SIGNAL only.** Each local backtest must produce readable evidence for whether its registered prediction adds beyond relevant momentum, market, and other known exposures. Follow the [backtest and evidence contract](docs/BACKTEST_EVIDENCE_CONTRACT.md): matched baselines, signal ablation, feasible net costs and lag, uncertainty, robustness, and honest IS/OOS conclusions. Only advance a distinct signal supported by the registered checks in IS validation and untouched OOS. Retain explained, rejected, and inconclusive ideas; high P&L does not establish a new edge.

Read the **[required signal-reading methods](docs/signal-reading/README.md)** before writing or reviewing hypothesis code. Register S01–S12, then implement the appropriate signal/target diagnostics, strength and horizon checks, momentum/factor baselines, incremental comparisons, uncertainty, falsification, and execution checks after the hypothesis commit. Each method needs an actual implementation and readable evidence; the README includes the review checklist.

The [signal-testing guide](docs/SIGNAL_TESTING_GUIDE.md) explains the direct baseline, feature-removal and appropriate Ken French factor comparisons, including accounting, timing and uncertainty. The [project story](PROJECT_STORY.md) gives the public technical account; logs and the experiment ledger retain the detailed run record.

## Repository layout

[Massive coverage preparation](docs/massive/README.md) documents the bounded shared metadata/access check, local Massive key and ignored cache. It examines development-period feasibility without running a strategy or evaluating price correlations.

The [exploratory idea index](Hypotheses/README.md#exploratory-idea-index) links the statistical discovery folders H03–H17, with folder-owned analysis code and research logs. The [discovery guide](docs/discovery/README.md) covers completed local acquisition, HiPerGator jobs and verified returns; the [integrated findings](docs/discovery/options-final-findings.md) record the option/disclosure relationships and five possible hypotheses to explore. Discovery uses 2024–2025 development data without backtests or protected outcomes. Registered trading experiments continue to follow the strategy workflow below.

```text
AGENTS.md                      Rules for agents working in this repository
PROJECT_STORY.md                Maintained narrative across related QuantHacks work
.gitignore                     Shared ignore rules for every hypothesis
.python-version                Shared Python 3.11 selector
.env.example                   Shared credential template; actual .env is local
pyproject.toml / uv.lock        One dependency manifest and lockfile
research_config.py             Shared configuration helper / example adapter
CONVENTIONS.md                 Runtime, setup, and verification boundaries
webull_bt/                     Shared Webull/Backtrader integration
examples/                      Reference entry points, example strategies, sample report
docs/                          Shared starter documentation and research sources
  signal-reading/README.md     Mandatory methods and hypothesis code-review checklist
tests/                         Offline configuration and separation checks
Hypotheses/
  README.md                    Registration and comparison workflow
  .env.example                 One shared experiment-settings template
  EXPERIMENTS.csv               Repository-wide record of every tested variant
  Hypothesis 1/
    README.md                  Folder instructions
    Hypothesis.md              Complete and commit before strategy implementation
    Research Log.md            Registration, changes, runs, and failed ideas
    .env                       Local experiment settings, created after registration
    backtest.py                Own Webull-derived backtest, created after registration
    strategies/                Hypothesis code, created after registration
    results/                   Hypothesis output, created when results are rendered
  Hypothesis 2/                Separate plan, settings, code, log, and output
```

Read [the hypothesis workflow](Hypotheses/README.md), complete the relevant `Hypothesis.md`, and commit it before strategy implementation. Future folders must follow the same workflow. The initial two templates leave the actual economic ideas undecided.

The root `.gitignore`, `.python-version`, `pyproject.toml`, `uv.lock`, and `.venv` serve every hypothesis. Do not recreate these or copy `webull_bt/`, `docs/`, or `examples/` into new hypothesis folders. Entries labeled “created after registration” are future locations, not existing strategy implementations.

## Databento reference

Use [the Databento implementation pack](docs/databento/README.md) for Python or C++ integration. It provides task guides, source-linked API/schema/dataset cards, and explicit documentation gaps. Its [research contract](docs/databento/research/README.md) connects provider clocks, instrument identity, revisions, and costs to this repository's evidence requirements. This is documentation preparation; account access and runtime behavior remain unverified.

## What judges score


Judges score five criteria from **1 to 10**, for a total out of **50**. A high return is useful evidence only when it supports a credible argument. There is no P&L leaderboard. Code receives no separate score; judges spot-check that it runs and matches the note. Paper and live trading are not scored.

| Criterion | Points | Evidence the note should make clear |
| --- | --- | --- |
| Economic Foundation | 1–10 | Why the strategy should earn a return, who takes the other side, why the mechanism persists, and the economic evidence supporting it. |
| Innovation | 1–10 | What is creative or distinct relative to established ideas, and what we add to any strategy or research we borrow. |
| Risk Management Plan | 1–10 | Position and exposure limits, maximum plausible position loss, rules for cutting and restoring risk, factor exposures, and failure under adverse regimes. |
| Liquidity & Capital | 1–10 | How capital is deployed, how position size compares with market liquidity, realistic trading costs and impact, and estimated capacity in dollars. |
| Performance & Analytical Evidence | 1–10 | Historical or other evidence supporting the prediction, honest validation, justified costs, robustness, and reproducible results. |

**Criterion 5 is capped at 4 if either condition fails:** judges can run the code and it matches the note; the work has no lookahead and no tuning on out-of-sample data. Ties are resolved first by Performance & Analytical Evidence, then Economic Foundation.

The rubric simulator illustrates score bands of 1–3, 4–6, 7–9, and 10. Its displayed 30/50 and individual scores are examples, not scores for this repository. Aim for a supported mechanism, convincing analysis, thorough controls, and practical capacity assumptions; cosmetic code volume does not supply that evidence.

## Track rules and responsibility

- **Data:** sponsor data is optional. Free public sources are allowed. Cite every source used in the note, including research and libraries that inform the strategy.
- **Market:** any liquid, publicly traded market is allowed. Choose a market for which clean data can be obtained.
- **Costs:** every reported performance result must be net of transaction costs. State the cost in basis points (bps) per trade and justify it for the market. Define whether the quote means one side or a round trip.
- **Originality:** open-source libraries and published research are allowed with attribution. A copied strategy must be clearly extended, with the new contribution stated.
- **AI:** AI tools are allowed. We remain responsible for every line of code and every claim, and must be able to explain them.
- **Team:** every member should be able to explain the strategy and answer follow-up questions.

## Register the economic hypothesis first

Use this structure in each `Hypothesis.md`: “We expect **[universe]** to **[behavior]** over **[horizon]** because **[economic mechanism / other side]**. The edge persists because **[reason]**. If true, we should see **[testable prediction]**. It fails if **[falsification condition]**.”

The guide offers four possible sources of an edge. They are ways to reason about a hypothesis, not four strategies we have selected.

| Edge source | Why someone might pay us | What could destroy the edge |
| --- | --- | --- |
| Risk premium | Investors pay to transfer a risk they prefer not to hold; the compensation reflects real losses in bad states. | Risk arrives together, crowding compresses the premium, or apparent excess return is explained by market beta. |
| Behavioral bias | Underreaction, overreaction, anchoring, or late chasing leaves a predictable pattern. | Arbitrage removes the pattern, a crash reverses it, or performance exists only at one isolated parameter value. |
| Structural constraint | Rules, mandates, or scheduled rebalances force trading regardless of price. | The rule changes, the effect disappears in recent years, or enough traders anticipate the flow to remove its price impact. |
| Liquidity provision | Hurried buyers or sellers accept a worse price in exchange for immediacy. | Spreads and impact consume the edge, or the counterparty has information we lack. |

**Team rule:** register the universe, timing, signal, baseline, parameter search, split, costs, risk limits, and acceptance/failure criteria before strategy implementation or backtesting. Earlier statistical discovery follows [the discovery scope](AGENTS.md#statistical-discovery-before-a-hypothesis). A blank template commit does not count. Preserve the commit hash in the research log after committing; do not rewrite history to imply an idea preceded results. A material change is a versioned amendment, and every tested variant remains in the ledger.

## Lock the holdout and tune only in the earlier history

The out-of-sample period is the **most recent 20% of the history or the most recent two years, whichever is shorter**. Choose the available history and record exact dates, timezone, bar frequency, cutoff convention, and actual bar counts before tuning. Do not silently change the history endpoint to improve the split.

Within the earlier, in-sample period, use chronological walk-forward folds: train on the past and validate on what follows. Leave a purge gap long enough that overlapping targets or holding periods cannot leak across fold boundaries. Fit preprocessing, feature selection, normalization, and models on training data only. The final holdout stays outside that development process.

Freeze the strategy and select the submission candidate using in-sample validation, then evaluate the final holdout once under the registered plan. **Team rule for multiple hypotheses:** use the same final holdout for comparable candidates and do not rank, retune, or switch candidates using their holdout results. Predeclare any final comparisons; reading several holdouts to select a winner also uses the test set for selection. Record an accidental exposure or failed evaluation honestly. A rerun to correct an operational problem must retain the earlier attempt and its reason; it does not create a fresh untouched holdout.

The screenshot's example years, fold count, and bar counts are interactive illustrations. They do not fix the dates for our own dataset.

## Lag every signal and model feasible execution

If a signal uses today's closing price, it cannot also trade at that closing price. Compute it after that bar is known and fill at the **next feasible bar's open or close**, with at least one bar between the signal's source bar and execution. A next-close fill is valid only if the decision uses information available before that execution. Document the decision timestamp and fill convention.

For daily returns, this usually means applying the position decided at close `t` to returns after `t`; multiplying a position built from return `t` by that same return leaks the outcome. For event or alternative data, a historical event date alone is insufficient: account for publication time, vendor availability, timezone, revisions, and processing/order delay. An intraday bar is unavailable until it closes. A daily feed cannot establish an intraday fill.

**Team rules:** check actual signal/order/fill timestamps before trusting metrics; prohibit same-bar close fills based on that close, forward-looking joins, backward fills from future observations, and convenience execution settings that create lookahead. Test an extra execution delay when latency could matter. Record asynchronous or stale multi-asset bars, halts, and unfillable orders rather than assuming every order fills immediately. Avoid double-lagging when the engine already delays the fill: verify the timeline instead of adding an arbitrary second shift.

## Charge realistic costs and double them

Report results net of commissions, bid/ask spread, slippage, and relevant market impact. Add borrow, financing, or other instrument-specific costs where applicable. State the assumption in bps per side, its round-trip equivalent, how turnover is defined, and the source or rationale. Avoid counting the same spread twice under separate labels.

The guide illustrates adding the following after `cerebro.broker.setcash(...)` in `examples/backtest/main.py`:

```python
cerebro.broker.setcommission(commission=0.0005)  # 5 bps per side
cerebro.broker.set_slippage_perc(0.0005)        # 5 bps price slippage
```

These numbers are an illustration, not an endorsed cost model for every market. We have not added them to the shared backtest. The starter sets no explicit trading costs and does not automatically reserve the competition holdout. Before reporting results, implement the registered cost model and date restrictions, verify how the engine applies fees/slippage, and show the outcome when costs double. If the edge disappears, say so.

## Data quality must be explained

| Issue | Required handling and disclosure |
| --- | --- |
| Survivorship | Prefer a point-in-time universe including firms that later disappear. If only today's survivors are available, disclose the bias and estimate its importance. Do not describe today's index members as historical membership. |
| Corporate actions | Account for splits and dividends, explain how prices were adjusted, and keep traded prices, returns, volume, and adjustments consistent. |
| Missing data | Identify gaps, halts, and stale prints. State what was dropped or filled and why. Never fill a gap with information from after the gap. |
| Availability and revisions | Use the version and release time actually available at the decision. Record timezones, bar boundaries, vendor delays, and any approximation. |

Keep source/access instructions, retrieval dates, dataset versions or hashes where available, field definitions, and universe construction beside the experiment. **Team rule:** raw licensed data, credentials, and caches stay out of Git; `.env.example` contains placeholders only. Missing entitlement or a partial download is a limitation to resolve, not a complete dataset.

## Catch the nine common backtest pitfalls

The supplied guide identifies these failure modes. Every hypothesis must explain which checks apply and retain the result of those checks.

| Pitfall | What goes wrong | Our required check |
| --- | --- | --- |
| P-hacking / data snooping | Many signals, lookbacks, or thresholds are tried and only the winner is reported. | Commit the hypothesis first; log every attempt and failed idea; report the total variants tried across folders. |
| Overfitting | Too many parameters, complex rules, or ML choices fit a short history. | Limit the planned search; use chronological validation; show nearby parameters also work, rather than one sharp peak. |
| Lookahead bias | Same-bar signal/fill, revised data, or future index membership supplies future information. | Audit availability and execution timestamps, point-in-time inputs, joins, and signal lag. |
| Survivorship bias | Only current tickers or surviving index members are tested. | Use historical membership/delisted coverage where possible and quantify/disclose remaining bias. |
| Ignoring costs | Gross performance or free high-turnover trading exaggerates the edge. | Net costs in every performance claim; justified bps; doubled-cost sensitivity. |
| Leaking the test set | OOS results are viewed, then the strategy is changed. | Lock the final holdout; freeze selection before evaluation; log every exposure and amendment. |
| Misleading Sharpe | Too little data, overlapping returns, serial dependence, or hidden short-volatility risk makes Sharpe look stronger. | Report sample size, frequency, annualization, uncertainty where feasible, drawdown, tail behavior, and overlap treatment. |
| Regime dependence | One period, such as a crisis or a trending market, produces nearly all profits. | Show annual/period results and adverse regimes; explain concentrated profit and plausible failure conditions. |
| Unrealistic capacity | Full-size trades in illiquid names ignore price impact. | Size relative to available volume, model impact, and estimate the capital level where the edge is consumed. |

The guide's many-variants demo uses pure noise: a strong in-sample winner can arise by luck and fail out of sample. Its displayed Sharpe and returns are illustrative. When a result looks good, first check for a bug, a bias, or a familiar exposure such as market beta, momentum, or value. Report what the strategy adds beyond an appropriate baseline.

## Risk, capital, and capacity

Set limits per name and sector, and on gross exposure (total absolute exposure) and net exposure (long minus short exposure). Specify the most we can lose on one position, how position size responds to volatility, and any leverage or concentration limits. Set de-risking and re-entry rules in advance, including their triggers and actions; do not invent them after a drawdown.

Check whether the strategy is mainly market beta, momentum, or value through suitable factor regressions or comparisons. Explain behavior in a crash, volatility spike, and a market that stops trending. A good average metric does not answer tail risk.

For capacity, state strategy capital, names traded, average daily dollar volume per name, turnover, strategy volatility, spread/fees, and market volatility assumptions. Size orders as a fraction of average daily volume (ADV), check participation in the actual execution window, and estimate capacity in dollars. Distinguish position notional from the amount actually traded at each rebalance. Show how rising capital and doubled costs change net performance, including the capital where the edge is materially reduced or gone.

The screenshot's square-root impact calculator is a **rough teaching model**. Its displayed $136M capacity, example Sharpe, turnover, and participation are not empirical capacity estimates for our ideas. If using such a model, state its equation, coefficients, units, assumptions, and calibration limits. Use our market's inputs; daily ADV alone does not justify a large fast intraday fill.

## Minimum evidence and the five-page note

Report **in-sample and out-of-sample separately**, both net of costs: annualized return, volatility, Sharpe, maximum drawdown, turnover, and an equity curve. State dates, observation frequency, trade/sample counts, annualization conventions, and cost assumptions. Show doubled-cost results and nearby-parameter robustness. Period/year breakdowns, worst-month results, skew, factor comparisons, and delay sensitivity support the argument where relevant.

The main PDF is **at most five pages including figures and tables**, with **11 pt or larger font and standard margins**. References and the optional appendix do not count toward the five-page limit. Judges are not required to read the appendix, so decisive evidence belongs in the main five pages.

The guide suggests this starting budget; the allocation is adjustable, and is not a separate scoring rule:

| Section | Suggested pages | Purpose |
| --- | --- | --- |
| Summary | 0.25 | Main prediction, finding, and scope. |
| Economic hypothesis | 0.50 | Mechanism, other side, persistence, prediction, and falsification. |
| Data & universe | 0.50 | Sources, membership, adjustments, missingness, and availability. |
| Methodology | 1.00 | Signal, lag/execution, split, validation, costs, sizing, and variant count. |
| Results | 1.25 | Separate IS/OOS metrics, equity curves, baselines, costs, and robustness. |
| Risk management | 0.50 | Limits, de-risking, factor/tail/regime behavior. |
| Liquidity & capacity | 0.50 | Deployment, participation, impact assumptions, dollar capacity. |
| Limitations & next steps | 0.50 | What failed, what could break the strategy, and what to test with more time. |
| **Total** | **5.00** | References and optional appendix are outside this budget. |

The retained October 2 track review additionally records a public GitHub repository and note submitted through Devpost, with all team members listed. The repository must provide setup, a dependency file, data-download/access instructions, signal/backtest/analysis code, and one command or notebook reproducing the headline results. A ZIP does not replace the repository link. These submission details come from that retained review rather than the screenshots; see [sources](docs/RESEARCH_SOURCES.md). This scaffold is preparation and does not yet reproduce research results.

## Paper formatting workspace

The Overleaf quant-note project (private Overleaf copy) contains the paper outline, preliminary references and preparation credits, with a matching local source at [submission/main.tex](submission/main.tex). It uses 11-point type, US Letter and one-inch margins, standard figure/table support and normal-size captions. Its eight visible main sections follow the [Systematic Trading note blueprint](https://www.gqhacks.com/tracks/systematic-trading), freshly read in the browser on October 3. Subheadings map the [Massive requirements](https://www.gqhacks.com/tracks/systematic-trading/massive) into that outline: category/strategy and mechanism, events/options data, timing/contracts, fixed horizons, ordinary-day controls, uncertainty, study windows/replay, net IS/OOS evidence, decay, sensitivity, risk, costs/liquidity/capacity and failure conditions. The subheadings are our organizational choices. The research sections remain headings only, with no hypothesis, team identity or measured result entered. Overleaf compiled the outline and credits on one main page and 18 linked references on a second page, with zero errors and warnings. Later edits to either copy require deliberate synchronization.

[References and credits](submission/REFERENCES_AND_CREDITS.md) covers all eleven selected QuantHacks chats and distinguishes source review, background ideas, upstream starter code, software and assistance. Its [627-URL public inventory](submission/SOURCE_INVENTORY.csv) preserves provenance and original inspection boundaries. The paper bibliography is preliminary; match it to the actual methods and claims before submission.

The main-track five-page rule above remains distinct from the Massive starter's unresolved two-page write-up instruction; see the [Massive submission reference](../Massive%20Track/Submission%20and%20Event%20Reference.md). Paper size and one-inch margins are chosen standard defaults, not exact dimensions prescribed by the retained rule. The template does not automatically enforce either page limit.

## Starter setup, after registration

Use the root `.python-version`, `pyproject.toml`, `uv.lock`, and `.venv` for all hypotheses. Python 3.11 is selected through `uv`; do not rely on whichever interpreter happens to be on the system path. Run setup once from the repository root. The first hypothesis example in PowerShell is:

```powershell
uv sync --locked
Copy-Item -LiteralPath '.env.example' -Destination '.env'
Copy-Item -LiteralPath 'Hypotheses/.env.example' -Destination 'Hypotheses/Hypothesis 1/.env'
```

Put shared credentials in root `.env`, and the registered market, symbols, dates, frequency, parameters, and strategy name in the selected hypothesis's `.env`. Never commit either local file. The two templates are maintained once; do not copy credentials into every experiment. Choose inputs with `WEBULL_CATEGORY`, `WEBULL_SYMBOLS`, `WEBULL_TIMESPAN`, `WEBULL_FROMDATE`, and `WEBULL_TODATE`. Use explicit timezone-aware dates. Keep `WEBULL_TODATE` strictly before the registered holdout during development, verify the actual bars returned, and do not rely on the default latest-bar count to enforce a split. Record the non-secret settings with the committed plan and run evidence so they can be reproduced.

After registration, each hypothesis must adapt the root Webull backtest into its own `backtest.py`, implementing its registered split, comparisons, diagnostics, and readable run report. Its development mode must keep OOS outside the loaded/evaluated history; its final-OOS mode evaluates the frozen package once. The expected local interface, to be implemented and documented for each idea, is:

```powershell
uv run python 'Hypotheses/Hypothesis 1/backtest.py' --phase development
uv run python 'Hypotheses/Hypothesis 1/backtest.py' --phase final-oos
```

These commands describe future hypothesis implementations; no `backtest.py` or strategy exists yet because the economic plans remain unregistered. Place the registered strategy in that folder's `strategies/<module>.py` and expose `STRATEGY_CLASS = YourClass` when retaining the starter interface. Keep outputs in separate `results/<run-id>/` directories, with a plain-language conclusion, IS/OOS strategy/baseline tables, equity/drawdown figures, factor/ablation/robustness checks, and a reproducible manifest. See the [evidence contract](docs/BACKTEST_EVIDENCE_CONTRACT.md) for acceptance and artifact requirements.

See root `docs/USAGE_EN.md` for the underlying kit interface. It is preserved upstream documentation. The optional root example harness supports `uv run python examples/backtest/main.py --hypothesis 'Hypothesis 1'` and the original `examples/backtest/.env` example interface without that option; it does not implement a complete hypothesis validation or signal verdict. The root strategies and shipped sample report remain illustrative material. API access, entitlements, and market backtests have not been verified by this scaffold.

Offline setup checks run from the root with `uv run python -m unittest discover -s tests -v`. They check experiment selection, shared credentials, missing inputs, and output separation; they are not trading evidence.

## Before making a result claim

- [ ] A substantive hypothesis commit predates hypothesis-specific code and the first backtest; its hash is recorded.
- [ ] Sources, history, universe, adjustment/missingness policy, and availability assumptions are documented.
- [ ] The final holdout and walk-forward/purge plan were fixed before tuning; candidate selection did not use OOS.
- [ ] Signals and fills have a feasible timeline, with no same-bar close leakage or future/revised input leakage.
- [ ] All performance claims are net of justified costs, with doubled-cost and applicable delay checks.
- [ ] Every tested variant and failed idea is retained; the repository-wide count is disclosed.
- [ ] Separate IS/OOS metrics, equity curves, baselines, robustness, and regime/factor checks support the note.
- [ ] The hypothesis owns its Webull-derived backtest and reports incremental evidence beyond relevant momentum/market/factor baselines, ablations, uncertainty, and an explicit supported/explained/rejected/inconclusive verdict.
- [ ] Required S01–S12 methods have registered choices, implemented diagnostics, actual check outcomes, and linked evidence; signal strength/horizon/target readings are included.
- [ ] Risk limits, de-risking/re-entry rules, ADV participation, impact, and dollar capacity are explained.
- [ ] A clean setup reproduces the headline results and matches the submitted note; dependencies/data access are documented.
- [ ] The PDF satisfies the five-page/font/margin rules and contains decisive evidence outside the appendix.
- [ ] Every member can explain the code and claims, and attribution identifies the new contribution.
