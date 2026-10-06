# Massive coverage preparation

This shared utility checks data feasibility before a strategy is chosen. It retrieves a versioned taxonomy, a bounded set of development-period disclosure categories and small historical stock/option samples. Its output describes data access, filing counts, source grain, missing mappings and candidate filing-date order. It computes no return, price correlation, strategy score, option P&L or selected signal window.

Begin with [the vault's Massive track reference](../../../Massive%20Track/README.md), particularly its challenge, endpoint discovery and data-timing review. Statistical discovery code may precede a formed hypothesis under [the repository rules](../../AGENTS.md); substantive registration remains required before strategy implementation or backtesting. The [discovery run guide](../discovery/README.md) describes the nine studies, local historical downloads and subsequent HiPerGator computation. This coverage utility is preparation rather than a registered hypothesis or a competition backtest.

## Local key and command

The shared root `.env.example` now has a `MASSIVE_API_KEY` placeholder. Put the actual key in the ignored root `.env` or a local process environment variable. The utility reads it locally and sends an Authorization header; it never asks for a key in chat or prints it. No wallet or pay-per-request service is used.

Run from the repository root:

```powershell
uv run --no-sync python tools/check_massive_coverage.py `
  --universe-source '../../../Sources/QuantHacks/Massive Track Reference/2026-10-03 - Massive Starter Notebook.md' `
  --categories ceo_departure guidance_withdrawal `
  --max-requests 16
```

The category arguments reflect Oscar's discussion example, without selecting an economic strategy. The utility reads the source's `TOP_100` literal as text; it never executes the notebook. This is the supplied static September 2026 universe, not historical membership. Requests stay in January 2024–December 2025, with default AAPL option-access samples on January 2, 2024 and December 1, 2025. Future contract expiry metadata can be known before expiry; no later option-price outcome is requested.

The tool waits at least 12.5 seconds between standard REST requests, follows only pagination on `api.massive.com`, rejects redirects, strips auth query parameters from recorded URLs and enforces a maximum request count. HTTP errors or unfinished pagination leave a partial report rather than proving absent data or entitlement. Sample contract choice is a price-access check, not a trade recommendation; accepted zero-row queries remain distinct from authorization errors.

## Output and interpretation

Each run saves source responses, hashes, request receipts and `coverage-summary.json` under the ignored `data/cache/massive-coverage/<run-id>/`. Never commit the key or licensed source responses. Deliberately retained derived evidence needs a separate review and provenance record.

Disclosures use `tickers`, an optional list, rather than a singular `ticker`. Matching expands only symbols present in the supplied universe; CIK identifies issuers when available. Rows without ticker lists remain unmatched and counted explicitly. Share-class matches, filing/category identity and independent underlying developments are different units. Distinct filing counts alone do not prove independent events.

The optional ordering description requires the first filing to have a strictly earlier date and a different accession for the same issuer. Same-accession labels and same-day filings are separately counted. It records observed calendar-day gaps without choosing a threshold, testing a future outcome or resolving public/vendor availability. Events before January 2024 are outside this preparation sample.

## October 3 evidence and correction

Ten requests completed successfully: the taxonomy contained 119 rows; CEO departure returned 1,951 all-market label rows and guidance withdrawal 27. After matching ticker lists, the starter universe had 31 CEO-departure filing/category records across 25 CIKs and no matched guidance-withdrawal records. CEO rows without ticker mappings numbered 433; guidance withdrawal had one such row. The unmatched guidance CIK did not match the 25 observed starter-universe CEO CIKs, which still does not prove its complete issuer identity or permanent absence from that universe.

Both AAPL dates returned a stock bar, five reference contracts and six daily bars for the selected option over the short sample interval. This verifies those specific samples, not all companies, expiries, dates, quotes or live delivery.

The first processing pass expected a singular ticker and incorrectly produced zero universe counts. The original report was retained; its universe counts are invalid. An initial correction then rejected legitimate missing ticker lists, which was repaired by counting the missing mappings explicitly. Corrected processing used identical cached responses, verified hashes and made no new API requests. Its output is `coverage-summary-corrected.json`. Repeat that correction offline with:

```powershell
uv run --no-sync python tools/check_massive_coverage.py `
  --universe-source '../../../Sources/QuantHacks/Massive Track Reference/2026-10-03 - Massive Starter Notebook.md' `
  --categories ceo_departure guidance_withdrawal `
  --reprocess 'data/cache/massive-coverage/20261003T092239280902Z'
```

Offline fixtures verified plural ticker lists, missing/malformed mappings, share-class identity, CIK-based ordering, same-day/same-accession exclusion, auth-query redaction, off-host rejection and rejection of an OOS price probe before requesting it. Git-ignore checks covered the local key and cache. No correlation, return or hypothesis acceptance was evaluated.

## Registered mechanism round

Before H18–H20 acquisition, implementation or review, read the [complete round-1 protocol](mechanism-round1-plan.md), [settings](../../config/mechanism-round1.json), selected folder brief/log and root signal/evidence requirements. This earlier coverage utility remains preparation. Historical tags and approximate parity do not establish executable availability.

The [mechanism run guide](mechanism-run-guide.md) is required before implementation, acquisition, transfer or replay. It documents the owned runners, private source review, manifests, Slurm jobs, verified return and final freeze.
