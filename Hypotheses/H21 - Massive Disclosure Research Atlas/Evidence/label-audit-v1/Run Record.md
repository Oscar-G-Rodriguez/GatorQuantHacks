# H21 standard-label audit — label-audit-v1

This record identifies the prepared standard-label audit and separates completed preparation from evidence that still requires scheduled execution or review. The change follows Oscar's October 4, 2026 instruction in chat `private project chat` to preserve Massive's standard classifications and use narrower economic distinctions only when their meaning can be verified. The [prospective protocol](../../Label%20Audit%20Protocol.md), [research log](../../Research%20Log.md) and [execution guide](../../../../docs/discovery/atlas.md) explain the method and operating boundaries.

Massive's served category is the primary observation. Completion, cash receipt, departure context and guidance direction are optional annotations. Missing, ambiguous and unreviewed annotations retain their primary events. This stage does not rewrite H22's receipt-word rule or its inconclusive backtest, select a profitable example, register a strategy, or simulate trades.

## Prepared identity and ordering

The stage manifest was created at `2026-10-04T07:29:39.93367-04:00`. Git inspection confirms that the complete protocol commit is an ancestor of the implementation commit; the protocol commit contains the completed method specification. The following identities come from the prepared private manifest and transfer receipt, with the local archive and verifier hashes checked against their actual bytes.

| Evidence | Identity |
| --- | --- |
| Complete protocol commit | `88db95aee74ea54f2fe8da0ea022673c8aa55717` |
| Implementation commit | `7dbd89b8b9d0baca29596f7e8356a81ba68ef179` |
| Stage manifest ID | `66dac7df700f40c791b7f7925ac5d74507b75e9e311567a1ad1767572811d928` |
| Manifest file SHA-256 | `ef0a63323d24e0702b16070d8aca234d2dec9fd4bf70c93ab9f00f7a9e22e268` |
| Source manifest ID | `dd286e7aa9fe7593d418d42737ccda1113986e42d48366373db840c167abc371` |
| Source manifest SHA-256 | `1af2623b713706afc7d087629a1d6df2a65ef4b9970e3d985a671f54828d4526` |
| Pinned taxonomy SHA-256 | `9f52ec76c76c33109c089d944d1f089b3d39024c8a7c14c98d6a15c76b254e50` |
| Existing stock master SHA-256 | `819c0423ce0214c99cbf45c3353ad558da7cb4790944d84a0e41536085cbff95` |
| Copied source-count projection SHA-256 | `571688155cb448e2f372d0669ab891eae83d0d358ed825831fcc8ce6f5d01353` |
| Transfer archive SHA-256 | `4d3bcf41bba141790a250ecfce6227a5a9d50594cbf3bbebe696fbaaacbe2316` |
| Transfer receipt file SHA-256 | `fd794b083f3dcd1f99348c3b1c6bce3c1a712ad0ad1e71963d23a14e31cc5d92` |
| Installation verifier SHA-256 | `bd9673a27f997b42ee33fe7cccc77c52060dad48d04b994326e2925b511f028d` |

The input archive is 704,877 bytes. Its transfer receipt lists 110 members for remote verification. The archive's local whole-file hash matches the receipt; remote extraction and all-member verification require separate evidence. The stock master is referenced solely to identify the existing category/source-count projection. Market outcomes, prediction results and P&L are excluded from cohort construction and the review packet.

The prepared manifest also freezes the relevant implementation bytes:

| File | SHA-256 |
| --- | --- |
| `discovery/atlas_label_audit.py` | `b7dac269cde3c04a1afca90ecf024cc308a8f46ac91acba014683a1092f0cc60` |
| `discovery/io.py` | `163fce0c52b455e3af23d779525d12ee3447a07f15c79b8abf620ad7d3981358` |
| H21 `label_audit.py` | `91640c43c9a1dbfb1beb0a12ac7e02061da55511fdb855533ba7832c486e695e` |
| H21 `Label Audit Protocol.md` | `e8141d7f426c9a5c2e4b2a09a903d631a604a8384ee675f97ed870a6e238d637` |
| `tests/test_atlas_label_audit.py` | `0df4af9ab60eacd5043848b7c49ea496ae17d03b57dad0eafd74b43913004cac` |

Licensed objects, unchanged excerpts, identity lookup keys, review cards and annotations remain under ignored private storage. This committed record contains their provenance identities and methodological boundaries, rather than their contents.

## Measured synthetic checks

The [research log](../../Research%20Log.md) records eight passing synthetic checks before preparation. Their [test implementation](../../../../tests/test_atlas_label_audit.py) is pinned above. These checks verify software behavior on artificial examples; they do not establish real coverage reconciliation, annotation accuracy, independent review or a market finding.

| Check | Verified behavior |
| --- | --- |
| Duplicate appearances and excerpts | Share-class appearances do not multiply one filing/category; distinct exact excerpts and source provenance survive. |
| Same-date filings and labels | Separate accessions remain separate, and several labels remain distinct records within their filing bundle. |
| Missing text and empty types | Missing text remains an event; a zero-observation taxonomy category remains visible. |
| Unknown labels and metadata conflicts | Unknown categories, hierarchy/identity/date conflicts and 2026 rows fail explicitly. |
| Source-only cards and deterministic selection | Review cards omit market values and explicit identity/date lookup fields; altered future returns do not change selection. |
| Exact evidence and provenance | A reviewed non-unknown field requires a supporting excerpt span, reviewer, timestamp and rationale. |
| Absent annotations | Unreviewed and missing-text cards retain unknown fields and remain present. |
| Invalid annotations | Duplicate or unknown card IDs, incompatible values and prohibited outcome fields are rejected. |

## Execution, review and acceptance boundaries

The prepared job uses one CPU in a scheduled HiPerGator allocation. It will reconstruct primary records from the frozen source, reconcile all 119 category rows against existing source counts, and export a private review packet. The seed is `H21-standard-label-audit-v1`; selection is up to five cards per category/year for debt issuance, executive-officer departure and guidance issuance/update, or at most 60 first-batch cards. Selection does not use outcomes. The lookup key is separate from the review view, though embedded names and dates in unchanged excerpts may remain visible.

The following table preserves the preparation checkpoint before the first scheduled allocation. The later execution record below supersedes its pending remote/execution items while retaining the original ordering.

| Requirement | Evidence at preparation checkpoint |
| --- | --- |
| Complete protocol precedes implementation | Verified commit contents and ancestry. |
| Frozen preparation and local archive identity | Manifest, transfer receipt and whole-file hashes recorded above. |
| Synthetic integrity checks | Eight passing checks recorded in the research log. |
| Remote archive/member verification | Pending measured remote verification. |
| Scheduled real-source execution | Pending measured scheduler job, completion and exit status. |
| Actual 119-row source reconciliation | Pending returned scheduled output. |
| Whole return archive and member verification on PC | Pending completed export, download and verified import. |
| First outcome-blind excerpt review | Pending returned cards and versioned annotations. |
| Scheduled validation and complete-cohort left join | Pending first annotations and a separate allocation. |
| Independent second review | Pending; no independent accuracy claim. |
| Full-cohort annotation | Pending; a first batch cannot establish population coverage or accuracy. |

All real source aggregation remains on HiPerGator. Local work covers code, synthetic checks, preparation, transfer verification and reading returned review cards. No real-data calculation, scheduler completion, complete audit or reviewed result is inferred from the existence of this package.

The standard-label audit does not finish the broader H21 atlas. Option-priced comparisons, the complete 499 full-search scrambled-timing searches and verified return of the large resampling archive remain separate unfinished requirements unless later measured evidence records their completion. Existing exposed development history remains exposed, and the organizer's sealed interval remains excluded. A later strategy still needs its own complete committed economic and execution plan before strategy implementation or backtesting.

## October 4, 2026 — first scheduled audit completed

The authenticated HiPerGator terminal reported that the uploaded whole-archive SHA-256 `4d3bcf41bba141790a250ecfce6227a5a9d50594cbf3bbebe696fbaaacbe2316` and installation-verifier SHA-256 `bd9673a27f997b42ee33fe7cccc77c52060dad48d04b994326e2925b511f028d` matched the PC identities. The verifier checked and installed all 110 members. Scheduled job `44683612` completed with exit `0:0` and scheduler elapsed time `00:00:02`. These are observed remote installation and scheduler facts; they do not establish a verified return to the PC.

The completed job's log reports the following source-only results:

| Result | Reported scheduled output |
| --- | --- |
| Taxonomy categories retained | 119 |
| Primary CIK/accession/category records | 5,353 |
| Distinct filings | 3,509 |
| Cards for the three optional-review categories | 906 |
| Cards selected for the first review batch | 60 |
| Cards still unreviewed, with unknown optional fields | All 906 |
| Primary labels excluded by text interpretation | 0 |
| Filing, distinct-issuer and year-count reconciliation | All matched the existing source-count projection |

The 906 cards cover the optional debt-issuance, executive-departure and guidance groups. They do not replace the 5,353 primary filing/category records. The 60-card selection is a first review batch under the committed source-only seed and rule, not a completed review or statistical sample of successful trades. Missing-text counts are reported in the audit, but the current implementation does not reconcile those counts against the reference table; the completed reconciliation claim is therefore limited to filing, issuer and year counts.

The remote job reported `audit.zip` SHA-256 `2bd9618ac9c644773480a321bd913d924dcb3b0ed9d6c544b3bfd8a6708a5f72` and ten hashed output members. The archive has not yet been imported or verified on the PC at this checkpoint. Whole-file and every-member return verification remain required before interpreting or reviewing the returned artifacts.

The implementation review also identified an operational boundary: interrupted outputs and a second annotation version require a fresh stage. Original outputs remain retained rather than overwritten. A later scheduled annotation validation must use a separate version and record its own job, output hashes and verified return.

First semantic review, scheduled annotation validation, independent second review and full-cohort annotation remain pending. The broader option-priced and placebo calculations remain outside this completed source audit. No new trading trial has run, and no alpha or independently supported strategy follows from these counts.

## October 4, 2026 — return imported and first review dispatched

The PC import verified whole ZIP SHA-256 `2bd9618ac9c644773480a321bd913d924dcb3b0ed9d6c544b3bfd8a6708a5f72` and all ten hashed members before installing the return under `data/cache/disclosure-atlas/label-audit-v1/returned`. A retained private copy is `data/cache/disclosure-atlas/label-audit-v1/returned-audit.zip`; the downloaded original remains `Downloads/audit.zip`. This completed verification supersedes the pending return status in the previous checkpoint. No audit code changed during return or documentation.

The imported summary confirms all 119 categories, 5,353 primary filing/category records, 3,509 distinct filings, 906 review cards and 60 selected first-batch cards. It confirms zero primary labels excluded by text and the filing/issuer/year reconciliation. All 906 optional annotations are unreviewed and unknown in the imported initial packet. These are verified source and preparation findings, not reviewed economic distinctions or market findings.

The first agent review has been dispatched against the returned source-only cards. Dispatch does not establish completion, supporting-span validation or independent accuracy. Its versioned annotations still require the separate scheduled validation allocation and verified return. Independent second review and full-cohort annotation also remain pending; the initial unreviewed packet and hashes are retained.

Separate scheduler observations clarify the broader atlas without changing this audit's scope:

| Existing H21 task | Measured scheduler evidence | Remaining boundary |
| --- | --- | --- |
| Shuffled-date resource pilot `44647730`, worker 0 | Completed `0:0`; elapsed `9:32`; batch MaxRSS `2688928K` | Pilot evidence, not all 499 complete searches. |
| Shuffled-date resource pilot `44647730`, worker 1 | Completed `0:0`; elapsed `13:05`; batch MaxRSS `3058636K` | Pilot evidence, not all 499 complete searches. |
| Shuffled-date resource pilot `44647730`, worker 2 | Completed `0:0`; elapsed `10:45`; batch MaxRSS `3027432K` | Pilot evidence, not all 499 complete searches. |
| Shuffled-date resource pilot `44647730`, worker 3 | Completed `0:0`; elapsed `9:32`; batch MaxRSS `2869344K` | Pilot evidence, not all 499 complete searches. |
| Large resampling archive return `44643729` | Completed `0:0`; elapsed `24:55` | Whole archive/member verification on the PC remains pending. |

The MaxRSS values above retain the scheduler's reported `K` units. A first-wave script is prepared for 16 placebo replicas across 128 cells each, with a maximum of 64 concurrent workers. It has not yet been submitted at this checkpoint. Prepared scripts and the completed four-worker pilot do not establish full-wave execution or the complete declared 499-replica search. Option-priced comparisons remain unfinished, and this documentation records no new trading trial or alpha conclusion.

## October 4, 2026 — placebo wave running and two blind reviews returned

The first numerical full-search placebo wave was submitted as job array `44684234` after remote script SHA-256 `73ceb6c540870d3225ac9220dfa181c219a41ed3de9fc651a591bfd786b70599` was verified. The array is `0–2047%64`, covering 16 replicas across 128 cells each, with one CPU, 8 GB memory and a two-hour limit per task. It uses the unchanged numerical parent manifest `66aa91424cacbe818edea9b1be52348818269db99081f70195bb71c4a40dfb15`. The latest scheduler snapshot reports 64 running tasks and a compressed pending range. This measured submission and running state supersede the prepared-but-unsubmitted status in the previous checkpoint. No completed full-wave results or verified return are claimed here, and the full 499-replica search remains unfinished.

Windows Application Control blocked the local scikit-learn-dependent job generator. The identical Slurm worker template was rendered locally using the standard library; numerical source and settings were unchanged. No policy bypass occurred. The verified script identity above records the actual submitted artifact rather than assuming that the blocked generator completed.

Two separate source-only agent reviews of the selected 60 cards have now finished. Their annotation-file identities are:

| Review artifact | SHA-256 |
| --- | --- |
| First 60-card agent review | `0b901466c0967dc60fbb59f3af9d2c18c17ee780f598863e57d97ce63f968615` |
| Second 60-card agent review | `46e0817322c75be860d184a2c46ea3dedfc3d4412dbfb488a006f07ae0dbbdba` |

Finished agent reviews are not human ground truth, validated population annotations or evidence of alpha. The scheduled validation, consensus and comparison wrapper and its transfer hashes have been generated locally, but upload and submission remain pending at this checkpoint. The consensus rule retains disagreements as unknown. Supporting-span validation, the scheduled complete-cohort left join, review-comparison results and verified return therefore remain unestablished. The initial packet with all 906 cards unreviewed stays retained, and the unselected cards still require review before full-cohort annotation can be claimed.

Option acquisition resumed under a 1,000-call cap and stopped at its request budget. It did not complete option coverage. Exact acquisition receipt counts remain pending and are not inferred from the cap. No new trading trial, supported strategy or alpha conclusion is recorded by these operational and review milestones.

## October 4, 2026 — scheduled review validation and verified return completed

The five review-stage upload hashes matched `review-transfer.json` on HiPerGator before execution. The transfer receipt file has SHA-256 `86084d64d93b2d8690fcbb7d6600ed896661b3a9c55993af9ae5b50cb51b352b`. It pins the two review files recorded above, the validation/comparison wrapper (`98a575f4f06703f857c1ee549c22e05e3deb1e69ff54c31e2136e08cc68b02bb`), review-stage settings (`52ccd0b95c821c67eb1224b4eb459c0c31fe9cbf4b7690545403d22375d6508a`) and allocation script (`a4753d0ecbd4a6a5aecc2ce4ff00c4fa8fb8047890091f5cc0776e7a785be8f7`). These private review-stage artifacts preserve the original audit outputs and use the unchanged primary-audit implementation.

Scheduled validation job `44684985` completed with exit `0:0` and elapsed time `00:00:04`. Its recorded finish time is `2026-10-04T11:53:51.887615+00:00`. The resulting `reviewed-comparison.zip` whole SHA-256 is `78d4b35fd567709c8b734c9956620b1f42e13962cb637395177bad6e9c8af026`. The PC verified that whole archive and all 15 hashed members at `2026-10-04T11:54:40.125636+00:00`, importing the return under `data/cache/disclosure-atlas/label-audit-v1/returned-review`. The retained ZIP's actual bytes match that hash. This completed allocation and verified return supersede the pending review-stage upload, submission, validation and import items in the previous checkpoint.

The scheduled comparison covers 60 cards and 80 optional fields. Three reviewer disagreements remain unknown in the conservative consensus: two transaction-stage fields were interpreted as completed by one review and unknown by the other; one guidance-direction field was unknown in one review and reaffirmed in the other. No disagreeing interpretation is promoted to a known economic condition.

The imported summary retains the full primary cohort and reports:

| Result | Verified returned summary |
| --- | --- |
| Taxonomy categories | 119 |
| Primary filing/category records | 5,353 |
| Distinct filings | 3,509 |
| Optional-review cards | 906 |
| First-batch cards | 60 |
| Unreviewed cards | 846 |
| Reviewed cards | 32 |
| Ambiguous cards | 28 |
| Missing-text cards | 0 |
| Primary labels filtered by text | 0 |

Ambiguous and unknown fields remain attached to their primary events. The imported summary retains `independent_review: pending` and `statistical_or_alpha_claim: false`. Two agent interpretations plus exact-span validation do not establish independent human accuracy. Full-cohort annotation and human accuracy review remain pending. The recorded source-count reconciliation still concerns filing, issuer and year counts; missing-text counts are reported but not reconciled against the reference table. Original outputs, review files, disagreements and separate return receipts are preserved.

The resumed option source now has a measured receipt. It finished this bounded attempt at `2026-10-04T11:50:14.418569+00:00` with 868 served anchor records and 7,957 retained objects. Its source ID is `d0872f22a2ced674da8c81f06b1bb7138b799c3a1aea4907b563b044ccba5163`, and request-file SHA-256 is `101d0710fc88a95eda3fa9be54e36b63db02d5927de86b9b0e6c651113b83dde`. The source remains `complete: false` after the 1,000-call-budget attempt. These resumed-source counts do not establish complete option eligibility or completed option-priced comparisons. The full placebo search and large-archive PC verification also remain unfinished. No new trading trial was run through this review stage, and it establishes no supported alpha conclusion.


## October 4, 2026 — latest partial worker snapshot

Authenticated scheduler accounting observed 62 tasks in array `44684234` completed with `0:0`, 61 running and one compressed pending range at the latest check (recorded `2026-10-04T11:55:37+00:00`). This is partial execution of the 2,048-task first wave. Pending display rows are not a count of pending tasks, and scheduler completion alone does not verify scientific output members. The private snapshot is `data/cache/disclosure-atlas/label-audit-v1/placebo-wave0-scheduler-snapshot.json`. Full wave aggregation/return, all 499 replicas, option-priced comparisons and large-archive PC acceptance remain outstanding.
