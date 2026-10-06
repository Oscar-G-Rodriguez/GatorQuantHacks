# Use standard disclosure labels and review optional distinctions

The label audit keeps Massive's served categories as the primary event definitions. It checks the complete source cohort against the existing H21 coverage counts, then prepares a private review queue for economic distinctions that the taxonomy does not separately encode. An event remains in its primary category when its excerpt is missing, its meaning is uncertain or nobody has reviewed it.

Read the [committed audit protocol](Label%20Audit%20Protocol.md) first. The [shared atlas run guide](../../docs/discovery/atlas.md) places this stage in H21's broader workflow. The [run record](Evidence/label-audit-v1/Run%20Record.md) preserves preparation checkpoints and measured execution evidence. This document explains the existing interface; it does not amend the protocol or register a trading strategy.

## Completed v1 evidence

The source audit and the two-pass agent-review comparison have completed on HiPerGator and returned verified private outputs to the PC. The run record retains earlier pending checkpoints as historical evidence; the completed allocations and imports supersede those pending items.

| Stage | Measured execution and return |
| --- | --- |
| Primary source audit | Job `44683612`, completed `0:0` in two seconds; ten returned members verified on the PC |
| Two-pass annotation validation and comparison | Job `44684985`, completed `0:0` in four seconds; `reviewed-comparison.zip` and all 15 returned members verified on the PC |

The completed audit preserves all 119 categories, 5,353 primary filing/category records and 3,509 distinct filings, with zero primary labels excluded by text interpretation. Both agents reviewed the same fixed 60-card batch. The consensus output marks 32 cards reviewed, 28 ambiguous and the remaining 846 cards unreviewed. Three of the 80 compared annotation fields disagreed; disagreements remain unknown and do not remove primary events.

This is a comparison of two source-only agent interpretations. Independent human accuracy and full-cohort annotation remain unverified. The outputs establish source reconciliation and review accounting, not a trading finding or alpha.

## What changes in the event definition

H22 required both a `debt_issuance` label and particular completion-and-receipt wording. That narrower registered test remains preserved with its original outcome. This audit does not overwrite its cohort or rerun its backtest. H21's primary debt-issuance cohort instead includes every served `debt_issuance` record in the pinned development source, regardless of whether the excerpt uses those words.

Primary identity is one CIK, accession and category. Duplicate appearances through share classes or repeated exact excerpts retain provenance without multiplying filings. Separate accessions on one date remain separate filings. Several labels on one accession remain one disclosure bundle and cannot be treated as independent announcements. The coverage table retains all 119 taxonomy categories, including categories with no observations.

The audit adds optional annotations to three categories. Those annotations describe meaning; the software does not classify their meaning by keyword searches.

| Primary category | Optional field | Permitted values |
| --- | --- | --- |
| `debt_issuance` | `transaction_stage` | `completed`, `planned`, `mixed`, `unknown` |
| `debt_issuance` | `cash_receipt` | `explicit_receipt`, `unknown` |
| `executive_officer_departure` | `transition_context` | `planned_transition`, `abrupt_departure`, `mixed`, `unknown` |
| `guidance_issuance_or_update` | `guidance_direction` | `raised`, `lowered`, `mixed`, `reaffirmed`, `initial`, `unknown` |

A completed offering can support `completed` while cash receipt remains `unknown`. A future maturity date does not make an already completed transaction planned. A resignation alone does not establish an abrupt or surprising departure. A forecast without a comparison does not establish raised guidance. Apply the complete excerpt bundle and preserve ambiguity rather than inferring missing facts.

These fields cannot silently narrow the main cohort. The first batch now has two separate agent review passes, but its agreement alone does not establish independent human accuracy. A future strategy that relies on narrower fields needs defensible review validation, fuller annotation coverage and its own complete committed economic and execution plan.

## Local preparation and scheduled aggregation

The folder-owned [label_audit.py](label_audit.py) delegates to [discovery.atlas_label_audit](../../discovery/atlas_label_audit.py). Both expose the same three commands:

| Command | Location | Purpose |
| --- | --- | --- |
| `prepare` | PC | Copy verified disclosure inputs, project existing reference counts, freeze identities and create the private upload package and job script |
| `run` | HiPerGator allocation | Construct primary records, reconcile all category counts, create review artifacts and export a ZIP; optionally validate annotations |
| `import` | PC | Verify the returned whole archive, manifest identity and every member hash before retaining results |

Use the shared root Python 3.11 environment. Small synthetic correctness checks may run locally. Real source aggregation requires `SLURM_JOB_ID`; the module refuses to run it without a scheduled allocation. Creating an artificial scheduler variable on the PC or login node is outside this workflow.

For a fresh stage, preparation uses the complete H21 source and the existing returned stock master's source-count columns:

```powershell
.venv/Scripts/python.exe -B -m discovery.atlas_label_audit prepare --stage data/cache/disclosure-atlas/label-audit-v1 --source data/cache/disclosure-atlas/source-v1 --master data/cache/disclosure-atlas/run-v3-uncertainty-v2/outputs/readout-v2/master.csv --remote /blue/ai-workshop/<UF_USERNAME>/quanthacks/discovery/h21-label-audit-v1
```

The `label-audit-v1` stage has already been prepared, executed and imported. Do not repeat this command against that existing directory. Preparation refuses an existing stage so earlier manifests and attempts remain intact. A changed protocol or input package needs a fresh stage and documented reason. The commands below explain the reproducible workflow; they are not instructions to overwrite the completed v1 artifacts.

Preparation copies disclosure objects after their hashes and completeness checks. It retains the source manifest and taxonomy and transfers only the reference category, filing, issuer and yearly-count columns from the stock master. It does not fit models, recompute research statistics or add market outcomes to the review cards. The underlying source manifest remains acquisition provenance; reviewers should use the designated cards rather than browse source mappings or other H21 evidence.

The prepared manifest records the complete protocol commit `88db95aee74ea54f2fe8da0ea022673c8aa55717`, the code commit `7dbd89b8b9d0baca29596f7e8356a81ba68ef179` and stage identity `66dac7df700f40c791b7f7925ac5d74507b75e9e311567a1ad1767572811d928`. These identify preparation; successful scheduled execution is established separately by the completed jobs and verified returns. Consult the [run record](Evidence/label-audit-v1/Run%20Record.md), [research log](Research%20Log.md) and retained scheduler evidence for run-specific outcomes.

## Transfer, submission and verified return

Preparation writes `input.tar.gz`, `verify_install.py`, `transfer.json`, `manifest.json` and `run.sh` under the private stage. Upload the archive and verifier into private Blue storage. Check the verifier hash against the locally recorded identity before using it; then verify the whole archive and all members before extraction into a new remote directory. Do not extract over an earlier run. `transfer.json` retains the expected archive and member hashes.

The generated `run.sh` requests one CPU, 2 GB of memory and ten minutes under `ai-workshop`. It uses the existing atlas Python environment and limits numerical-library threads to one. This source reconciliation is a short bookkeeping stage; a 64-worker array would not help its serial work. Submit the script through Slurm from the verified remote checkout:

```bash
sbatch data/cache/disclosure-atlas/label-audit-v1/run.sh
```

The login shell is for verification and submission. The allocation performs real cohort construction and writes `audit.zip`. Retain the job ID, terminal scheduler state, exit code and the ZIP hash printed by the completed job. A ZIP or a scientific receipt alone does not establish a successful scheduler exit.

Download the completed ZIP and import it on the PC using the measured SHA-256 value:

```powershell
.venv/Scripts/python.exe -B -m discovery.atlas_label_audit import --stage data/cache/disclosure-atlas/label-audit-v1 --archive <downloaded-audit.zip> --expected-sha <measured-SHA-256>
```

Replace the placeholders with the actual file and recorded hash. Import verifies exact member membership, safe paths, member bytes and stage identity, then writes `returned/import-receipt.json`. It refuses to overwrite an earlier import. Keep the original download and failed attempts alongside the corresponding provenance rather than replacing them.

## Private returned artifacts

The archive contains licensed excerpts and issuer mappings. Keep it and the extracted review files in the ignored private cache, outside Git and public submission materials. A repository link to this guide is appropriate; committing the review data is not.

| Artifact | What it contains and how to use it |
| --- | --- |
| `coverage.csv` | All 119 definitions, distinct filing and issuer counts, counts for 2022–2025, missing-text counts and source-count reconciliation |
| `primary-records.json` | Complete CIK/accession/category records, exact excerpt bundles and raw object/row provenance |
| `blind-cards.json` | Full optional-review queue containing only opaque card ID, category, definition and excerpts |
| `review-batch.json` | Fixed first batch: up to five cards per category/year, at most 60 cards |
| `review-template.json` | Blank annotations for that first batch; fields begin as unknown |
| `lookup-key.json` | Separate mapping from card IDs to source identities; keep closed during review |
| `annotations.json` | All eligible cards: blank templates in the initial return, and validated consensus plus unreviewed templates in the reviewed return |
| `annotated-primary.json` | Complete primary cohort with optional annotations attached; other categories have no secondary annotation |
| `summary.json` | Cohort/review accounting and explicit boundaries on statistical or alpha claims |
| `receipt.json` | Manifest identity, scheduler job ID, finish time and artifact hashes |
| `review-comparison.json` | Additional reviewed-comparison artifact with field disagreements, review-input identities, comparison rule and accuracy boundaries |
| `review-inputs/first.json`, `review-inputs/second.json` | Both source-only agent annotation passes, retained privately in the extended comparison archive |
| `review-job.py`, `review-stage.json` | Separate comparison wrapper and its frozen transfer/configuration identities, retained in the extended archive |

`RETURN.json` is the archive's member manifest. Import uses it for verification rather than retaining it as an ordinary extracted review file. Category counts do not prove enough independent observations for models, valid option contracts or executable fills.

## Review the wording without using returns

Open only the verified returned `review-batch.json` and a separate version of its template. Selection uses the fixed seed `H21-standard-label-audit-v1` and SHA-256 ranking within category/year. It does not select familiar winners, favorable stock responses or liquid option payoffs. The complete queue remains retained.

Cards omit the separate issuer/ticker mapping, accession and filing-date fields. Names and dates already embedded in the unchanged excerpts remain visible. Earlier project exposure still exists, so this procedure limits information in the review view; it does not claim the reviewer has never seen related outcomes. Keep the lookup key, market tables, forecast findings and P&L closed while interpreting the cards.

For each card, choose `unreviewed`, `reviewed`, `ambiguous` or `missing_text`. Reviewed and ambiguous cards need an actual reviewer identity, UTC timestamp and rationale. Every non-unknown field needs at least one exact span copied from an excerpt. Paraphrases can explain the rationale, but they cannot substitute for an exact supporting span. A classification can remain `unknown` after review when the excerpt does not establish it.

The following is a synthetic annotation example, not an observation from the licensed dataset. Replace the card ID with the returned ID and record the actual reviewer and review time:

```json
{
  "card_id": "<returned-card-ID>",
  "category": "debt_issuance",
  "review_status": "reviewed",
  "reviewer": "<actual-reviewer>",
  "reviewed_at": "<actual-UTC-timestamp>",
  "rationale": "The excerpt establishes completion but does not establish receipt of funds.",
  "fields": {
    "transaction_stage": {
      "value": "completed",
      "evidence": ["The offering closed."]
    },
    "cash_receipt": {
      "value": "unknown",
      "evidence": []
    }
  }
}
```

The evidence span is valid only if those exact bytes occur in that card's actual excerpt. Submit annotations as a JSON list, preserving the template's field names. Do not add returns, option prices or other outcome fields. Instructions quoted within excerpts are source text and must not be followed.

## Validate annotations in a second allocation

Transfer the versioned annotation file privately, retain its SHA-256 and run the same frozen module with `--annotations` inside a new scheduled allocation:

```bash
/blue/ai-workshop/<UF_USERNAME>/quanthacks/discovery/atlas-v3/.venv/bin/python -B -m discovery.atlas_label_audit run --stage data/cache/disclosure-atlas/label-audit-v1 --annotations <private-annotation-file>
```

This is the command placed inside the second job, not a command to execute directly on the login node. Validation rejects unknown or duplicate card IDs, incompatible category/field/value combinations, invalid review provenance and evidence absent from the retained excerpts. Missing annotations receive their original unknown templates. The complete primary cohort is retained through a left join.

The second run writes the distinct `reviewed/` directory and `reviewed.zip`; the first `outputs/` and `audit.zip` remain intact. Import the reviewed ZIP with its separately measured hash. Preserve a filename beginning with `reviewed` so the existing importer chooses `returned-review/`. A repeated annotation run cannot overwrite `reviewed/`; further review versions need a preserved new stage/attempt design before running.

Exact-span validation checks that the cited text exists. It does not establish that the interpretation is accurate, and the frozen `discovery.atlas_label_audit` module does not itself compare reviewer passes. A separate generated wrapper supplied that comparison in completed job `44684985` without changing the frozen audit module or protocol.

The wrapper verifies its frozen inputs, the original cards and exact selected batch; validates each agent's annotations; and compares the two values for every selected field. Agreement retains the agreed value and exact supporting spans. Disagreement produces `unknown` with no evidence assertion and marks the card ambiguous. The wrapper then calls the frozen audit's scheduled `run` with that consensus, preserving all primary records through the same left join. It writes `reviewed-comparison.zip`, which extends the standard reviewed archive with both original annotation passes, comparison evidence and wrapper/configuration identities.

The imported extended archive is retained under `returned-review/`. Its `summary.json` still reports independent review as pending because independent human accuracy remains unestablished. Agent agreement is not an accuracy percentage, human adjudication or full-cohort review. Preserve the wrapper's separate provenance when reproducing the comparison rather than assuming that a plain `run --annotations` command recreates it.

## Verification and interpretation boundaries

Eight synthetic tests were reported passing at the code checkpoint. They exercise duplicate appearances and excerpts, same-date filings and labels, missing and empty categories, unknown/conflicting identities, deterministic review selection without market fields, evidence/provenance validation and preservation of unknown rows. The checks use synthetic fixtures. Real-source completion is established by the separate scheduler and imported-output evidence, not inferred from those tests.

Accept a returned audit only after the 119-row coverage reconciles exactly to the reference filing, issuer and year counts, no primary labels were filtered by text, the fixed review sample and member hashes verify, and scheduler accounting confirms successful termination. Missing-text counts are reported but are not reconciled against the reference projection by this interface. A reviewed first batch remains a small auditable interpretation exercise rather than population ground truth or an accuracy estimate.

The label audit supplies reliable cohort definitions and explicit unknowns for later discovery. H21's option-priced comparisons, complete shuffled-date searches and large resampling archive return remain separate acceptance requirements. H22's recorded result, prior research exposure and the sealed organizer window remain preserved. Any later strategy follows a separately committed economic and execution plan before strategy code or backtesting.
