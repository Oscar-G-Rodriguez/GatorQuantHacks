# Findings from the Massive-focused cross-variable follow-up

The follow-up completed on HiPerGator and its results returned to the PC on October 3, 2026. It produced 1,522 recorded comparisons: 713 measured and 809 inconclusive. Those counts describe implemented/supportable measurements, not successful hypotheses. All fourteen scheduler allocations completed with exit code 0:0. The [combined table](../../data/cache/discovery/runs/massive-followup-20261003-v4/trials.csv), [run report](../../data/cache/discovery/runs/massive-followup-20261003-v4/REPORT.md) and [frozen identity](../../data/cache/discovery/runs/massive-followup-20261003-v4/manifest.json) retain every attempted variant.

This is an extension selected after reviewing v3 on the same 2024–2025 development history. Its targets are split-adjusted stock-price returns and root-mean-square later daily returns, rather than option-strategy returns. The fixed 100-company universe, assumed next-calendar-day category clock, observation-close controls and small event sample remain material limitations. The options stage described in [the specification](cross-variable-options.md) still needs a fuller contract/quote/pricing panel. No backtest, later 2026 outcome or sealed window was used.

## Compensation is useful context for leadership labels

The training-only H10 input relationships show a positive association between the compensation-context indicator and CFO/CEO event indicators: Pearson correlations approximately 0.385 and 0.347 on 8,448 early-development rows for the 44 context-covered issuers. This says the labels often share an observation session. The separate H07 co-tag join establishes whether they are on the exact same CIK/accession filing; ordinary same-day overlap does not establish that identity.

Among the later-development eligible events for the one-session outcome, CFO appointments have 11 compensation co-tags and seven without one. That misses the frozen eight-events-per-group requirement and remains inconclusive. CEO departures have thirteen with and eight without compensation, across sixteen event issuers. That comparison was supportable under the configured rule, although supportability does not establish a reliable effect.

For CEO departures, the adjusted one-day RMS interaction coefficient with an exact compensation co-tag is −0.0106759450937352, or **−1.068 percentage points** beyond the model's additive main effects. The event main coefficient is +0.0077584683802356; the model therefore associates a CEO event without that co-tag with +0.776 percentage points, and a CEO event with it with −0.292 percentage points, relative to the corresponding non-event observations and controls. These are conditional linear associations, not a simple difference of raw subgroup averages or a causal news effect. There is no coefficient confidence interval, and the lead was found through a wider search. At five sessions the interaction is much smaller, approximately −0.000681, so the next-day result should not be generalized across maturities or horizons.

Compensation could help distinguish the kind of transition described in a filing. Inferring that a transition was planned or unexpected would require a separately defined and reviewed text-based distinction. The compensation label alone does not establish it. Earnings and guidance combinations lacked sufficient event support in this selected sample; they are not zero-effect findings.

## Continuous interactions did not improve prediction

The H07 adjusted next-day RMS coefficients differ by disclosure and recent price state. Per one early-development standard deviation of the second variable, CFO × past volatility is approximately −0.001505 and CEO × past 20-session return approximately −0.003050. These are descriptive coefficients with no intervals. The past controls are measured at the assumed observation close and can contain the reaction to the filing; they do not establish a clean pre-filing forecast.

H08 supplies a stronger practical check by comparing the same chronological validation observations with and without the candidate inputs. The target below is next-session stock RMS, equal to absolute next-session return. Relative improvement is calculated from row-weighted fold mean squared errors as `(baseline MSE − augmented MSE) / baseline MSE`.

| Ridge feature addition | Validation cohort | Relative MSE improvement | Interpretation |
| --- | --- | ---: | --- |
| Disclosure labels | All 28,900 eligible validation rows | +0.00158% | Very small pooled change; approximate pointwise interval includes zero. |
| Labels plus past-control interactions | Same 28,900 rows | −0.1138% | Worse pooled prediction; pointwise improvement interval is negative, with no search-adjusted interval. |
| Disclosure labels | 36 labeled event rows | +0.789% | Small aggregate improvement with fold changes −4.17%, +10.98%, −14.15%; unstable and no event-cohort interval. |
| Labels plus past-control interactions | Same 36 labeled rows | −102.56% | Error is roughly twice the baseline overall. Fold changes +29.88%, −236.13%, −105.15% show substantial instability. |

These results argue against treating these particular continuous interactions as a forecasting signal now. They do not establish that every nonlinear event relationship is absent. The existing tree cannot split the rare candidate columns into its required thirty-row training leaves; the follow-up correctly records those comparisons as inconclusive instead of interpreting identical predictions as negative evidence.

The 63-session uncertainty blocks match the longest configured horizon. H11 retains sparse event-cohort and insufficient-block comparisons as inconclusive. Its 999 valid draws support approximate pointwise intervals for eligible pooled comparisons but cannot resolve the expanded 400-comparison adjusted family. The compensation interaction is outside that interval family and has no inferential coverage from H11.

## The original matched differences remain exploratory

H06's unchanged matching rule on the same one-session inputs retains the earlier CFO mean difference of −0.5142 percentage points across eighteen pairs and the CEO difference of +0.6787 percentage points across twenty-one pairs. This is expected reuse of the same evidence, not an independent replication. The added median differences are smaller: −0.1402 and +0.3770 percentage points. Maximum absolute standardized control differences are approximately 0.260 and 0.249, so matching did not make every observed control equal.

Leave-one-issuer mean differences preserve their signs within this observed sample, but those ranges are sensitivity diagnostics rather than confidence intervals. Dependent matched-pair intervals are still unimplemented. Together, the balance, median and prediction findings favor cautious options-specific discovery over promotion of a stock-volatility association into a trading rule.

## What additional data is justified

Massive returned historical quotes for the two sampled development contracts, allowing the next core acquisition to use its own bid/ask history alongside historical references and bars. That probe is not a full-chain coverage guarantee. Preserve synchronized backward timestamps, quote ages and requested/achieved contract characteristics before comparing option premium changes, maturity or implied-move proxies.

Databento's most distinctive optional addition is dated OPRA open interest; consolidated minute quotes also provide a useful independent mark/spread audit. Its exact sample cost estimates are nonzero and no time-series data was purchased. Its one-second quote coverage begins in February 2025, so minute quotes better match the entire development window. Massive's [snapshot specification](https://massive.com/docs/rest/options/snapshots/option-contract-snapshot) exposes current IV/Greeks and prior-day open interest without a historical selector; it cannot be used as 2024–2025 history. Databento [statistics](https://databento.com/docs/schemas-and-data-formats/statistics) and [OPRA details](https://databento.com/docs/venues-and-datasets/opra-pillar) supply the relevant open-interest schema/clock requirements. Optional external-feed use in the final Massive-only-key replay remains unverified.

The [official resource list](https://gqhacks.devpost.com/resources) identifies Massive, Databento and Webull as its market-data/API partners. Webull historical option-research access was not established here, and no additional dedicated historical-options provider was identified on that list. Keep the next acquisition tied to option pricing, market expectations, liquidity and event identity rather than adding unrelated markets.

The local code/configuration is preserved in the hypothesis folders and shared `discovery/` package. Twenty-nine small local checks passed, the locked environment loaded every study on a compute node, all fourteen allocations completed, and all 26 returned report/task files passed manifest and SHA-256 verification. The archive's PC and remote SHA-256 both equal `ced60cfe1c55375d5a02dd7713f213abc01806a7573bd0a5cb3be62e62e95e25`. Detailed source/access estimates remain in the specification and ignored acquisition receipts; no credentials were transferred or retained in these reports.
