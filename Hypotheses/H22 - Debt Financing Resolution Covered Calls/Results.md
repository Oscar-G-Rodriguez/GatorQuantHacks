# H22 development backtest — October 4, 2026

**INCONCLUSIVE.** The registered primary setup produced one completed simulated trade and zero complete event/ordinary matched comparisons. The covered call earned less than the same stock position in that single trade. This establishes neither an incremental disclosure signal nor net alpha.

The plain-language rule was: after a disclosure explicitly says debt financing finished and funds were received, buy 100 shares and sell one call about 5% above the share price with roughly 120 days remaining. Enter after the fixed assumed disclosure clock, then close after 21 trading sessions. The call pays a premium and caps the upside; the shares still carry substantial downside. Historical daily closes and declared costs simulate fills. They do not prove those prices could have been traded.

## What actually happened

| Primary event | Result | Explanation |
|---|---|---|
| LOW, March 24, 2022 filing | Unfilled | No standard call within the fixed contract rules |
| PEP, July 18, 2022 filing | Completed | Entered July 20; exited August 18, 2022 |
| LOW, March 30, 2023 filing | Unfilled | Required decision/entry bar missing |

For the one PEP trade, the simulation funded 100 shares with **$16,826**. Stock price movement contributed **+$1,214**; the short call contributed **−$295**; dividends contributed $0; declared costs were **$57.97**. The covered-call net result was **+$861.03**, or 5.1173% of the funded stock notional. The same-date stock-only comparison returned **+$1,193.08** after its costs. The short call reduced the stock gain as the shares rallied.

PEP's ordinary-date comparison lacked a qualifying call, so it cannot enter the paired disclosure-versus-ordinary estimate. Both LOW primary comparisons were also incomplete. Zero completed matched pairs means the primary mean increment, overlay increment and confidence bounds are unavailable. Ordinary-cohort portfolio P&L is a different set of trades and is not a valid substitute for that paired comparison.

The primary event portfolio used a fixed $1 million cash account, one contract per admitted issuer, and 1,003 sessions from January 3, 2022 through December 31, 2025. Its one trade earned $861.03; most capital remained in zero-return cash. Descriptive annualized return was 0.021626%, volatility 0.021377%, Sharpe 1.01167 at zero risk-free return, maximum drawdown 0.019188%, and turnover 0.035555 times average NAV. Those portfolio ratios are not persuasive performance evidence with one trade. [Complete development KPIs](Evidence/run-v1/performance.csv) retain all variants and cohorts. [Final OOS KPIs](Evidence/run-v1/oos-performance.csv) are explicitly unavailable because all study dates were previously exposed.

## Fixed checks and limitations

| Fixed base-cost event variant | Completed trades | Net portfolio P&L |
|---|---:|---:|
| Primary 120-day/5% OTM | 1 | +$861.03 |
| 30-day maturity | 3 | +$516.24 |
| 60-day maturity | 2 | +$1,379.87 |
| 3% OTM | 1 | +$662.78 |
| 10% OTM | 1 | +$159.39 |
| One additional session delay | 1 | +$625.78 |
| Three additional sessions delay | 1 | +$1.48 |
| Five additional sessions delay | 0 | Unavailable |

These are predeclared sensitivity results, not a parameter ranking or a newly selected strategy. Higher-cost and alternative assignment cases, all eight horizons, failed/unfilled cases and unsupported cells remain in the [384-cell trial table](Evidence/run-v1/trials.csv). Three financing filings across two issuers cannot meet the registered minimum 30 pairs across 8 issuers. There are no strict positive filings in 2024 or 2025. Receipt wording is conservative: unknown excerpts do not establish that financing failed or never occurred.

The separate synthetic statistical calibration **failed**, rejecting 12 of 100 known-null replicas against the unchanged maximum 10 criterion. [Measured null evidence](Evidence/run-v1/synthetic-null-validation.json) is distinct from the 19 passing software correctness tests. Inferential claims are suppressed; sparse groups remain unsupported. The scheduled result reports zero quote-supported matched trade records, so this run supplies no executable quote-backed profit claim. Missing matching/option coverage, static-universe survivorship and the assumed historical delivery clock all limit interpretation. The [S01–S12 table](Evidence/run-v1/validation_checks.json) preserves executed, pending and failed evidence without relabeling completion as criterion success.

## Execution and reproduction evidence

The complete [economic/execution plan](Experiment%20Plan.md) was committed as `8c3e4e43bceed5ffc0b170c7aa6fcfab2a2ed5a8` before code. This run used code `f6fe1d1c526d4c693f1fd28295d7b5e02e32bc0f`, manifest `6a5e82aa93607a3d4e79444418fb65a23c54b460377c3b92ae4c8f590a85c0a7`, and acquisition identity `57d7bc2f5437b4a5c4a0edc0c052234d78bcd162d88b35b9a8ab5ce097101249`. The completed PC download stage recorded 776 anchors, 499 bar-supported cases, 277 cases without qualifying calls, 741 verified acquisition objects and zero request failures in its corrective attempt. Earlier failed attempts remain retained.

Four pilot workers in 44663033 completed 0:0 in 17 seconds each, with measured process peaks below 240 MiB. Full array 44663110 completed 0:0 for all 24 tasks; analysis 44663142 completed 0:0 in 17 seconds; return 44663156 completed 0:0 in 7 seconds. Full-array pilot tasks reused hash-verified checkpoints. Both uploaded files and 4,875 packaged members verified remotely. On return, ZIP SHA `5df0706ef66abcfdb6d1a328c43cda3103423b0e529e761edb40bc638b12937b`, 150 returned members and 25 completed stage receipts verified on the PC. The ledger's PEP net P&L reconciles with final portfolio NAV within floating-point precision. [Scheduler evidence](Evidence/run-v1/scheduler-ledger.json), [PC acceptance checks](Evidence/run-v1/pc-acceptance.json) and [return-member manifest](Evidence/run-v1/return.json) retain the boundaries of that verification; no fresh rerun from an empty output directory is claimed.

Open the local [HTML report](data/cache/run-v1/report.html) for the equity curves and full tables. Licensed source objects, immutable input/return archives, task outputs and earlier attempts remain under repository `data/cache/h22/`; they are not committed. The [run guide](README.md) describes preparation, freezing, pilot/full jobs and verified import. Reproduction uses the frozen bundle/code and source hashes, rather than the subsequently updated prose in this folder. The session driver adapts the supplied Webull/Backtrader starter; H22 owns the funded ledger and research comparisons. No live trading took place.

The appropriate conclusion is a completed development feasibility backtest with insufficient evidence to advance H22 as an alpha strategy. A broader completion rubric or a different disclosure family would require its own prospective committed plan, preserving this result and the earlier research exposure.
