# H18–H20: verified development findings

The three registered studies completed on HiPerGator on October 3, 2026. Every primary conclusion remains **INCONCLUSIVE**. The usable matched samples are too small, quote-backed comparisons are incomplete, and the incoming-CFO compensation study has no verified absence group. These results identify data and inference limits; they do not establish an incremental trading signal.

The [registered protocol](mechanism-round1-plan.md) was committed as `7688ad1d96303039d6e61ef2dcc6f19f21764a15` before implementation or new acquisition. Earlier adaptive discovery informed these hypotheses. This development run therefore cannot be described as independent confirmation of those discoveries. [Run instructions](mechanism-run-guide.md) explain the local acquisition, scheduled computation and verified return.

## Mechanisms and trade comparisons

| Study | Question | Usable primary mechanism support | Primary trade comparison | Result |
| --- | --- | --- | --- | --- |
| H18 | Does CEO-departure disclosure precede abnormal five-session option-premium compression? | 5 matched observations, 4 issuers; minimum 12/8 unmet | 0 complete matched covered-call versus funded-long event/ordinary comparisons | Inconclusive |
| H19 | Is downside concentrated in the first five feasible sessions, with useful paid protection? | 5 matched observations, 4 issuers; minimum 12/8 unmet | 0 complete matched protective-put versus funded-long event/ordinary comparisons | Inconclusive |
| H20 | Do verified incoming-CFO compensation terms distinguish subsequent risk? | 1 usable verified-terms event/issuer; 0 verified-absence events/issuers | Verified groups unsupported; filtered portfolio abstains | Inconclusive |

“Usable” counts are the estimator's complete observations, not the number of retrieved disclosures. The CEO-category package contains 31 event and 24 ordinary anchors; the CFO package contains 34 event and 28 ordinary anchors. H18 and H19 reuse the same underlying category observations. Their counts must not be added as independent events. Each failed or unavailable comparison remains in the returned tables with its reason.

The registered three chronological prediction folds were sparse. H18's matured training/test counts were 1/1, 2/2 and 4/7; H19's were 1/1, 2/2 and 4/6. H19's common-maturity incremental fit had 10 observations across 9 issuers but failed rank/parameter support. H20's co-tag and text proxies each had 5 observations across 5 issuers and also failed support. None supplies a fitted predictive or causal claim.

## Funded portfolio accounting

These are the returned base-cost, zero-extra-delay portfolios over 502 sessions, January 2, 2024 through December 31, 2025. Capital is $1 million, positions are one standard contract unit with full strike reserves, and idle cash earns the declared 4% calendar-day rate. Annualization uses 252 sessions. Reported volatility includes variation in calendar-day cash accrual between trading sessions. Sharpe uses excess returns over that same cash convention; an all-cash excess Sharpe is undefined.

| Portfolio | Annualized return | Annualized volatility | Excess Sharpe | Maximum drawdown magnitude | Closed trades | Unfilled entries / exits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H18 covered call | 4.0915% | 0.1508% | -0.7945 | 0% | 1 | 30 / 1 |
| H19 protective put | 4.0909% | 0.1508% | -0.8858 | 0% | 1 | 30 / 1 |
| H20 verified-terms filtered put | 4.0948% | 0.1507% | Undefined | 0% | 0 | 0 / 0 |
| Cash baseline, all studies | 4.0948% | 0.1507% | Undefined | 0% | 0 | 0 / 0 |

The positive total returns mostly reflect cash interest. One eventual closed trade in H18/H19 does not mean its mandated filing-offset-5 exit filled: a failed scheduled exit remained open and the ledger attempted later liquidation. Consequently, these portfolio metrics cannot replace the missing primary matched horizon comparison. All three registered portfolios lagged or equaled cash. Their small number of positions prevents a capacity or stable risk-adjusted-performance claim.

Base costs buy at ask and sell at bid, with $0.65 per contract per side and one premium basis point of assumed adverse slippage on every leg. Doubled-cost, delayed-entry, ordinary, funded-long, price-only and H20 all-CFO portfolios are retained separately. These assumptions are research scenarios; assignment/dividend and empirical impact validity remain unresolved. Trade attempts were excluded chiefly by unavailable primary chains, insufficient prior leg volume, wide spreads and missing/freshness-limited quotes. No filter was relaxed after viewing these results.

## Computation, provenance and final freeze

The first remote setup failed before any scientific task because its transfer lacked declared root build inputs. Its log/accounting and three affected-folder operational records are preserved separately from the measured trial family. Correction commit `127e5db356b62f7313b49a3092a4fa5242726234` fixed the transfer and empty-category schema handling without changing the scientific settings. An isolated local wheel build passed, followed by 25 correctness checks on the compute node.

Actual development-v2 scheduler evidence confirms setup **44611122**, core tasks **44611123_0/1/2**, report **44611124** and return **44611125** all completed with exit `0:0`. Core elapsed times were 67, 56 and 25 seconds. Development manifest identity is `046db5f7b15d181ade994877548abdc27190946824a877662b3fbf4bc08fc5ea`. The archive transfer verified 8,447 members. The returned ZIP matched remote SHA-256 `65138084daa30d315812de86597750db76f5f1b30d428a43eed5c9dbd7c1756a`; all 65 returned members and each task completion hash verified before interpretation.

The private canonical evidence is `data/cache/massive-mechanisms/runs/development-v2/`: `aggregate.json`, each task's `findings.json`, `metrics.csv`, `signal_diagnostics.csv`, `horizon_comparison.csv`, `robustness.csv`, `equity_curves.csv`, execution/capacity evidence, S01–S12 status, prediction models and scheduler records. The shared [experiment ledger](../../Hypotheses/EXPERIMENTS.csv) retains 175 H18, 175 H19 and 181 H20 trial cells, **531 total**. A cell can be measured, unavailable or inconclusive; this total is not a count of successful primary tests.

Development freeze SHA-256 is `ec5e6b0a7e27d1beeceb2cc25652f4ef3f3a185955473db3debaa75643f1afa9`. It fixes code, settings, models and all three final hypotheses. First final acquisition began at **2026-10-03 21:09:22 UTC**, after verification and freeze, with a retained exposure receipt. The final filing window is January 1–August 31, 2026, with outcomes bounded at October 2, 2026. This document reports development only; final results belong in the later combined findings. The organizer's sealed interval has not been run.

Historical vendor-label delivery, the static survivor-selected universe, approximate American-option parity, missing full filings, dividends/assignment, broad factor/sector attribution and limited execution coverage constrain interpretation. They remain explicit in the method-status files. A future data or design improvement requires a separate versioned experiment; the 2026 window will not be reused as an untouched selection set.
