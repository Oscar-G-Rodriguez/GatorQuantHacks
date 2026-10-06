# Buffered connection study: verified dense-stage findings

The corrected dense stage completed on HiPerGator and returned to the PC on October 3, 2026. All five allocations finished with exit 0:0; setup passed 38 correctness checks. Eleven returned files matched the frozen manifest and the PC/remote archive SHA-256. The [full table](../../data/cache/discovery/runs/connections-dense-20261003-v2/trials.csv) retains 4,632 attempted cells: 3,128 measured and 1,504 inconclusive. The first failed attempt remains preserved separately. These are development discoveries; no protected-window outcomes or backtests were used.

The [committed plan](options-buffered-plan.md) covers H12–H17. This page records only the completed stock/disclosure connection phase. The full local historical-options acquisition and option-enabled cluster run are still unfinished at this checkpoint. Candidate selection must account for those results before a final hypothesis shortlist is delivered.

## Delay changes the interpretation

H12 shifts inputs by actual exchange sessions while retaining later targets. Zero delay is the assumed observation close following filing+1 calendar day; it can already contain the filing reaction. Vendor label release and first-public-announcement timestamps remain unverified. The table reports issuer/past-control-adjusted next-day absolute-return associations in percentage points, without coefficient intervals.

| Input delay | CFO appointment | CEO departure | Compensation disclosure |
| --- | ---: | ---: | ---: |
| 0 sessions | -0.3284 | +0.1786 | +0.1270 |
| 1 session | +0.0818 | +0.0799 | +0.1531 |
| 3 sessions | -0.1886 | +0.0032 | +0.0761 |
| 5 sessions | -0.3152 | -0.1129 | -0.2500 |

The signs vary with delay. This weakens a claim that either leadership category alone creates a persistent, readily executable volatility forecast. It still supports examining when prices incorporate information, and whether option premiums differ from those subsequent responses. The source cohort has 31 CFO and 30 CEO observations; dense group data are known only for the 44 context-covered issuers.

## Event-focused five-session volatility is a limited lead

H17 fits fixed Ridge models in three purged chronological development folds. Baseline and augmented models share exactly the same rows within each comparison. Percentages below are computed from summed row-weighted squared-error totals, rather than averages of fold percentages. The target is future five-session RMS daily stock return, not annualized volatility or option returns.

| Input delay | Disclosure groups: event rows | Groups plus prior context: event rows | Groups plus prior context: pooled rows |
| --- | ---: | ---: | ---: |
| 0 sessions | +7.19% | +10.04% | -1.21% |
| 1 session | +2.33% | +4.10% | -1.33% |
| 3 sessions | -1.72% | -4.59% | -1.71% |
| 5 sessions | -6.93% | -12.82% | -1.58% |

Positive means lower augmented-model MSE. At zero delay, both event-focused comparisons improve in all three folds across 36 total validation event rows. The effect weakens with delay; pooled comparisons worsen. The sparse event-date cohort does not support this implementation's block interval. One-day stock-return comparisons worsen across every delay and both feature families. Different families can have different eligible training histories, so compare each augmented model with its own same-cohort baseline.

The possible lead is a short-lived conditional volatility response concentrated near leadership disclosures. It is selected from the wider discovery family and cannot be called independent confirmation or profitable option timing. The next question is whether historical option prices already incorporate that movement.

## Most sequence hypotheses lack support

H16 attempted 1,536 prior-context interaction cells, of which 64 were measurable. Most combinations miss the frozen eight-events-per-side threshold. The supported one-day volatility example is CFO appointment with debt issuance in the strictly prior 63-session history: 11 with prior debt and 19 without. Its coefficients vary by buffer and all four pointwise issuer-bootstrap intervals span zero. This is a weak exploratory lead, not a reason to advance a financing/leadership strategy.

Same-filing compensation remains a separate distinction from prior context. The earlier [v4 study](followup-findings.md) found a selected CEO-compensation interaction, with small group counts and no coefficient interval. A compensation tag does not itself prove that a transition was planned. Both the disclosure subtype and its option-pricing response still need examination.

## What remains

The main unfinished work is H13–H15 historical option pricing: three maturities, fixed contracts, pre/post buffers, eight horizons, missing/stale leg coverage, prior ordinary anchors and the pre-close quote audit. Acquisition is resumable on the PC. The cluster receives a completed, credential-free frozen package; actual option findings are added only after verified execution and return.

The final shortlist should distinguish potential pricing mechanisms, unsupported sequences, input redundancy and failed forecasts. A later trading test requires a separately completed and committed economic plan with an eligible strategy shape, feasible information/execution clock, costs, risk and falsification. Current pages are statistical discovery evidence.

The subsequent option-enabled run is now complete. Read [the integrated findings and hypothesis shortlist](options-final-findings.md) for the final acquisition, six-study results, pricing-quality audit and remaining research questions. This page preserves the earlier dense-stage checkpoint.
