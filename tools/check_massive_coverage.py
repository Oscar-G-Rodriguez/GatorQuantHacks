"""Bounded, development-only data preparation; no returns or strategy evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
HOST = "https://api.massive.com"
DEVELOPMENT_START, DEVELOPMENT_END = "2024-01-01", "2025-12-31"


def clean_url(url):
    """Never store auth query parameters or follow pagination off the API host."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "api.massive.com":
        raise ValueError("Pagination URL is outside the expected API host")
    pairs = [(key, value) for key, value in parse_qsl(parsed.query) if key.lower() not in {"apikey", "api_key", "token"}]
    return urlunparse(parsed._replace(query=urlencode(pairs)))


class AccessFailure(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # A provider migration needs review rather than forwarding the key.
        return None


class Client:
    def __init__(self, key, output, max_requests, minimum_interval=12.5, separate_buckets=False):
        if not math.isfinite(minimum_interval) or minimum_interval < 0.5:
            raise ValueError("Minimum request interval must be at least half a second")
        self.key, self.output, self.max_requests = key, output, max_requests
        self.last_request = None
        self.receipts = []
        self.minimum_interval, self.separate_buckets = minimum_interval, separate_buckets
        self.bucket_last_request, self.bucket_intervals = {}, {}

    def request_bucket(self, url):
        if not self.separate_buckets:
            return "shared"
        path = unquote(urlparse(url).path)
        if path.startswith("/v3/reference/"):
            return "reference"
        if path.startswith(("/v3/quotes/O:", "/v2/aggs/ticker/O:")):
            return "options"
        if path.startswith("/v2/aggs/ticker/"):
            return "stocks"
        return "shared"

    @staticmethod
    def retry_delay(value):
        try:
            delay = float(value)
        except (TypeError, ValueError):
            try:
                delay = (parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                delay = 60
        if not math.isfinite(delay):
            delay = 60
        return max(60, delay)

    def get(self, label, path=None, params=None, url=None):
        url = clean_url(url or f"{HOST}{path}?{urlencode(params or {})}")
        for attempt in range(3):
            before = len(self.receipts)
            try:
                return self._get_once(label, url)
            except AccessFailure:
                if len(self.receipts) == before or self.receipts[-1]["http_status"] != 429:
                    raise
                receipt = self.receipts[-1]
                self.bucket_intervals[receipt["pacing_bucket"]] = 12.5
                if attempt == 2 or len(self.receipts) >= self.max_requests:
                    raise
                delay = receipt["retry_after_seconds"]
                if delay > 3600:
                    raise AccessFailure("Rate-limit wait exceeds one hour; resume later") from None
                print(f"{label}: HTTP 429; slowing {receipt['pacing_bucket']} bucket and retrying after {delay:g}s", flush=True)
                remaining = delay
                while remaining > 0:
                    part = min(60, remaining)
                    time.sleep(part)
                    remaining -= part

    def _get_once(self, label, url):
        if len(self.receipts) >= self.max_requests:
            raise AccessFailure("Configured request cap reached; coverage remains partial")
        bucket = self.request_bucket(url)
        interval = self.bucket_intervals.get(bucket, self.minimum_interval)
        last = self.bucket_last_request.get(bucket)
        if last is not None:
            time.sleep(max(0, interval - (time.monotonic() - last)))
        self.last_request = time.monotonic()
        self.bucket_last_request[bucket] = self.last_request
        receipt = {"label": label, "url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(), "http_status": None,
                   "pacing_bucket": bucket, "minimum_interval_seconds": interval}
        self.receipts.append(receipt)
        try:
            request = Request(url, headers={"Authorization": f"Bearer {self.key}", "Accept": "application/json"})
            with build_opener(NoRedirect()).open(request, timeout=40) as response:
                receipt["http_status"] = response.status
                raw = response.read()
        except HTTPError as error:
            receipt["http_status"] = error.code
            receipt["error"] = f"HTTP {error.code}; response text omitted to protect credentials"
            if error.code == 429:
                receipt["retry_after_seconds"] = self.retry_delay(error.headers.get("Retry-After"))
            raise AccessFailure(receipt["error"]) from None
        except (URLError, TimeoutError, OSError):
            receipt["error"] = "Network request failed; no entitlement conclusion"
            raise AccessFailure(receipt["error"]) from None
        payload = json.loads(raw)
        file_name = f"response-{len(self.receipts):02d}.json"
        (self.output / file_name).write_bytes(raw)
        receipt.update(cache_file=file_name, sha256=hashlib.sha256(raw).hexdigest(), status=payload.get("status"), rows=len(payload.get("results") or []))
        if payload.get("status") in {"ERROR", "NOT_AUTHORIZED"}:
            raise AccessFailure("Provider reported an API error; raw response is in the ignored cache")
        print(f"{label}: HTTP {receipt['http_status']}, rows={receipt['rows']}", flush=True)
        return payload

    def pages(self, label, path, params):
        rows, next_url, seen = [], None, set()
        while True:
            payload = self.get(label, path, params, next_url)
            rows.extend(payload.get("results") or [])
            next_url = payload.get("next_url")
            if not next_url:
                return rows
            next_url = clean_url(next_url)
            if next_url in seen:
                raise AccessFailure("Repeated pagination URL; coverage remains partial")
            seen.add(next_url)


def profile(rows, universe):
    # The disclosure grain contains a ticker LIST, potentially multiple share
    # classes. Expand only matching symbols and retain CIK for issuer identity.
    filtered = []
    for row in rows:
        if row.get("tickers") is not None and not isinstance(row["tickers"], list):
            raise ValueError("Unexpected disclosure tickers type; universe match is unverified")
        for ticker in sorted(set(row.get("tickers") or []) & universe):
            filtered.append({**row, "ticker": ticker})
    identity = lambda row: (row.get("cik") or row.get("ticker"), row.get("accession_number"), row.get("tertiary_category"))
    keys = Counter(identity(row) for row in filtered)
    dates = sorted({row.get("filing_date") for row in filtered if row.get("filing_date")})
    return {
        "all_market_rows": len(rows), "starter_universe_rows": len(filtered),
        "distinct_issuer_filing_category_keys": len(keys),
        "repeated_issuer_filing_category_keys": sum(count > 1 for count in keys.values()),
        "distinct_issuers": len({row.get("ticker") for row in filtered}),
        "distinct_ciks": len({row.get("cik") for row in filtered if row.get("cik")}),
        "source_rows_matching_universe": sum(bool(set(row.get("tickers") or []) & universe) for row in rows),
        "missing_ticker_lists_in_source": sum(not row.get("tickers") for row in rows),
        "ticker_mapping_limit": "Rows lacking ticker lists cannot be matched to the starter universe by this check; issuer mapping has not been independently repaired",
        "rows_by_year": dict(Counter((row.get("filing_date") or "missing")[:4] for row in filtered)),
        "rows_by_month": dict(sorted(Counter((row.get("filing_date") or "missing")[:7] for row in filtered).items())),
        "first_filing_date": dates[0] if dates else None, "last_filing_date": dates[-1] if dates else None,
        "missing_fields": {field: sum(row.get(field) in (None, "") for row in filtered) for field in ["ticker", "accession_number", "filing_date", "tertiary_category", "supporting_text"]},
        "source_grain": "Disclosure label rows; distinct filing/category keys are not verified independent underlying economic events",
    }, filtered


def candidate_ordering(first_rows, second_rows):
    """Describe dates only; no event window, future-price label or signal scoring."""
    first = {(row.get("cik") or row["ticker"], row["accession_number"], row["filing_date"]) for row in first_rows}
    second = {(row.get("cik") or row["ticker"], row["accession_number"], row["filing_date"]) for row in second_rows}
    ticker_for_issuer = {row.get("cik") or row["ticker"]: row["ticker"] for row in first_rows + second_rows}
    candidates = []
    same_accession = 0
    same_day = 0
    for issuer_id, accession, when in sorted(second):
        previous = [(prior_date, prior_accession) for issuer, prior_accession, prior_date in first if issuer == issuer_id and prior_date < when and prior_accession != accession]
        same_accession += any(issuer == issuer_id and prior_accession == accession for issuer, prior_accession, _ in first)
        same_day += any(issuer == issuer_id and prior_date == when and prior_accession != accession for issuer, prior_accession, prior_date in first)
        if previous:
            prior_date, prior_accession = max(previous)
            candidates.append({"ticker": ticker_for_issuer[issuer_id], "issuer_identity": issuer_id, "first_filing_date": prior_date, "second_filing_date": when, "first_accession": prior_accession, "second_accession": accession, "gap_calendar_days": (date.fromisoformat(when) - date.fromisoformat(prior_date)).days})
    return {
        "second_filings_with_strictly_earlier_different_accession_first_filing": len(candidates),
        "distinct_issuers": len({row["ticker"] for row in candidates}),
        "second_filings_with_same_accession_first_label": same_accession,
        "second_filings_with_same_day_distinct_first_filing": same_day,
        "candidates": candidates,
        "limitations": "Date-ordered filing candidates only; same-day order unknown, no public/vendor clocks, no selected gap threshold, no verified independence, no prior events before development start, no pricing outcome analyzed.",
    }


def option_probe(client, when):
    day = date.fromisoformat(when)
    if not DEVELOPMENT_START <= when <= DEVELOPMENT_END:
        raise ValueError("Probe must remain within the development period")
    end = min(day + timedelta(days=7), date.fromisoformat(DEVELOPMENT_END))
    spot = client.get(f"Stock bar availability {when}", f"/v2/aggs/ticker/AAPL/range/1/day/{when}/{when}")
    bars = spot.get("results") or []
    if not bars:
        return {"date": when, "stock_bar_rows": 0, "contract_rows": None, "option_bar_rows": None, "interpretation": "No stock bar in this exact date sample; later steps skipped"}
    close = bars[0]["c"]
    reference = client.get(f"Option contract availability {when}", "/v3/reference/options/contracts", {
        "underlying_ticker": "AAPL", "contract_type": "call", "as_of": when,
        "expiration_date.gte": (day + timedelta(days=30)).isoformat(),
        "expiration_date.lte": (day + timedelta(days=90)).isoformat(),
        "strike_price.gte": round(close * .9, 2), "strike_price.lte": round(close * 1.1, 2),
        "expired": "false", "limit": 5,
    })
    contracts = reference.get("results") or []
    if not contracts:
        return {"date": when, "stock_bar_rows": len(bars), "contract_rows": 0, "option_bar_rows": None, "interpretation": "Accepted narrow reference query returned no contracts; not proof of absent entitlement"}
    contract = min(contracts, key=lambda row: abs(row["strike_price"] - close))
    prices = client.get(f"Option bar availability {when}", f"/v2/aggs/ticker/{contract['ticker']}/range/1/day/{when}/{end.isoformat()}")
    return {"date": when, "stock_bar_rows": len(bars), "contract_rows": len(contracts), "sample_contract": contract["ticker"], "option_bar_rows": len(prices.get("results") or []), "interpretation": "One reference/price sample, not complete universe/history or executable quote coverage; numeric price outcomes not scored"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-source", type=Path, required=True, help="Inspected starter text containing TOP_100; never executed")
    parser.add_argument("--categories", nargs=2, required=True, help="Two labels for descriptive filing-date feasibility")
    parser.add_argument("--probe-dates", nargs="*", default=["2024-01-02", "2025-12-01"])
    parser.add_argument("--max-requests", type=int, default=16)
    parser.add_argument("--reprocess", type=Path, help="Reprofile existing cache offline without reading a key or making requests")
    args = parser.parse_args()
    if not 1 <= args.max_requests <= 20:
        parser.error("Request cap must be between 1 and 20")
    text = args.universe_source.read_text(encoding="utf-8-sig")
    match = re.search(r'TOP_100\s*=\s*"""(.*?)"""\.split\(\)', text, re.S)
    if not match:
        parser.error("Starter TOP_100 literal not found; source is read as text only")
    universe = match.group(1).split()
    if len(universe) != 100 or len(set(universe)) != 100:
        parser.error("Expected 100 distinct starter tickers")
    if args.reprocess:
        run = args.reprocess.resolve()
        report = json.loads((run / "coverage-summary.json").read_text())
        if not report["complete"] or report["categories"] != args.categories:
            parser.error("Offline reprocessing requires a completed matching collection")
        filtered = []
        for category in args.categories:
            records = []
            for receipt in report["request_receipts"]:
                if receipt["label"] == f"Development disclosure coverage {category}":
                    raw = (run / receipt["cache_file"]).read_bytes()
                    if hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
                        parser.error("Cached source hash mismatch")
                    records.extend(json.loads(raw).get("results") or [])
            summary, selected = profile(records, set(universe))
            report["category_profiles"][category] = summary
            filtered.append(selected)
        report["date_ordering_candidates"] = candidate_ordering(*filtered)
        report["processing_history"] = [{"initial_report": "coverage-summary.json", "status": "Invalid universe counts; singular ticker assumption mismatched actual tickers list", "correction": "Offline reprocessing of identical cached bytes; tickers-list expansion and CIK issuer identity", "corrected_at": datetime.now(timezone.utc).isoformat(), "additional_requests": 0}]
        output = run / "coverage-summary-corrected.json"
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"corrected_report": str(output), "category_profiles": report["category_profiles"], "date_ordering_candidates": report["date_ordering_candidates"]}), flush=True)
        return 0
    key = os.getenv("MASSIVE_API_KEY") or dotenv_values(ROOT / ".env").get("MASSIVE_API_KEY")
    if not key or key.strip().lower().startswith(("your_", "replace_", "paste_")):
        parser.error("Set MASSIVE_API_KEY locally in root .env; never paste the key into chat")
    output = ROOT / "data/cache/massive-coverage" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True)
    client = Client(key.strip(), output, args.max_requests)
    report = {"scope": "Development-only descriptive coverage; no correlation, prediction, return, strategy or P&L evaluation", "development_window": [DEVELOPMENT_START, DEVELOPMENT_END], "starter_universe": universe, "universe_source_sha256": hashlib.sha256(args.universe_source.read_bytes()).hexdigest(), "categories": args.categories, "request_cap": args.max_requests, "requests_per_minute_max": 5, "complete": False, "category_profiles": {}, "option_probes": [], "entitlement": "Only the specific successful endpoint/date samples are observed", "warnings": ["Starter universe is static September 2026 membership and introduces survivorship/selection concerns", "Filing dates cannot resolve intraday information availability", "No 2026 later sample or judges' sealed-window request is made", "Candidate sequence counts do not prove independent events or a profitable options trade"]}
    exit_code = 0
    try:
        taxonomy = client.pages("Disclosure taxonomy", "/stocks/taxonomies/vX/disclosures", {"limit": 1000})
        labels = {row.get("tertiary_category") for row in taxonomy}
        if not set(args.categories) <= labels:
            raise AccessFailure("Requested categories not found in retrieved taxonomy")
        report["taxonomy_rows"] = len(taxonomy)
        report["taxonomy_versions"] = sorted({str(row.get("taxonomy_version", row.get("version"))) for row in taxonomy if row.get("taxonomy_version", row.get("version")) is not None})
        filtered = []
        for category in args.categories:
            rows = client.pages(f"Development disclosure coverage {category}", "/stocks/filings/8-K/vX/disclosures", {
                "tertiary_category": category, "filing_date.gte": DEVELOPMENT_START,
                "filing_date.lte": DEVELOPMENT_END, "limit": 1000, "sort": "filing_date.asc",
            })
            if any(not DEVELOPMENT_START <= row.get("filing_date", "") <= DEVELOPMENT_END for row in rows):
                raise AccessFailure("Provider returned rows outside requested development dates")
            summary, category_rows = profile(rows, set(universe))
            report["category_profiles"][category] = summary
            filtered.append(category_rows)
        report["date_ordering_candidates"] = candidate_ordering(*filtered)
        for when in args.probe_dates:
            report["option_probes"].append(option_probe(client, when))
        report["complete"] = True
    except (AccessFailure, ValueError, KeyError) as error:
        exit_code = 1
        report["failure"] = str(error) if isinstance(error, AccessFailure) else "Unexpected response structure or invalid data; inspect the ignored local cache"
    finally:
        report["request_receipts"] = client.receipts
        report["requests_made"] = len(client.receipts)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        (output / "coverage-summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Coverage report saved: {output / 'coverage-summary.json'}", flush=True)
        print(json.dumps({"complete": report["complete"], "requests_made": report["requests_made"], "category_profiles": report["category_profiles"], "date_ordering_candidates": report.get("date_ordering_candidates"), "option_probes": report["option_probes"], "failure": report.get("failure")}), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
