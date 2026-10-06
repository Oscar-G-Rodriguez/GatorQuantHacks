# H24: Credit Facility Risk Repricing

Status: **prospective economic specification for complete round-2 registration; not yet evaluated**. Drafted October 4, 2026 after the financing development leads were exposed. The [shared complete experiment plan](../../docs/massive/financing-round2-plan.md) and [fixed configuration](../../config/financing-round2.json) form part of this specification and own the numerical and operational settings. Record the actual registration identity in [Research Log.md](Research%20Log.md) after the complete package is committed and before strategy implementation.

## 01 — Summary

A credit-facility disclosure can reveal access to contingent funding and changes in contractual financing risk. The study asks whether the full standard category helps time an option overlay, without treating every facility as drawn cash or every agreement as evidence that risk has disappeared.

Test the exact served `credit_facility` label using two complementary funded-share branches: **covered call** and **protective put**. The primary horizon is ten trading sessions and the target option maturity is 120 calendar days. Measure the net event-versus-ordinary effect, the option overlay beyond its own stock leg and the additional information beyond prior market and option conditions. Both branches are predeclared and remain in the evidence family. Neither an attractive stock return nor a single profitable option establishes the proposed contribution.

The verdict at registration is **not yet evaluated**. The eventual paper must distinguish development evidence from fresh confirmation and retain unsupported or unavailable results.

## 02 — Economic Hypothesis

We expect credit-facility disclosures in the supplied 100-company universe to contain information about the next ten sessions of financing risk because committed borrowing arrangements can change assessments of liquidity access and financing constraints. A company may gain a buffer while also revealing dependence on credit or contractual restrictions. The proposed opportunity persists if headline attention and the interpretation of those financing implications occur at different speeds. A served label does not separately prove actual borrowing, lender performance, sufficient liquidity or new public information.

**Covered-call branch.** If disclosed borrowing arrangements make funding availability more predictable, residual uncertainty can fall while investors still value calls against a broader previous risk estimate. The covered-call branch tests whether selling upside optionality against funded shares earns an unusual net increment over matched ordinary-date calls. Call buyers seeking leveraged upside and risk transfer are the proposed other side. This branch does not assume that a larger facility mechanically increases equity value.

**Protective-put branch.** If the disclosure instead reveals tighter constraints, greater reliance on external funding or unresolved refinancing risk, a put can offer protection against downside that has not been fully reflected in its premium. The protective-put branch tests that possibility across the entire credit-facility cohort and against the same ordinary-date protection and unhedged-share baselines. Put sellers and liquidity providers accept contingent losses for compensation. The proposed persistence is uneven interpretation of liquidity and constraint information, not known lender behavior.

**Testable prediction.** The covered-call prediction is a positive net event-versus-ordinary overlay contrast consistent with more predictable residual risk. The protective-put prediction is a positive net protection contrast under its separately fixed criterion. Report the two branches together; access to credit and dependence on credit are competing explanations whose option consequences must be measured.

**Falsification.** The mechanism fails if the facility category adds no information beyond prior market and option prices, if the benefit is ordinary short-option carry or market exposure, or if feasible lag and friction consume it. A put gaining during one stressed issuer is insufficient when premiums across the full hedge program are charged. The standard label's heterogeneity may make both branches inconclusive or unsupported.

The two branches do not predict that every financing is simultaneously safe and dangerous. They register distinct option-tail implications for the complete category before new option-program results are inspected. Their counterparty and persistence descriptions are proposed mechanisms, not facts established by these data.

## 03 — Data & Universe

Use the supplied static 100-company universe, exact pinned Massive categories and 2022-01-01 through 2025-12-31 development history, subject to actual account coverage. Required financial observations are Massive API disclosures, contract reference, nominal stock prices, option prices and available quotes, with corporate-action metadata and the fixed exchange-session calendar. Software and cited methodological sources do not substitute for market data.

H21 retained 154 distinct credit-facility filings across 55 issuers in 2022–2025. The exposed example concerns absolute return over ten sessions with zero extra input delay. Source support does not establish executed trades, drawn funding or favorable option prices.

An agreement, amendment, extension or commitment remains eligible when the pinned taxonomy serves the credit-facility label. The rule does not infer receipt of money from that label and does not require particular wording, drawdown evidence or a favorable reading of the excerpt.

Preserve CIK/accession identity, the category hierarchy, exact excerpt provenance, separate same-date filings and share-class mappings under the shared plan. Report source filing counts, usable issuer/session activations, option-supported observations, complete comparisons and executed trades separately. Keep failures, missing/stale marks, unresolved mappings and unknown cash flows visible. The retrospective universe has selection and survivorship concerns.

All 2022–2025 is previously exposed development history. The previously viewed 2026 period cannot supply an untouched OOS result for this study. Do not extend outcomes into 2026 to complete development targets. The sealed organizer interval remains inaccessible to development; any genuinely unseen confirmation must use a frozen pipeline and explicitly recorded evidence.

## 04 — Methodology

The complete shared plan fixes event deduplication, feasible availability/decision/fill clocks, contract selection, option prices and mark quality, entry/exit accounting, ordinary controls, component comparisons, chronological fitting/purge, uncertainty, search family, exact practical thresholds, risk limits and all registered sensitivities. Apply its configuration unchanged to this folder. A missing consequential field in that shared package must be resolved before the registration commit and strategy code; this brief is not permission to choose it from results.

The common construction buys 100 actual funded shares and either sells one approximately 5% OTM call or buys one approximately 5% OTM put, targeting 120 calendar DTE. The primary exit is ten trading sessions after feasible entry. Keep stock, option, dividend, financing, cost and exercise/assignment contributions separate. Charge protection on every entry and retain the covered call's stock downside and capped upside.

Apply the same fixed eligibility, contract, clock, cost and capital conventions to event trades and matched ordinary dates for the same issuers. The stock-only counterpart uses the same stock observations. Compare the event-versus-ordinary option contrast with the stock-only contrast, prior-price/option information and the registered ablation/component tests. For H25, the shared component contrast is mandatory; conjunction performance must add beyond debt issuance and underwriting rather than repeat their contribution.

Report all sponsor horizons 1, 2, 3, 5, 10, 21, 42 and 63 sessions, plus expiry when observable, under the fixed missing-outcome policy. Keep the primary horizon fixed. Maturity, strike, extra-delay and doubled-cost neighbors follow the declared shared grid and remain diagnostics rather than a new winner search. Fit any forecast, transformation or matching scale only on eligible earlier training data with outcome overlap purged from later validation.

The shared plan fixes S01–S12, eleven variants per study, and a joint 19-estimand primary family before implementation. Covered-call advancement tests net overlay and strategy increments. Protective-put advancement tests net downside reduction, additional hedge benefit beyond ordinary-date protection and bounded average return drag; it is a protection claim rather than automatic alpha. H25 also tests both component contrasts. Apply the shared support, simultaneous-bound, calibration and two-block-length gates exactly. A planned check is pending until its measured evidence returns; this adjustment cannot erase earlier adaptive exposure.

## 05 — Results and acceptance

No H24 strategy P&L, trade count, Sharpe ratio, drawdown or hypothesis-specific option comparison exists at this registration checkpoint. H21's prior stock forecast improvements do not provide these quantities. Exposure commit `1d531db17acc3cd6f0df6cebdb2ff503b0d40b95` records that all displayed financing examples had Romano–Wolf p=1 at both block lengths in every year. Their full-feature-group comparison does not isolate the selected label or establish the H25 interaction beyond components.

The shared plan fixes branch-level practical effect, sample support, uncertainty, search treatment and rejection criteria before implementation. Report every branch against those criteria on consistent observations. Inadequate option/control/support evidence is **INCONCLUSIVE**; fulfillment of a fixed failure condition is **REJECTED**; a familiar stock/option exposure explaining an apparent benefit is **EXPLAINED**. A development candidate remains pending genuinely unseen confirmation and cannot receive the final **SUPPORTED incremental signal** verdict merely because a historical program made money.

The paper's results section must report net strategy and baseline tables, observable horizons and counts, uncertainty, exposure and search history, measured curves, double-cost and delay outcomes, exclusions and integrity statuses. Missing or unrun metrics receive explicit reasons, not invented values or zeros.

## 06 — Risk Management

Both branches own funded equity risk. The covered call caps upside while retaining substantial stock downside; the protective put pays a premium and supplies protection only under its actual contract, expiry and exercise conditions. Neither branch uses naked option exposure or assumes that a price stop guarantees a fill through a gap.

Use the shared fixed position, issuer/sector, gross/net and overlapping-event limits, funding/cash conventions and de-risking/re-entry policy. Preserve the registered handling of corporate actions, dividends, early assignment, expiry, stock halts and unfillable exits. Unknown facts stay explicit and prevent an executable claim where the shared acceptance gates require them. Report risk on actual deployed capital as well as comparable stock notional.

## 07 — Liquidity & Capacity

Apply the shared quote/bar quality rules, executable-price convention and per-side friction model to every stock and option leg. Daily option trade marks are marked-value evidence; they do not independently prove executable bid/ask fills. Distinguish the registered research-mark approximation from quote-supported execution and record all missing or stale-price exclusions.

Charge the protective premium, covered-call opening/closing obligations and all stock costs and cash flows consistently. Test the fixed doubled-friction and delay scenarios without changing the event definition. Liquidity evidence comes from the thin required leg and actual observed size/volume at the relevant clock; summed daily volume does not establish simultaneous fills or market depth. Dollar capacity remains unestablished until measured liquidity and an adequately supported net increment justify it.

## 08 — Limitations & Next Steps

The idea follows a broad, exposed and statistically unconfirmed development search. Category bundles, common issuers and overlapping horizons create dependence. Label delivery timestamps and prior public announcements remain imperfectly observed. The complete standard category is heterogeneous; neither keyword relaxation nor a standard taxonomy establishes mispricing.

Commit this complete folder specification together with the shared plan and fixed settings before code. Implement the registered diagnostics and funded programs locally, acquire and package private inputs on the PC, transfer by verified hashes, run real studies through scheduled HiPerGator allocations and verify the returned evidence before interpreting it. Then prepare an individual eight-section paper using the prior five-page, 11-point layout, showing the measured conclusion even if null, failed or inconclusive. Preserve H18–H22, original attempts and the sealed window.

Sources: [recorded H21 stock findings](../H21%20-%20Massive%20Disclosure%20Research%20Atlas/Stock%20Readout.md); [H21 research/exposure log](../H21%20-%20Massive%20Disclosure%20Research%20Atlas/Research%20Log.md); [Massive challenge](../../../Massive%20Track/Challenge%20and%20Rubric.md); [research/trade design](../../../Massive%20Track/Research%20and%20Trade%20Design.md); [Massive taxonomy methodology](https://massive.com/blog/tagging-8-k-disclosures-with-ai-corporate-events-labelled-by-what-actually-happened); [covered-call construction](https://www.optionsplaybook.com/option-strategies/covered-call); [protective-put construction](https://www.optionsplaybook.com/option-strategies/protective-put); [evidence contract](../../docs/BACKTEST_EVIDENCE_CONTRACT.md); [quant-note template](../../docs/QUANT_NOTE_TEMPLATE.md).
