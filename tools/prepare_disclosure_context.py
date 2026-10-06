"""Retain all development disclosure tags for already-observed lead issuers.

The same-filing join uses CIK plus accession. A shared filing date cannot create
a co-tag. This is local download/preparation, without outcome calculations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values
from check_massive_coverage import AccessFailure, Client

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def source_events(snapshot):
    meta, config = read(snapshot / "snapshot.json"), read(snapshot / "config.json")
    rows = []
    for obj in meta["provenance"]["source_identity"]["objects"]:
        if obj["path"] != "/stocks/filings/8-K/vX/disclosures":
            continue
        candidates = list((ROOT / "data/cache/discovery/downloads").glob(f"*/{obj['object_id']}.json"))
        candidate = next((p for p in candidates if hashlib.sha256(p.read_bytes()).hexdigest() == obj["sha256"]), None)
        if candidate is None:
            raise ValueError("A retained disclosure source is missing or corrupt")
        for row in read(candidate):
            if set(row.get("tickers") or []) & set(config["tickers"]):
                if not row.get("cik") or not row.get("accession_number"):
                    raise ValueError("Lead event requires verified CIK and accession")
                rows.append(row)
    return rows, config


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-requests", type=int, default=70)
    args = p.parse_args()
    if not 1 <= args.max_requests <= 100:
        raise ValueError("Context request cap must be 1–100")
    leads, c = source_events(args.snapshot)
    if c["start"] != "2024-01-01" or c["end"] != "2025-12-31":
        raise ValueError("This follow-up preserves the 2024–2025 development window")
    issuers = sorted({str(r["cik"]).zfill(10) for r in leads})
    args.output.mkdir(parents=True, exist_ok=True)
    attempt = args.output / ("requests-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    attempt.mkdir()
    key = os.getenv("MASSIVE_API_KEY") or dotenv_values(ROOT / ".env").get("MASSIVE_API_KEY")
    if not key:
        raise ValueError("MASSIVE_API_KEY is not configured")
    client = Client(key, attempt, args.max_requests)
    report = {"complete": False, "scope": "All tags for existing lead issuers, 2024–2025; no expanded universe or statistical analysis",
              "issuers": issuers, "lead_rows": len(leads), "objects": [], "errors": []}
    all_rows = []
    for cik in issuers:
        obj, receipt = args.output / f"{cik}.json", args.output / f"{cik}.receipt.json"
        if obj.exists() and receipt.exists():
            saved = read(receipt)
            if hashlib.sha256(obj.read_bytes()).hexdigest() != saved["sha256"]:
                raise ValueError("Retained context bytes changed")
            rows = read(obj)
        else:
            start_index = len(client.receipts)
            try:
                rows = client.pages("Issuer context " + cik, "/stocks/filings/8-K/vX/disclosures",
                                    {"cik": cik, "filing_date.gte": c["start"], "filing_date.lte": c["end"], "limit": 1000, "sort": "filing_date.asc"})
            except AccessFailure as error:
                report["errors"].append({"cik": cik, "reason": str(error)})
                break
            if any(str(r.get("cik", "")).zfill(10) != cik or not c["start"] <= r.get("filing_date", "") <= c["end"] for r in rows):
                raise ValueError("Context response violates issuer/development scope")
            write(obj, rows)
            saved = {"sha256": hashlib.sha256(obj.read_bytes()).hexdigest(), "cik": cik, "rows": len(rows),
                     "requests": client.receipts[start_index:]}
            write(receipt, saved)
        all_rows.extend(rows)
        report["objects"].append({"file": obj.name, **saved})
        write(args.output / "download-report.json", report)
    report["complete"] = len(report["objects"]) == len(issuers)
    report["requests"] = client.receipts
    if report["complete"]:
        tags = {}
        for row in all_rows:
            if row.get("accession_number") and row.get("tertiary_category"):
                k = str(row["cik"]).zfill(10) + ":" + row["accession_number"]
                tags.setdefault(k, set()).add(row["tertiary_category"])
        lead_context = []
        for row in leads:
            k = str(row["cik"]).zfill(10) + ":" + row["accession_number"]
            lead_context.append({**row, "same_filing_categories": sorted(tags.get(k, set())),
                                 "context_join": "CIK + accession", "context_found": k in tags})
        write(args.output / "lead-context.json", lead_context)
        report.update(context_rows=len(all_rows), context_filings=len(tags),
                      unmatched_leads=sum(not r["context_found"] for r in lead_context),
                      lead_context_sha256=hashlib.sha256((args.output / "lead-context.json").read_bytes()).hexdigest())
    write(args.output / "download-report.json", report)
    print(json.dumps({"complete": report["complete"], "issuers": len(issuers), "requests": len(client.receipts),
                      "context_rows": report.get("context_rows"), "receipt": str(args.output / "download-report.json")}))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
