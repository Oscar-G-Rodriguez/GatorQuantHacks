# Run the registered H18–H20 package

Read the [registered protocol](mechanism-round1-plan.md) and [settings](../../config/mechanism-round1.json), then the selected folder's brief and research log. Substantive registration is `7688ad1d96303039d6e61ef2dcc6f19f21764a15`; the draft-only checkpoint is earlier. This code adapts the Webull example's offline Backtrader feed/strategy organization and the Massive notebook's parity/option-payoff conventions. Its custom funded ledger accounts for collateral and every leg. It never invokes live trading.

The PC acquires information and prepares hashes/archives. Slurm compute nodes execute real mechanism estimates, resampling, model fits and option programs. The session feed is only a clock: reported NAV comes from the funded ledger, never Backtrader's default stock broker. The primary quote-backed portfolio uses filing horizon 5; other required filing horizons are independent same-unit diagnostics, not a continuously held portfolio claim.

From the root, use the existing Python 3.11 environment and shared `.env`. Download development only:

```powershell
uv run --no-sync python -m discovery.mechanism_data --phase development --output data/cache/massive-mechanisms/round1/development
uv run --no-sync python -m unittest discover -s tests -p 'test_mechanism*.py' -v
```

Retain failed receipts and cache checkpoints. Complete raw sources are hash-checked; a missing option/quote stays unavailable. The first acquisition failed on a Windows atomic receipt replacement; the bounded-retry correction was tested and the resume completed 111 anchors in 8,448 cumulative HTTP attempts. Historical raw content remains private.

H20 reviews live in the ignored source folder's `cfo-reviews.json`. Each verified record has incoming-person identity, same-accession passages and their hash. No passage absence is interpreted as full-filing absence. The October 3 development review retained 34 events, 21 verified incoming-person terms, two other-person/ambiguous records and 11 unknown excerpts. A SEC full-filing probe returned HTTP 403. With no verified-absence group, the primary filtered program abstains; all-CFO and separately labeled proxy diagnostics remain in its evidence.

Create an immutable phase run, its scripts and private archive:

```powershell
uv run --no-sync python -m discovery.mechanism_run manifest --source data/cache/massive-mechanisms/round1/development --run data/cache/massive-mechanisms/runs/development-v1
uv run --no-sync python -m discovery.mechanism_jobs jobs --run data/cache/massive-mechanisms/runs/development-v1 --remote /blue/ai-workshop/<UF_USERNAME>/quanthacks/discovery/mechanisms-round1-development-v1
uv run --no-sync python -m discovery.mechanism_jobs bundle --run data/cache/massive-mechanisms/runs/development-v1 --output data/cache/massive-mechanisms/transfer/development-v1.tar.gz
```

Upload into that fresh personal Blue directory, verify the whole archive SHA-256 against the local receipt **before extracting**, then verify `BUNDLE-FILES.json` member hashes. The single compute submission command is:

```bash
bash data/cache/massive-mechanisms/runs/development-v1/hpg/submit.sh
```

Setup synchronizes the frozen root dependencies and runs synthetic tests; three folder runners execute concurrently with one CPU/8 GB each. Report assembly follows terminal core tasks. A separate return job follows terminal report assembly so scheduler accounting can confirm the report's actual exit. Failures are exported with the results. Reusing a run directory or overwriting task evidence is rejected.

Download `returned-results.zip` and observe its remote SHA-256. Import verifies that whole hash, manifest identity, archive paths and all members before writing anything:

```powershell
uv run --no-sync python -m discovery.mechanism_jobs import --run data/cache/massive-mechanisms/runs/development-v1 --archive <downloaded-zip> --expected-sha <observed-remote-sha>
```

Inspect development findings and retain every trial/failure. Freeze only after the return and terminal scheduler proof verify. `freeze` fixes code, settings, the three-member final family, and trained development prediction models. Final-data access requires this file and writes an exposure receipt before any calls. Use the same pipeline with `--phase final-oos --freeze <freeze-json>`; supply `--freeze` when creating its manifest. No transformation/model is refitted to final outcomes. Insufficient development model/group support remains inconclusive in final evaluation.

Judges may supply an explicit `--phase sealed --start ... --end ... --as-of ...` acquisition interval; we do not execute their sealed dates. The same frozen prediction models and code are required for their scientific replay.

Each task retains all mandated horizons, missing reasons, primary and secondary intervals, ordinary/long/cash/price-only comparisons, nearby settings, years, prior shock/quiet states, curves, all-leg fill audit, capacity scenarios and S01–S12 outcomes. Square-root participation impact is an **uncalibrated proxy**, not measured dollar impact. Missing historical label release, dividend/assignment validity and broad-exposure attribution prevent an executable supported-signal verdict. Conditional mechanism results can still guide later research.

Run evidence is private and ignored. Folder logs point to its canonical location; selectively retained derived summaries may be added after verification. The later combined quant note must disclose post-discovery development, the static universe, missing support and the one-time final exposure. Publishing/submission/live orders require separate authorization.

Coverage safeguard: an ordinary anchor is usable only when its entire registered +/-30-calendar-day category exclusion interval lies inside the acquired filing history. Boundary intervals remain unknown and are retained as missing, rather than assumed event-free. No historical labels are borrowed from another phase.

Operational history: development-v1 setup failed before analysis because the transfer omitted shared build inputs. Its actual setup/accounting/ID files were returned and verified (ZIP SHA-256 `66f2386789e4147eafe08a62cc6d4c955f9035ce780270ce92ed6c70ee708e50`, three members). The corrected package includes `webull_bt/` and `docs/README.md` once at root and validates declared build inputs. Empty category windows also preserve complete schemas and inconclusive results. The corrected local suite passed 25 checks in 0.303 seconds; use a fresh development-v2 run rather than overwrite v1.

Read the [verified development findings](mechanism-round1-development.md) for measured support, baseline accounting, actual successful job IDs and the final freeze/exposure record. All three development verdicts are inconclusive; return completion does not imply signal support.

The original final H18/H19 tasks failed on an empty quote-comparison schema. Follow the [bounded correction plan](mechanism-round1-correction.md) and preserve the first final exposure. A corrected replay is explicitly after exposure; it cannot be called untouched.

## Corrected round-1 runs and presentation reproduction

The accepted development replay is `development-v3`, under the bounded [post-exposure correction plan](mechanism-round1-correction.md). Its 65 returned members verified; all 45 scientific files match development-v2 after normalizing only run identifiers. The corrected freeze is `data/cache/massive-mechanisms/round1/development-corrected-freeze.json` (SHA-256 `daf1f3e000594effb3043f357f6e9e25e338cbcb6a2bf311e0d5d321627ddcef`). It does not replace the original freeze. Final-oos-v2 reuses the existing final source and outcome-blind reviews; no new HTTP requests are needed. The separate `download-corrective-replay.json` links the preserved original exposure, failed attempt, code repair and equality receipt.

The corresponding final compute submission, after whole/member transfer verification, is:

```bash
bash data/cache/massive-mechanisms/runs/final-oos-v2/hpg/submit.sh
```

This is a corrective replay after exposure, not an untouched holdout. A fresh reproduction should use distinct run directories; the scientific helpers reject overwriting attempts. Final models remain those trained on development-v3. The scheduler chain uses setup -> three tasks concurrently -> report -> return. The PC only downloads, verifies, packages and typesets.

The combined note and table are generated from verified returned artifacts. The optional presentation dependency is separate from the frozen scientific lock:

```powershell
python -m pip install -r scripts/requirements-mechanism-note.txt
python scripts/render_mechanism_round1_note.py --evidence docs/massive/mechanism-round1-evidence.json
```

The retained derived-evidence snapshot has a SHA-256 sidecar and contains selected returned metrics, findings, curves, actual method statuses, code identities and scheduler proof. This command regenerates the note and headline CSV without provider access, licensed raw responses, model fitting or portfolio replay. A fresh scientific rerun instead needs appropriately entitled historical inputs and the root locked environment. Keep local raw archives private and retain all prior failed/exposed records.

Read the [combined verified findings](mechanism-round1-results.md), [headline table](mechanism-round1-headline.csv), [derived snapshot](mechanism-round1-evidence.json) and [report verification](mechanism-round1-report-verification.json) after completing this route. They report actual inconclusive outcomes and preserve both final attempts.
