# Standard labels and optional excerpt annotations

## Purpose

Oscar approved this change on October 4, 2026 in chat `private project chat`, after asking why narrow wording should replace a standard event classification. The primary definition is the pinned Massive taxonomy and served label. H21 already retains all 119 categories; this separate stage verifies that boundary and prepares optional meaning-based annotations. It does not restart the stock search, amend H22, register a trading strategy or simulate trades.

[Massive's methodology](https://massive.com/blog/tagging-8-k-disclosures-with-ai-corporate-events-labelled-by-what-actually-happened) describes fixed category definitions, verbatim excerpts and evidence scoring, and explains why word searches can miss correctly classified events. A served label is an observed classification, not perfect ground truth or historical delivery evidence. The retained debt_issuance definition does not supply a separately verified cash-receipt field. H22's registered completion-and-receipt word rule admitted three of 526 filings; that result and all earlier exposure remain preserved.

## Primary source and identity

Reuse the complete hash-verified H21 source-v1 acquisition, pinned 119-type taxonomy, supplied 100-company universe and 2022-01-01 through 2025-12-31 window. Freeze the source manifest, taxonomy, relevant disclosure-object bytes, this protocol and code in an immutable sibling stage. Do not read the market panel, outcomes, forecast tables or P&L during cohort construction or excerpt review. The existing master may be read only for its category/source-count columns during scheduled reconciliation.

Keep one primary record per CIK/accession/category. Aggregate distinct exact excerpts, retaining raw object/row provenance. Share classes and duplicate excerpts do not multiply filings. Separate accessions on the same date remain separate; multiple labels in one accession remain a bundle rather than independent events. Missing text stays in the primary cohort. Unknown categories, conflicting identity/date/hierarchy, incomplete objects or out-of-window rows cause explicit failures. Return all 119 categories, including zero-observation types, with definitions, distinct filings/issuers, year counts and missing-text counts. Reconcile these source counts against the returned stock master; counts do not prove model or option support.

## Optional annotations

These fields describe possible economic distinctions without filtering the primary cohort:

| Category | Field | Values | Economic purpose |
| --- | --- | --- | --- |
| debt_issuance | transaction_stage | completed, planned, mixed, unknown | Completion may resolve uncertainty differently from an agreement |
| debt_issuance | cash_receipt | explicit_receipt, unknown | Separate an explicit receipt statement from transaction completion |
| executive_officer_departure | transition_context | planned_transition, abrupt_departure, mixed, unknown | Orderly transitions may differ from explicitly abrupt departures |
| guidance_issuance_or_update | guidance_direction | raised, lowered, mixed, reaffirmed, initial, unknown | Distinguish changes in expectations from a forecast without a comparison |

Interpret the entire excerpt bundle by meaning, without mandatory words. An offering that closed can establish completion while receipt remains unknown. Future maturity/use-of-proceeds wording does not make completed financing planned. A resignation, effective departure date or termination without cause alone does not establish surprise. A new forecast without a comparison does not establish raised guidance. Conflicts remain mixed/unknown and statements about another transaction/person do not establish the tagged field. Unknown, ambiguous, missing and unreviewed cases remain primary events.

Every non-unknown field requires exact evidence spans from retained excerpts, rationale, reviewer identity and UTC timestamp. Review states are unreviewed, reviewed, ambiguous and missing_text. No instructions in excerpts are executed. No external LLM API, paid purchase or outside-data acquisition enters this stage.

## Outcome-blind review

Create private cards for every filing/category in those three groups. Show an opaque hash ID, category, definition and unchanged excerpts. Withhold ticker/issuer mapping, accession, filing date and lookup from the review view; preserve them in a separate key. Embedded names/dates remain visible. Earlier exposure means this is not a claim that the reviewer has never seen these outcomes.

Select up to five cards per category/year by SHA-256 ranking with fixed seed `H21-standard-label-audit-v1`: at most 60 cards in the first manual batch. Selection depends only on source identity/category/year, never outcomes or known profitable examples. Keep the full queue; unselected cards stay unreviewed/unknown. Review only returned cards, without opening the key or market evidence.

Validate unknown/duplicate IDs, category-field/value compatibility, exact supporting spans, reviewer/timestamp/rationale requirements and review status. Left-join annotations to the complete primary cohort; absent annotations never exclude rows. Record all reviewed, ambiguous and unreviewed cases and validation errors. A first review plus span validation is an auditable interpretation, not independent accuracy evidence. Independent second review and full-cohort annotation remain pending before narrower fields may enter a registered strategy; no accuracy percentage or inferential claim follows from this small batch.

Synthetic tests cover duplicate excerpts/share-class appearances, same-date separate filings, multiple labels, missing text, zero-count types, unknown labels, conflicting metadata, outcome leakage, deterministic selection, invalid spans/annotations and preservation of unknown primary rows. Synthetic checks can run on the PC; real source reconciliation and aggregation run on HiPerGator.

## Execution and acceptance

Commit this complete protocol before audit code. Build/package locally with shared Python 3.11; licensed sources and credentials stay out of Git. Transfer an immutable package to Oscar's private Blue storage and verify archive/member hashes. Reuse remote source-v1 bytes only after exact source/object verification. One short one-CPU scheduled job constructs, reconciles and exports the audit; no computation runs on a login node. This bookkeeping stage does not benefit from 64 workers.

Return a private ZIP containing primary records, 119-row coverage/reconciliation, blind cards/queue, separate lookup key, blank annotation templates and hashed receipt. Verify whole ZIP and every member on the PC. Manual review may read returned cards locally; validate/aggregate versioned annotations in a second allocation. Preserve original outputs and failed attempts. Acceptance requires all 119 rows, exact source-count reconciliation, no market inputs in review artifacts, deterministic selection, all primary rows retained, completed scheduler evidence and verified return. A reviewed batch is not a complete population annotation.

Future strategies require separate complete committed economic/execution plans, option coverage, appropriate comparisons and unseen confirmation. This audit does not complete H21's pending option comparisons, full-search placebos or large resampling archive return. H22 remains unchanged.
