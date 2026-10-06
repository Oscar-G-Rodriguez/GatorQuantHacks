# Massive discovery: completed options and buffered connections

The local historical acquisition and all six H12–H17 studies are complete. HiPerGator ran the calculations; the PC received and verified the outputs before interpretation. The full [comparison table](../../data/cache/discovery/runs/connections-options-20261003-v1/trials.csv), [run report](../../data/cache/discovery/runs/connections-options-20261003-v1/REPORT.md), [frozen identity](../../data/cache/discovery/runs/connections-options-20261003-v1/manifest.json) and [execution receipt](../../data/cache/discovery/runs/connections-options-20261003-v1/hpg/browser-submission.json) remain in the ignored local cache. All 10,398 cells are retained: 7,662 measurable and 2,736 inconclusive. These are selected 2024–2025 discoveries, with unadjusted pointwise uncertainty across a broad search; they establish possible research questions, not a trading edge.

## What completed

| Folder | Question | Attempted | Measured | Inconclusive |
| --- | --- | ---: | ---: | ---: |
| H12 | Dense disclosure/market relationships and 0/1/3/5-session delays | 2,328 | 2,328 | 0 |
| H13 | Option-input dependence and later uncertainty/price outcomes | 2,160 | 1,849 | 311 |
| H14 | Paired event/prior ordinary option repricing and compensation context | 3,456 | 2,535 | 921 |
| H15 | Maturity relationships, trade-mark coverage and pre-close quote quality | 150 | 150 | 0 |
| H16 | Same/prior disclosure context and buffered interactions | 1,536 | 64 | 1,472 |
| H17 | Purged chronological stock-outcome prediction comparisons | 768 | 736 | 32 |

The earlier nine H03–H11 discovery studies also completed in the retained development/follow-up runs. The integrated H12/H16/H17 measurement files exactly match the previous dense-stage files by SHA-256. Their repetition verifies integration; it adds no independent replication. Read [the dense findings](options-buffered-findings.md) and [the earlier follow-up](followup-findings.md) for those results.

The acquisition retained 62 deduplicated ticker/filing event anchors and 51 prior ordinary anchors, 327 selected maturity pairs, and explicit exclusions for 12 missing maturity buckets. An ordinary anchor is the same issuer 84 sessions earlier, subject to the declared event-distance rule. It is a prior comparison rather than a calendar-matched causal control. Historical contracts, unadjusted daily prices and primary-maturity pre-close quotes are retained with source identities and raw request receipts. Both selected legs must have same-day trade bars for the primary results below; looser one-/three-session mark-age variants remain in the full tables.

The [transport amendment](options-transport-plan.md) corrected a delay we imposed without verifying the sponsor account's limit. The faster resume reused 261 prior request attempts and obtained the remaining 773 in six minutes, twelve seconds. The final acquisition has 1,034 recorded attempts, 1,033 successful HTTP-200 receipts and the preserved initial unsuccessful network attempt; no HTTP-429 response occurred. There are no separate S3 credentials in the project. No bulk quote archive or paid Databento time series was downloaded. Databento and the exchange calendar are installed in the shared PC environment.

## Option premiums contain useful risk information

The price proxy is the paired call-plus-put premium divided by approximate parity spot. It is neither vendor IV nor a claim that the options are mispriced. The target is subsequent five-session RMS daily stock return, without annualization. Each outcome correlation requires observable future option legs as well as the stock target under the frozen construction; consequently its sample is selected for future mark coverage and should not be presented as an unconditional forecast test.

For the primary approximately 120-day bucket, the same-day-mark results are:

| Observation | Lead | Outcomes / issuers | Pearson | Spearman |
| --- | --- | ---: | ---: | ---: |
| Pre-filing close | CFO appointment | 23 / 19 | 0.707 | 0.374 |
| Pre-filing close | CEO departure | 22 / 17 | 0.726 | 0.785 |
| Assumed availability +1 session | CFO appointment | 22 / 19 | 0.691 | 0.394 |
| Assumed availability +1 session | CEO departure | 21 / 17 | 0.774 | 0.871 |
| Assumed availability +3 sessions | CEO departure | 21 / 17 | 0.405 | 0.548 |
| Assumed availability +5 sessions | CEO departure | 21 / 17 | 0.422 | 0.604 |

CEO observations show a clearer rank relationship than CFO observations. The shorter approximately 30-day pre-filing proxy also relates to five-session volatility: CEO Pearson 0.804 and Spearman 0.822 across 22 outcomes/18 issuers; CFO Pearson 0.732 and Spearman 0.656 across 20/18. These cells have no correlation intervals and were selected from the full discovery family. They support including priced uncertainty in a future baseline; they do not show that a disclosure can improve that baseline or that a permitted strategy can profit.

The dense stock-only prediction result makes that next question useful. Disclosure groups plus strictly prior context reduced event-row five-session volatility MSE by 10.04% at zero input delay across 36 validation event rows and three positive folds. That improvement fell to 4.10% after one session, then became negative after three/five sessions; pooled-row scores worsened. H17 did not fit an option-augmented predictor. First-public-announcement and vendor-label release times remain unverified, so an executable signal clock still needs a separate definition.

## Repricing gives a weak direction, with wide uncertainty

For the primary 120-day bucket and same-day marks, the table compares five-session changes in the same selected contract pair within each anchor, event minus prior ordinary. Values are percentage-point differences in fractional premium changes, without fills, costs, positions or strategy P&L. Contracts can differ between event and ordinary anchors; selection applies the same declared maturity/strike rules to each.

| Observation | Lead | Pairs / issuers | Mean difference | Pointwise 95% issuer-bootstrap interval |
| --- | --- | ---: | ---: | ---: |
| Pre-filing close | CFO | 17 / 15 | +1.09 pp | -4.80 to +7.11 pp |
| Pre-filing close | CEO | 17 / 14 | -3.31 pp | -7.20 to +0.59 pp |
| Availability +1 session | CFO | 18 / 16 | -3.75 pp | -13.23 to +4.00 pp |
| Availability +1 session | CEO | 15 / 13 | -2.82 pp | -8.03 to +2.36 pp |
| Availability +3 sessions | CEO | 15 / 12 | +7.68 pp | -5.45 to +22.96 pp |
| Availability +5 sessions | CEO | 14 / 12 | +3.04 pp | -7.18 to +12.64 pp |

Every interval in this selected table includes zero. The early CEO means and medians are negative, and leave-one-issuer means stay negative at pre/+1. At +3, the positive mean accompanies a negative median (-4.41 pp), which makes issuer/outlier sensitivity material. The delayed sign changes weaken a general premium-decay claim. Quote spreads are large relative to some early contrasts, and these are premium diagnostics rather than any permitted trade payoff.

Exact same-filing compensation separates some groups but is unstable. For CEO five-session summed-premium changes, the raw with-minus-without contrast is +3.67 pp at pre (13/9 events) and -3.41 pp at +1 (12/9). The analogous CFO contrasts are +7.02 pp (15/8) and +3.28 pp (14/9). These subgroup means are unpaired, lack intervals and can differ in firm, maturity and market conditions. A compensation label does not establish a planned transition. Prior-debt/leadership interactions are also weak: only 64 of 1,536 H16 cells meet support thresholds, and the previously reported supported CFO/debt intervals span zero.

## Maturity and price quality matter

At the pre-filing close, same-day paired trade marks are available for 89/113 anchors in the 30-day bucket, 93/113 in the 60-day bucket and 99/113 in the 120-day bucket. Permitting three-session-old marks raises those counts to 101, 96 and 107. At availability +1, the respective same-day counts are 79, 91 and 95. A higher count under stale marks is additional coverage, not evidence of more reliable pricing.

Maturity-normalized premium proxies share much of their variation. Pre-event Pearson correlations are 0.937 for 30/60 days (43 events/33 issuers), 0.918 for 30/120 (43/32), and 0.970 for 60/120 (45/32). Common company risk, maturity scaling and shared algebra can explain strong input dependence. Whether the remaining maturity difference predicts anything is a future question; these correlations alone do not answer it. Approximate American-option parity uses a flat 4% rate without dividends, and achieved moneyness/DTE vary.

The pre-close primary-maturity quote audit contains 111 anchors/44 issuers. Median bid/ask spread divided by midpoint is 3.02% for calls and 2.99% for puts; 90th percentiles are 7.67% and 12.99%. Median quote ages are 3.75 seconds and 2.43 seconds, while the median leg timestamp difference is 4.05 seconds (90th percentile 36.76 seconds). Quotes are backward observations, not guaranteed simultaneous executable prices. Among 107 anchors with both quote mids and acceptable trade marks, median quote-mid sum versus trade-price sum differs by +0.16%, with a +2.46% 90th percentile. That signed percentile is not an absolute-error percentile. Only pre-event primary-maturity quotes were audited, so later daily-bar findings do not inherit this quote validation.

## Possible hypotheses to explore next

| Priority | Possible hypothesis | Evidence that motivates it | What the next specified test must resolve |
| --- | --- | --- | --- |
| First | Leadership disclosures add information beyond option-priced uncertainty near the event. | CEO premium/risk ranks are related; the dense event-only five-session model improves briefly. | Compare a priced-risk/past-market baseline with disclosure additions on identical purged chronological rows, without selecting on future option availability. A positive premium/risk correlation alone is insufficient. |
| Second | Some CEO departures resolve uncertainty, followed by relative premium compression. | Pre/+1 five-session CEO premium contrasts are negative, with negative leave-one-issuer means. | Resolve wide intervals, different ordinary dates, delayed sign changes, rates/dividends, fresh quote marks and whether an allowed strategy survives costs. |
| Supporting | The maturity curve contributes event information beyond its common risk level. | Normalized maturities correlate 0.918–0.970, leaving a smaller residual component. | Test an explicitly defined maturity difference after controlling common risk, achieved moneyness and dividends. Incremental predictive value is unmeasured. |
| Conditional | Compensation context changes the pricing response to leadership events. | Exact-filing subgroup contrasts exist but change with observation time. | Define the mechanism from actual disclosure content; support both groups, control concurrent disclosures and quantify uncertainty. “Planned” versus “surprising” is currently unverified. |
| Required control | Freshness, spread and leg synchrony explain apparent premium relationships. | Same-day coverage is lower than stale-mark coverage, and some spreads/timestamp gaps are substantial. | Acquire only a separately planned bounded quote panel, then compare synchronized quote marks with daily trades. The current pre-only audit cannot settle later pricing effects. |

Defer directional next-day stock-return hypotheses, pooled disclosure forecasts and the ordered CFO→CEO sequence extension. The current directional/pooled comparisons worsen, and ordered sequences lack support in this bounded sample. Separate CFO and CEO events remain central usable track inputs; an ordered sequence is an optional additional idea.

These are candidate exploration specifications. Before a new data source or method, Oscar's folder/plan-commit gate applies again. Before any strategy implementation/backtest, complete and commit the economic hypothesis, permitted shape, information clock, fills/costs, benchmarks, capital/risk rules and falsification criteria. The protected 2026 outcomes remain untouched.

## Reproduction and review limits

The study plan commits are 197e8a050b15f2ca09d68b5b835b4393cfa6708f, 590ee72ca8e1475d80ade565c27a00ce2c7bc00f and a4a9684f778ae8dc67bda5b4f64d82d026e21b99. Implementation checkpoints are 37c645c930f53012fe4db7b297f5a39131c017cc and 97b5c6a8b443a358f7816407d520cb8762766676. The integrated manifest is c888c3dd853059982f0a0f936be5008e084f0eda3cff1e64b0c1322e0cdf28ad. The 58-file uploaded archive hash matched 0732b66db608ee10c7badeeab4c22d956eb64a031033d1f92683c9c15656e87c on PC and Blue before extraction. Scheduler setup 44587902, six core tasks 44587904_0–_5, and report 44587905 all completed with exit 0:0; setup passed 45 correctness checks. Nineteen returned output files and ten execution-evidence files were verified; the returned ZIP hash is c5e229d21ff7b7c46fb7a8f48ab634ec32b8e9f3caf1b74ccf2e5b4538aded76. The ledger and each folder log retain all attempted cells and actual recording times.

Share with caveats within this discovery scope. Arithmetic, selected definitions/denominators, input/output hashes, actual scheduler states, timing boundary fixtures and preserved failures were checked. The static supplied universe introduces survivorship/selection concerns; raw label delivery timing, causal attribution, search-adjusted confirmation, later quote executability, option-augmented forecast performance and net strategy returns remain unverified. The failed dense v1 and slower acquisition checkpoint remain retained as history.
