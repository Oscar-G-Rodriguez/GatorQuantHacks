# H18: CEO departures and uncertainty resolution

Internal hypothesis ID: **H18**. Status: **completed round-1 specification; actual registration commit is recorded in the research log after commit**. Drafted October 3, 2026 after reviewing the existing development discoveries. This document follows the eight-section quant-note structure and its economic-hypothesis wording. The original draft-only checkpoint is 094a38a. The completed round-1 protocol supersedes its unresolved operational choices; no pre-discovery claim or finished result is asserted.

## 01 — Summary

The disclosure of a CEO departure may settle a specific leadership uncertainty even while the company remains risky. This study asks whether option-priced uncertainty falls unusually quickly after usable disclosure availability. A covered call is the provisional permitted shape for a later strategy test; its stock exposure must be evaluated separately.

## 02 — Economic Hypothesis

We expect stocks in the Massive development universe with CEO-departure disclosures to show greater reductions in option-priced uncertainty over the first five feasible post-disclosure sessions than comparable ordinary observations, because confirmation can replace uncertainty about whether and how leadership will change. The proposed other side is investors buying protection while evaluating the transition; option liquidity providers supply that protection. The relationship may persist when interpreting a transition takes time and headline attention differs from assessment of its remaining risks. If true, we should see extra premium compression after accounting for stock movement, normal time decay and market volatility. It fails if those controls explain the compression, actual subsequent risk remains elevated, or the change occurs before the disclosure can be used.

The attention, information and counterparty explanations are proposed mechanisms. Participant behavior has not been observed or verified in our data. Alpha would be a possible later finding; it is not the primary question or an assumed result.

## 03 — Data & Universe

Use Massive 8-K records and their filing/context fields, historical option contracts, stock prices and option observations. Begin with the already retained 2024–2025 development history and its frozen identities in the [completed findings](../../docs/discovery/options-final-findings.md). The supplied 100-ticker universe is static and historically selected; it is not point-in-time membership.

Approximately 30-, 60- and 120-day option buckets are available as discovery inputs. Preserve actual expiry, strike, contract identity, deliverables and exclusion counts. The call-plus-put/spot proxy is not measured implied volatility, and a five-session stock target cannot be directly compared with a 120-day option price.

The designated January–August 2026 OOS and organizer-controlled sealed window remain outside development. Exact first-announcement and historical vendor-label delivery times are unresolved. Do not describe filing-date assumptions as verified availability.

## 04 — Methodology

The primary research outcome is the five-session change in option-priced uncertainty for the same selected contracts. A summed call/put premium change is an initial diagnostic; a defensible repricing measure must account for underlying movement, remaining maturity, achieved moneyness, rates and dividends.

Compare CEO-departure anchors with eligible ordinary observations for the same issuer, using a declared past-only matching rule. Include a price-only expected repricing baseline. Preserve the existing 84-session-prior controls as historical discovery; they do not automatically supply calendar-matched causal controls for this draft.

Compression should occur after usable information availability, exceed ordinary decay under comparable price conditions, and appear across issuers. A pre-filing change or a result supplied by one issuer weakens the proposed mechanism.

Use chronological development comparisons, fit transformations and thresholds on earlier observations only, and separate folds for overlapping outcome windows. Report event, issuer and date counts, missing/excluded observations, dependence-aware uncertainty, issuer concentration and all attempted choices. Eligibility must be determined from information available at the observation, without requiring future option marks for inclusion in a stock-outcome cohort.

The five-session mechanism focus does not replace Massive's fixed reporting horizons: 1, 2, 3, 5, 10, 21, 42 and 63 sessions, plus expiry where observable. Record unresolved exits with reasons. Keep pre-filing diagnostics separate from a feasible post-availability decision. Additional 1/3/5-session delays are sensitivity questions, not evidence of the actual delivery clock.

### Completed round-1 experiment specification

Funded synthetic long plus short 5% OTM call; five-feasible-session price/decay-controlled premium compression and event-minus-ordinary overlay increment. Primary portfolio settings are the 90–180-day bucket nearest 120 days, 5% OTM, and filing-session exit offset 5. Separate mechanism targets use five feasible holding sessions.

The complete [round-1 protocol](../../docs/massive/mechanism-round1-plan.md) and [settings](../../config/mechanism-round1.json) are mandatory parts of this hypothesis specification. They fix the conditional vendor clock, selection, all required horizons, controls, estimators and criteria, six-primary-family uncertainty, chronological prediction, S01–S12 methods, costs/risk/capacity, jobs and final freeze. Read them before acquisition or implementation. Unknown empirical facts remain explicit evidence gates, with no assumed successful availability. PC acquisition/correctness checks precede immutable Blue transfer; scientific estimates and replay use scheduled HiPerGator jobs. This completed plan must be committed before code or the first backtest.

## 05 — Results

**October 3 post-run update:** the registered experiment completed with an **INCONCLUSIVE** verdict. See [verified results](Results.md). The final run is a documented corrective replay after exposure. The statements below describe the original registration-time evidence boundary.

**This hypothesis has not been evaluated.** H14's selected early CEO event-minus-ordinary premium contrasts were negative, but their uncertainty intervals included zero and later observation times changed the sign. These are development-selected diagnostics of paired premiums. They did not measure the proposed covered-call payoff or establish abnormal compression after all price controls.

Existing selected discoveries informed this draft and remain part of its search history. They are not independent confirmation. The actual registration hash is logged after the completed plan commit exists. New statistical outcomes, net returns and OOS results are absent at registration.

## 06 — Risk Management

A covered call retains substantial stock downside and caps upside. Premium compression alone cannot establish improvement of the whole position. A later plan must specify stock versus synthetic implementation, assignment/dividends, collateral/financing, concentration limits, capital, maximum loss and de-risking. Compare with unhedged stock and the same covered-call process on ordinary dates.

Round 1 fixes $1,000,000 capital, one standard-contract unit, full strike reserves, 5% name/20% unknown-sector/40% gross reserve limits, and the shared protocol’s drawdown/re-entry rules. Historical availability and dividend/assignment evidence remain unresolved support gates. No live orders are part of this study.

## 07 — Liquidity & Capacity

The existing quote audit covers primary-maturity pre-event observations only. It does not establish post-disclosure executable prices or capacity. A later separately specified acquisition must resolve each required leg's freshness, spread, timestamp alignment, available size and actual execution window.

Round 1 fixes bid/ask-side execution, $0.65 per contract per side, 1 premium-basis-point adverse slippage, all synthetic/overlay legs, doubled costs, extra delay, and participation/impact scenarios. These are declared research scenarios awaiting observed quote evidence; no calibrated tariff or established dollar capacity is asserted.

## 08 — Limitations & Next Steps

Round 1 now fixes the estimator, timing scenario, matching, support/search, shape, costs, capital/risk, capacity and method coverage in the linked protocol. Historical vendor availability, approximate parity, dividends/assignment, static-universe selection and sparse groups are empirical limitations to retain. H20 requires verified incoming-person terms and complete-filing absence evidence; unknown text cannot be a negative group.

Commit the completed specification before new data/methods/code, record its actual hash, then implement and verify the declared evidence package. Freeze development choices before one final evaluation. A missing criterion remains pending; a failed or inconclusive result is retained. Later improvements require a versioned amendment and preserve this round’s history.

## References

- [Required note format](../../docs/QUANT_NOTE_TEMPLATE.md) and [hypothesis wording](../../README.md#register-the-economic-hypothesis-first).
- [Massive challenge](../../../Massive%20Track/Challenge%20and%20Rubric.md), [strategy library](../../../Massive%20Track/Options%20and%20Strategy%20Library.md), [research/trade design](../../../Massive%20Track/Research%20and%20Trade%20Design.md), [timing and starter limitations](../../../Massive%20Track/Code%20Review%20and%20Evidence%20Limits.md), and [configuration/horizons](../../../Massive%20Track/Setup%20and%20Configuration.md).
- [Completed discovery findings](../../docs/discovery/options-final-findings.md), [earlier follow-up](../../docs/discovery/followup-findings.md), [signal-testing guide](../../docs/SIGNAL_TESTING_GUIDE.md) and [required signal methods](../../docs/signal-reading/README.md).
