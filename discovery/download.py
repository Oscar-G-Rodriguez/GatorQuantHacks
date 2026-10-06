"""Single, rate-limited Massive controller; cached objects survive partial runs."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from urllib.parse import quote

import pandas as pd
from dotenv import dotenv_values

from .data import snapshot, validate_config
from .io import ROOT, digest, identity, now, read_json, write_json


def client_types():
    # Reuse the inspected, bounded HTTP client without executing its CLI.
    spec = importlib.util.spec_from_file_location("coverage_client", ROOT / "tools/check_massive_coverage.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Client, module.AccessFailure


def download(config_path, snapshot_path, max_requests=20):
    c = validate_config(read_json(config_path))
    if not 1 <= max_requests <= 1000:
        raise ValueError("Request budget must be between 1 and 1000")
    key = os.getenv("MASSIVE_API_KEY") or dotenv_values(ROOT / ".env").get("MASSIVE_API_KEY")
    if not key or key.lower().startswith(("your_", "replace_", "paste_")):
        raise ValueError("Set MASSIVE_API_KEY locally in root .env")
    Client, AccessFailure = client_types()
    cache = ROOT / "data/cache/discovery/downloads" / identity(c)[:16]
    cache.mkdir(parents=True, exist_ok=True)
    attempt = cache / "requests" / now().replace(":", "").replace("+", "_")
    attempt.mkdir(parents=True)
    client = Client(key.strip(), attempt, max_requests)
    report = {"config_id": identity(c), "started_at": now(), "complete": False, "cached_objects": [], "objects": [], "request_cap": max_requests}

    def pages(label, path, params):
        request_id = identity({"path": path, "params": params})
        obj = cache / f"{request_id}.json"
        receipt_path = cache / f"{request_id}.receipt.json"
        # Endpoint/date objects can be reused across universe/resample configs.
        # Only completed objects with verified bytes qualify; never partial pages.
        if not obj.exists():
            for existing in sorted(cache.parent.glob(f"*/{request_id}.json")):
                candidate_receipt = existing.with_suffix(".receipt.json")
                if candidate_receipt.exists():
                    saved = read_json(candidate_receipt)
                    if saved["sha256"] != digest(existing):
                        raise ValueError("Previously cached download hash changed")
                    obj.write_bytes(existing.read_bytes())
                    saved["source_receipts"] = os.path.relpath(existing.parent / saved["source_receipts"], cache).replace("\\", "/")
                    write_json(receipt_path, saved)
                    break
        if obj.exists() and receipt_path.exists():
            receipt = read_json(receipt_path)
            if digest(obj) != receipt["sha256"]:
                raise ValueError("Cached download hash changed")
            report["cached_objects"].append(request_id)
            report["objects"].append({"object_id": request_id, **receipt})
            return read_json(obj)
        # Partial pages never become a completed cache object. Their original
        # bytes/HTTP receipts survive and the bounded attempt is still reported.
        rows = client.pages(label, path, params)
        write_json(obj, rows)
        receipt = {"sha256": digest(obj), "path": path, "params": params, "retrieved_at": now(), "rows": len(rows), "source_receipts": os.path.relpath(attempt, cache).replace("\\", "/")}
        write_json(receipt_path, receipt)
        report["objects"].append({"object_id": request_id, **receipt})
        return rows

    try:
        taxonomy = pages("Disclosure taxonomy", "/stocks/taxonomies/vX/disclosures", {"limit": 1000})
        if not set(c["categories"]) <= {r.get("tertiary_category") for r in taxonomy}:
            raise ValueError("Category absent from the retrieved taxonomy")
        disclosures = []
        for cat in c["categories"]:
            disclosures += pages(f"Development disclosures {cat}", "/stocks/filings/8-K/vX/disclosures", {"tertiary_category": cat, "filing_date.gte": c["start"], "filing_date.lte": c["end"], "limit": 1000, "sort": "filing_date.asc"})
        events, missing_mapping = [], 0
        for row in disclosures:
            if not c["start"] <= row.get("filing_date", "") <= c["end"]:
                raise ValueError("Disclosure outside development window")
            if row.get("tickers") is not None and not isinstance(row["tickers"], list):
                raise ValueError("Unexpected disclosure ticker mapping")
            missing_mapping += not bool(row.get("tickers"))
            for ticker in set(row.get("tickers") or []) & set(c["tickers"]):
                events.append({"ticker": ticker, "issuer": str(row.get("cik") or ticker), "filing_date": row["filing_date"], "available_date": (pd.Timestamp(row["filing_date"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "accession": row.get("accession_number"), "category": row.get("tertiary_category")})
        bars = []
        for ticker in list(dict.fromkeys(c["tickers"] + [c["benchmark"]])):
            rows = pages(f"Daily development bars {ticker}", f"/v2/aggs/ticker/{quote(ticker, safe='')}/range/1/day/{c['start']}/{c['end']}", {"adjusted": "true", "sort": "asc", "limit": 50000})
            if not rows:
                raise AccessFailure(f"Accepted price query has no bars for {ticker}; resolve coverage before analysis")
            for row in rows:
                d = pd.Timestamp(row["t"], unit="ms", tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d")
                bars.append({"ticker": ticker, "date": d, "close": row["c"], "volume": row["v"]})
        source_identity = {"config_id": identity(c), "objects": report["objects"]}
        provenance = {"provider": "Massive standard REST", "created_at": now(), "synthetic": False, "source_identity": source_identity, "universe": c["universe_description"], "missing_disclosure_ticker_lists": missing_mapping, "all_market_disclosure_rows": len(disclosures), "availability": "RETROSPECTIVE labels; filing+1 calendar day is an assumption, not verified historical vendor availability", "entitlement": "Only the specific completed endpoint/date queries succeeded; no new paid plan or x402 route"}
        meta = snapshot(snapshot_path, pd.DataFrame(bars), pd.DataFrame(events), c, provenance)
        report.update(complete=True, snapshot_id=meta["snapshot_id"], snapshot_path=str(snapshot_path))
    except Exception as error:
        report["error"] = str(error) if isinstance(error, (ValueError, AccessFailure)) else f"Unexpected source structure ({type(error).__name__}); inspect ignored cache"
        raise
    finally:
        report.update(finished_at=now(), requests=client.receipts)
        write_json(attempt / "download-report.json", report)
        print(f"Download receipt: {attempt / 'download-report.json'}", flush=True)
    return report


def synthetic(config_path, snapshot_path):
    """Generated prices/events verify machinery, never support an economic claim."""
    import numpy as np
    c = validate_config(read_json(config_path))
    rng = np.random.default_rng(c["seed"])
    dates = pd.bdate_range(c["start"], c["end"])
    market = rng.normal(.0002, .008, len(dates))
    bars, events = [], []
    for k, ticker in enumerate(c["tickers"] + [c["benchmark"]]):
        ret = market.copy() if ticker == c["benchmark"] else market * .7 + rng.normal(0, .012, len(dates))
        close = 100 * np.cumprod(1 + ret)
        bars.extend({"ticker": ticker, "date": str(d.date()), "close": float(p), "volume": float(v)} for d, p, v in zip(dates, close, rng.integers(100000, 1000000, len(dates))))
        if ticker != c["benchmark"]:
            for j in range(25, len(dates) - 25, 11):
                for offset, cat in enumerate(c["categories"]):
                    i = j + offset * 4
                    events.append({"ticker": ticker, "issuer": ticker, "filing_date": str(dates[i].date()), "available_date": str((dates[i] + pd.Timedelta(days=1)).date()), "accession": f"synthetic-{k}-{j}-{offset}", "category": cat})
    return snapshot(snapshot_path, pd.DataFrame(bars), pd.DataFrame(events), c, {"synthetic": True, "created_at": now(), "source": "Deterministic engineering fixture; business-day grid is not an exchange calendar"})
