# H22: debt financing resolution and covered calls

Status: **complete development experiment protocol prepared for registration**. Recorded October 4, 2026 after reviewing the October 3 H21 development outcomes. [Experiment Plan.md](Experiment%20Plan.md) fixes the remaining coding, timing, costs, controls, risk, statistics, evidence and execution choices and takes precedence over provisional choices below. Oscar subsequently authorized the HiPerGator backtest; this plan must be committed before strategy code. No H22 backtest result exists at registration.

## 01 — Summary

Test a covered call after a company affirmatively completes a debt financing. A covered call combines a funded long stock position with a sold call on that stock. The proposed contribution is the disclosure-based timing of the option overlay, rather than a claim that covered calls themselves are novel.

The starting specification is a standard call near 120 calendar days to expiry, with a strike approximately 5% above the stock price, held for 21 trading sessions. The question is whether this timing improves net outcomes relative to the same covered call on comparable ordinary dates, after accounting for stock exposure, option prices and execution costs. Verdict: **not yet evaluated**.

## 02 — Economic Hypothesis

We expect completed debt financing in the supplied Massive universe to be followed by less unresolved financing uncertainty over the subsequent month, because receipt of funding can remove uncertainty about whether a planned transaction will close and on what terms. Investors may continue paying for optionality while assessing the company, while a covered-call writer accepts capped upside and continuing stock downside. The proposed persistence mechanism is uneven interpretation of transaction completion and remaining risks. This participant behavior and any mispricing have not been observed in our data.

If the mechanism holds, subsequent option-priced uncertainty should compress unusually relative to matched ordinary periods, and the event-timed covered call should offer an incremental net benefit. Financing can instead increase leverage, fund a risky acquisition or reveal distress. The hypothesis fails if those risks dominate, if ordinary short-option exposure explains the result, or if the price adjustment finishes before the label can be used.

The opportunity is proposed, not established. Better volatility forecasting does not imply lower future volatility, overpriced options, positive stock direction or positive option P&L.

## 03 — Data & Universe

Use the existing supplied 100-company universe and Massive API observations only: versioned disclosure labels and excerpts, historical contracts, nominal stock prices, option bars and suitably timed quotes. Preserve CIK/accession identity, share-class mapping, corporate actions and separate same-day filings. Standard contract strikes must be compared with same-session unadjusted stock prices in the same units.

H21 served 526 `debt_issuance` filings across 87 issuers in 2022–2025: 137 in 2022, 115 in 2023, 115 in 2024 and 159 in 2025. These are filing counts for the broad label, not counts of completed financings or feasible trades. The completion-filtered and option-eligible counts remain unknown. The retrospective universe has survivorship and selection concerns.

All 2022–2025 findings are exposed development evidence. The designated January–August 2026 period was exposed in earlier studies and cannot be fresh confirmation for H22. Preserve the organizer-controlled sealed period; do not infer its dates from starter placeholders. Any later confirmation must identify genuinely unseen evidence and freeze the experiment before exposure.

## 04 — Methodology

The proposed trade rules are:

1. Require Massive's exact `debt_issuance` label and supporting text that affirmatively establishes issuance or closing and receipt of financing, rather than only a proposed offering or an agreement to issue later. An underwriting agreement alone does not qualify. Completion can precede the filing, which must be retained as a possible late-information case. Before implementation, fix a reproducible completion-coding rubric and audit it without option outcomes. Ambiguous text remains unknown. Repeated tags do not prove repeated or new financing.
2. Decide only after the label and all required inputs could have been available. Massive currently describes daily next-load updates; historical delivery timestamps remain unverified. Filing plus one calendar day aligned to a session is an explicit research assumption. A decision using a close fills at the next feasible session price. Never sell at an earlier close or treat a pre-filing entry as executable. Register additional delays of 1, 3 and 5 sessions.
3. Select a standard 100-share call from the historical decision-time chain, using 90–180 calendar DTE and expiry nearest 120. Choose the strike nearest 1.05 times nominal spot, requiring an achieved OTM distance between 4% and 6%. Skip an unsupported contract or unavailable execution price. Do not choose the contract using its later return.
4. For a standalone research trade, buy 100 funded shares and sell one call together. For an overlay study on existing stock, specify the long exposure before the event; do not imply we held shares before a disclosure when we did not. Select one implementation at full registration and keep the capital convention fixed across controls.
5. Close the same stock/call position after 21 sessions. Also retain the sponsor's 1, 2, 3, 5, 10, 21, 42 and 63-session outcomes, and expiry where observable, as predeclared diagnostics. Outcomes extending beyond approved history remain missing. Same-contract early-exit P&L is `100 × [(stock_exit − stock_entry) + (call_entry − call_exit)]`, less all applicable costs and cash-flow adjustments. It is distinct from an option-premium percentage return.

The primary comparison is net event covered-call return minus net covered-call return on matched ordinary dates for the same issuer, using identical entry, expiry, strike and eligibility rules. Match on strictly prior momentum, volatility, volume, market conditions, achieved maturity/moneyness and available option-priced uncertainty. Register the distance, calipers and control-window rule before outcome inspection. A missing served label cannot establish that no economic news occurred on an ordinary date.

Compare both groups with their unhedged stock legs and a price/option-only timing rule. This tests whether the disclosure adds information beyond equity beta, momentum, generic option carry and selling options when premiums are high. A premium proxy is not vendor implied volatility. Decompose the stock and call contributions; lower call premiums alone do not establish a better combined trade.

Before code, the complete experiment registration must fix chronological folds and purge, completion coding, matching, liquidity gates, exact cost accounting, support/power criteria, primary practical effect, uncertainty and multiplicity family, risk limits and the final confirmation route. Map S01–S12 to measured diagnostics. Use the existing year-stratified joint issuer/calendar uncertainty principles where applicable, and retain all tested choices and earlier discovery exposure. The provisional parameter neighbors are sponsor maturity buckets around 30/60/120 days and 3%/5%/10% OTM; they diagnose robustness rather than choose a favorable holdout winner.

## 05 — Results and acceptance

No H22 strategy return, trade count, Sharpe or backtest result exists. H21's all-year positive debt-issuance forecast groups have adjusted p-values near one in the reviewed 63-session results. Those event-conditioned comparisons describe an entire model augmentation on debt-labelled observations, rather than isolating a debt-label contribution. They neither establish this mechanism nor support profitability.

An eventual supported claim requires a practical cost-adjusted improvement beyond matched ordinary covered calls and relevant exposure baselines, defensible uncertainty after the declared search, a consistent mechanism diagnostic, feasible timing and independent confirmation. Insufficient completion/quote coverage means inconclusive. No net increment or failure of the timing/mechanism prediction means rejected; an ordinary option risk-premium explanation must be reported as such. The exact thresholds remain a full-registration choice, not a post-results adjustment.

## 06 — Risk Management

A covered call retains substantial equity downside and caps upside. Completion of financing does not make stock ownership safe. The proposed portfolio is funded, with no naked call or leverage; overlap within an issuer requires one controlled position rather than multiplying accessions into simultaneous trades. Full registration must set name/sector exposure, maximum capital at risk, drawdown de-risking/re-entry and treatment of gaps, halts and unfillable exits.

Register dividends, splits, early exercise/assignment, expiry and deliverable handling. If those cash flows cannot be modelled, restrict and report the eligible subset or retain a mark study without claiming executable portfolio performance. Do not use a price stop as a guaranteed cap on a gap loss.

## 07 — Liquidity & Capacity

Opening sells the call at an executable bid and buys stock at an executable ask; closing reverses those sides. Add justified commissions and extra slippage/impact without counting the quoted spread twice. Financing, dividends and assignment-related cash flows must follow the chosen implementation. The starter's 5%-of-premium haircut is a sensitivity convention, not verified execution evidence. Daily option trade bars can support a marked-value research study, but cannot prove bid/ask fills.

Fresh quotes, positive sizes, contemporaneous stock prices and the thin option leg determine executable eligibility. Missing quotes remain missing; they are not filled from future observations. Fix quote-age, spread and participation limits before backtesting. Begin with one standard contract per event study; report capital and capacity only from measured liquidity evidence. Double the registered friction and test the declared extra delays.

## 08 — Limitations & next steps

The strategy was proposed after a large exposed discovery search. H21's complete 499-search placebo evidence and option-priced comparisons remain unfinished; this brief does not bypass them or relabel development observations as independent confirmation. Completion filtering may sharply reduce the broad filing count, daily label loading can miss fast repricing, and financing may increase rather than resolve risk.

The next concrete step is a coverage audit of completed financings and their feasible option observations, followed by a complete committed economic/execution experiment plan. Any subsequently authorized strategy code and scientific run remain local-code/PC-preparation then scheduled HiPerGator execution, with verified return. H18–H21 and their null or inconclusive evidence remain intact.

Sources: [H21 staged stock evidence](../H21%20-%20Massive%20Disclosure%20Research%20Atlas/Stock%20Readout.md); [Massive challenge evidence and permitted menu](../../../Massive%20Track/Challenge%20and%20Rubric.md); [Massive dataset and availability description](https://massive.com/blog/tagging-8-k-disclosures-with-ai-corporate-events-labelled-by-what-actually-happened); [covered-call construction and risks](https://www.optionsplaybook.com/option-strategies/covered-call); [required signal methods](../../docs/signal-reading/README.md).
