# Financing round2: verified pilot findings

The three registered financing hypotheses now have actual HiPerGator backtest outputs on the PC. The result is **INCONCLUSIVE**: the pilot demonstrates the data, funded-share accounting and evidence-return workflow, while its paired samples and failed statistical calibration prevent a strategy or alpha conclusion.

This snapshot uses the return verified on2026-10-04 at14:44:48 UTC. Its whole-archive SHA-256 is `a923f46a7dfc33d6bda51c183c0b93de0a99596ef2b9b9a78eaaf5ebb76dda90`; all177 members were verified. The registration commit is `b4159e2917248d588072ef5d9ae55bd88c3f8063`, which preceded the executed code commit `51331e7f24dd23397a6504de7407c4c8d239c060`. The frozen run manifest is `2f1dc336455036a3b2ca09ae38f44b90df2d59a6e83ed4ec76d4144ce46f5740`.

## What actually ran

The scoped pilot ran H23 debt issuance, H24 credit facilities and H25 same-filing debt issuance plus underwriting. Both the covered-call and protective-put shapes used actual funded shares, observed historical daily-price proxies and stated transaction costs. The primary holding period was ten sessions; all registered diagnostic horizons and supported expiry outcomes were retained. H23 also ran the doubled-cost variant. These are four completed pilot tasks out of the33 tasks in the full study.

All four array tasks `44693324_0` through `44693324_3` completed with exit code `0:0` in13–14 seconds each. Calibration job `44693325` completed in1:45, analysis job `44693326` in8 seconds, and export job `44693327` in6 seconds. The retained scheduler observation and individual scientific receipts preserve their different scheduler and child-job identifiers. Successful scheduler completion verifies execution; it does not establish scientific support.

## What the results support

The primary comparisons require an event strategy, event stock-only alternative, earlier ordinary-period strategy and ordinary stock-only alternative for the same issuer, with matching option characteristics and aligned evaluation clocks. This stricter comparison leaves very few observations in the deliberately small pilot.

| Hypothesis | Covered-call versus ordinary | Protective-put versus ordinary | Additional comparison | Evidence status |
|---|---|---|---|---|
| H23 debt issuance |1 pair across1 issuer|2 pairs across1 issuer|Doubled costs ran as a fixed sensitivity|Insufficient support|
| H24 credit facility |2 pairs across1 issuer|0 complete pairs|Missing put comparisons remain explicit|Insufficient support|
| H25 debt plus underwriting |2 pairs across2 issuers|2 pairs across1 issuer|0 supported debt-only or underwriting-only component pairs|Insufficient support|

The registered requirement is at least30 complete pairs across eight issuers overall. These pilot counts are copied from the verified summaries, rather than estimated from the raw objects. Return-complete and downside-path-complete samples remain separate. Missing outcomes were not replaced with zero, and standard Massive labels were not screened by narrow excerpt wording.

The statistical correction also failed its synthetic calibration. With100 artificial null datasets, the method produced45 false family rejections for63-session blocks and72 for126-session blocks; the registered maximum was10. These artificial datasets test whether the method can produce an apparent finding when no signal exists. This failure means its adjusted uncertainty estimates are suppressed for the empirical study. It does not show that the observed disclosures have no value, and it cannot be repaired by presenting an unadjusted p-value as confirmation.

## What remains incomplete

The full-cohort acquisition and remaining registered variants are outside this completed pilot. The exact shifted-source timing searches have0 of199 completed replications. Bounded quotes provide partial execution-price evidence, while daily closing fills, assignment and slippage remain modeled conventions. Risk-matched SPY, prior-momentum and broad-universe funded benchmarks still need the missing numerical policy decisions recorded in the task evidence. The previously examined development years and2026 history provide no fresh final confirmation period.

The next useful calculation is the complete registered cohort after its source acquisition is verified, accompanied by a corrected and newly frozen statistical calibration implementation. Preserve this pilot as an earlier exposed attempt; do not overwrite it or call the same history unseen. Positive individual profits or favorable point estimates in these sparse cells do not establish alpha.

## Delivered evidence

Each folder contains unchanged study summaries, validation checks, performance and baseline tables, actual unit trades, daily NAV, diagnostics, exclusions, job receipts, provenance and a per-study trial ledger:

- [H23 pilot results](../../Hypotheses/H23%20-%20Debt%20Issuance%20Option%20Repricing/results/financing-round2-pilot-v1/summary.md).
- [H24 pilot results](../../Hypotheses/H24%20-%20Credit%20Facility%20Risk%20Repricing/results/financing-round2-pilot-v1/summary.md).
- [H25 pilot results](../../Hypotheses/H25%20-%20Debt%20Underwriting%20Interaction/results/financing-round2-pilot-v1/summary.md).

`evidence_manifest.json` in each result directory maps every copied scientific member to its original path and SHA-256. The copy helper [package_financing_pilot_evidence.py](../../scripts/package_financing_pilot_evidence.py) re-verifies the imported return and records the four actual attempts in [EXPERIMENTS.csv](../../Hypotheses/EXPERIMENTS.csv). Existing trial rows are preserved byte for byte. The delivery contains derived results and receipts; raw provider objects, supporting excerpts and credentials remain in the private cache.

Read the [registered plan](financing-round2-plan.md) and each `validation_checks.json` together with the performance tables. The machine verdict is `UNSUPPORTED_FOR_CONFIRMATORY_CLAIM`; the research conclusion remains **INCONCLUSIVE**.
