"""Local historical option acquisition and preparation under the H12–H17 plan.

This module downloads and aligns data; scientific fits belong in compute jobs.
Immutable completed request objects permit resume without losing raw evidence.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import quote

import exchange_calendars as xc
import numpy as np
import pandas as pd
from dotenv import dotenv_values

from .download import client_types
from .io import ROOT, digest, identity, now, read_json, write_json

START, END = "2024-01-01", "2025-12-31"
BUCKETS = {"30": (21, 45, 30), "60": (46, 80, 60), "120": (90, 180, 120)}
HORIZONS = [1, 2, 3, 5, 10, 21, 42, 63]
BUFFERS = [1, 3, 5]
PLAN_COMMITS = ["197e8a050b15f2ca09d68b5b835b4393cfa6708f", "590ee72ca8e1475d80ade565c27a00ce2c7bc00f",
                "a4a9684f778ae8dc67bda5b4f64d82d026e21b99"]


def calendar():
    return xc.get_calendar("XNYS", start=START, end=END)


def session_dates():
    return [d.strftime("%Y-%m-%d") for d in calendar().sessions if START <= d.strftime("%Y-%m-%d") <= END]


def anchors(leads, universe, dates):
    """Retain lead identities and prior ordinary anchors without future controls."""
    ds = np.array(dates)
    by_identity, event_sessions = {}, {}
    for r in leads:
        if not START <= r["filing_date"] <= END:
            raise ValueError("Lead is outside development")
        for ticker in sorted(set(r.get("tickers") or []) & set(universe)):
            key = (ticker, str(r["cik"]).zfill(10), r["accession_number"])
            item = by_identity.setdefault(key, {"ticker": ticker, "issuer": key[1], "accession": key[2],
                                                "filing_date": r["filing_date"], "categories": [],
                                                "same_filing_categories": r["same_filing_categories"]})
            if item["filing_date"] != r["filing_date"]:
                raise ValueError("One filing has conflicting dates")
            item["categories"].append(r["tertiary_category"])
            e = int(ds.searchsorted(r["filing_date"]))
            event_sessions.setdefault(ticker, set()).add(e)
    rows, excluded = [], []
    for key, r in sorted(by_identity.items(), key=lambda x: (x[1]["filing_date"], x[0])):
        pre_i = int(ds.searchsorted(r["filing_date"])) - 1
        available = (pd.Timestamp(r["filing_date"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        first_i = int(ds.searchsorted(available))
        if pre_i < 0 or first_i >= len(ds):
            excluded.append({**r, "reason": "pre_or_assumed_availability_outside_development"})
            continue
        aid = identity(list(key))[:20]
        base = {**r, "categories": sorted(set(r["categories"])), "event_id": aid}
        rows.append({**base, "anchor_id": aid + "-event", "cohort": "event", "pre": dates[pre_i],
                     "pre_session": pre_i, "first_assumed_session": first_i,
                     "observations": {str(b): dates[first_i+b] if first_i+b < len(ds) else None for b in BUFFERS}})
        control_i = pre_i - 84
        if control_i < 0 or any(abs(control_i-e) <= 5 for e in event_sessions[r["ticker"]]):
            excluded.append({**base, "reason": "prior_ordinary_anchor_unavailable_or_near_lead"})
        else:
            # Ordinary observations use exactly the same offset from pre as the event.
            control_first = control_i + first_i - pre_i
            rows.append({**base, "anchor_id": aid + "-ordinary", "cohort": "ordinary", "pre": dates[control_i],
                         "pre_session": control_i, "first_assumed_session": control_first,
                         "observations": {str(b): dates[control_first+b] if control_first+b < len(ds) else None for b in BUFFERS}})
    return rows, excluded


def select_pairs(contracts, pre, spot):
    """Select by historical reference and pre-date spot, before later prices."""
    if not np.isfinite(spot) or spot <= 0:
        return {}, {b: "missing_unadjusted_pre_spot" for b in BUCKETS}
    pairs = {}
    for r in contracts:
        if r.get("contract_type") not in {"call", "put"}:
            continue
        if r.get("shares_per_contract") != 100 or r.get("additional_underlyings"):
            continue
        expiry = r["expiration_date"]
        dte = (pd.Timestamp(expiry) - pd.Timestamp(pre)).days
        if 21 <= dte <= 180:
            key = (expiry, float(r["strike_price"]))
            group = pairs.setdefault(key, {})
            leg = r["contract_type"]
            if leg in group and group[leg]["ticker"] != r["ticker"]:
                raise ValueError("Ambiguous paired contract identity")
            group[leg] = r
    selected, excluded = {}, {}
    for b, (lo, hi, target) in BUCKETS.items():
        eligible = [(k, v) for k, v in pairs.items() if set(v) == {"call", "put"}
                    and lo <= (pd.Timestamp(k[0])-pd.Timestamp(pre)).days <= hi]
        if not eligible:
            excluded[b] = "no_standard_paired_contract_in_bucket"
            continue
        (expiry, strike), legs = min(eligible, key=lambda kv: (
            abs((pd.Timestamp(kv[0][0])-pd.Timestamp(pre)).days-target),
            kv[0][0], abs(kv[0][1]/spot-1), kv[0][1]))
        selected[b] = {"expiry": expiry, "strike": strike, "stock_spot": spot,
                       "selection_moneyness": strike/spot, "legs": legs,
                       "dte": (pd.Timestamp(expiry)-pd.Timestamp(pre)).days}
    return selected, excluded


class Cache:
    def __init__(self, folder, cap, minimum_interval=12.5):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.attempt = self.folder / "requests" / now().replace(":", "").replace("+", "_")
        self.attempt.mkdir(parents=True)
        self.prior_count = sum(len(read_json(p).get("requests", [])) for p in self.folder.glob("attempt-*.json"))
        self.cap = cap
        key = os.getenv("MASSIVE_API_KEY") or dotenv_values(ROOT/".env").get("MASSIVE_API_KEY")
        if not key:
            raise ValueError("MASSIVE_API_KEY is not configured")
        Client, self.access_failure = client_types()
        self.client = Client(key.strip(), self.attempt, max(0, cap-self.prior_count),
                             minimum_interval=minimum_interval, separate_buckets=True)
        for p in self.folder.glob("attempt-*.json"):
            for receipt in read_json(p).get("requests", []):
                if receipt.get("http_status") == 429 and receipt.get("pacing_bucket"):
                    self.client.bucket_intervals[receipt["pacing_bucket"]] = 12.5
        self.used = {}

    def pages(self, label, path, params, paginate=True):
        spec = {"path": path, "params": params, "paginate": paginate}
        rid = identity(spec)
        obj, receipt = self.folder/f"{rid}.json", self.folder/f"{rid}.receipt.json"
        if obj.exists() and receipt.exists():
            saved = read_json(receipt)
            if digest(obj) != saved["sha256"] or saved["spec"] != spec:
                raise ValueError("Cached option request changed")
            rows = read_json(obj)
        else:
            start = len(self.client.receipts)
            try:
                rows = self.client.pages(label, path, params) if paginate else (self.client.get(label, path, params).get("results") or [])
            finally:
                write_json(self.folder/f"attempt-{self.attempt.name}.json", {"requests": self.client.receipts})
            write_json(obj, rows)
            saved = {"spec": spec, "sha256": digest(obj), "rows": len(rows), "retrieved_at": now(),
                     "source_receipts": self.client.receipts[start:]}
            write_json(receipt, saved)
        self.used[rid] = saved
        return rows


def download(context_path, snapshot_path, output, cap=2000, minimum_interval=12.5):
    from .data import load_snapshot
    panel, sm, config = load_snapshot(snapshot_path)
    report = read_json(Path(context_path)/"download-report.json")
    if not report["complete"] or digest(Path(context_path)/"lead-context.json") != report["lead_context_sha256"]:
        raise ValueError("Context source is incomplete or changed")
    if config["start"] != START or config["end"] != END or not 1 <= cap <= 2000:
        raise ValueError("Acquisition scope changed")
    ds = session_dates()
    rows, exclusions = anchors(read_json(Path(context_path)/"lead-context.json"), config["tickers"], ds)
    cache = Cache(output, cap, minimum_interval)
    previous = Path(output)/"download.json"
    if previous.exists():
        archived = Path(output)/"checkpoint-history"/(cache.attempt.name+".json")
        archived.parent.mkdir(parents=True, exist_ok=True)
        archived.write_bytes(previous.read_bytes())
    result = {"schema": 1, "started_at": now(), "complete": False, "plan_commits": PLAN_COMMITS,
              "source_snapshot_id": sm["snapshot_id"], "context_hash": digest(Path(context_path)/"lead-context.json"),
              "sessions": ds, "anchors": [], "exclusions": exclusions, "objects": {}, "errors": [],
              "transport": {"requested_minimum_interval_seconds":minimum_interval,
                            "separate_pacing_buckets":True, "resumed_prior_requests":cache.prior_count}}
    stocks = {}
    try:
        for t in sorted({r["ticker"] for r in rows}):
            bars = cache.pages("Unadjusted stock "+t, f"/v2/aggs/ticker/{quote(t, safe='')}/range/1/day/{START}/{END}",
                               {"adjusted": "false", "sort": "asc", "limit": 50000})
            stocks[t] = {pd.Timestamp(b["t"], unit="ms", tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d"):b["c"] for b in bars}
        for a in rows:
            pre, spot = a["pre"], stocks[a["ticker"]].get(a["pre"], np.nan)
            if not np.isfinite(spot):
                result["anchors"].append({**a, "selected": {}, "bucket_exclusions": {b:"missing_pre_stock" for b in BUCKETS}})
                continue
            # Narrow strikes bound paging; completeness is local to this declared band.
            contracts = cache.pages("Historical chain "+a["anchor_id"], "/v3/reference/options/contracts", {
                "underlying_ticker": a["ticker"], "as_of": pre, "expired": "false", "limit":1000,
                "expiration_date.gte":(pd.Timestamp(pre)+pd.Timedelta(days=21)).strftime("%Y-%m-%d"),
                "expiration_date.lte":(pd.Timestamp(pre)+pd.Timedelta(days=180)).strftime("%Y-%m-%d"),
                "strike_price.gte":round(spot*.95, 4), "strike_price.lte":round(spot*1.05, 4)})
            selected, missing = select_pairs(contracts, pre, spot)
            for bucket, s in selected.items():
                first = ds[max(0, a["pre_session"]-10)]
                last_i = min(len(ds)-1, a["first_assumed_session"]+max(BUFFERS)+max(HORIZONS))
                last = min(ds[last_i], s["expiry"], END)
                for leg, contract in s["legs"].items():
                    path = f"/v2/aggs/ticker/{quote(contract['ticker'], safe='')}/range/1/day/{first}/{last}"
                    bars = cache.pages("Option bars "+a["anchor_id"]+" "+bucket+" "+leg, path,
                                       {"adjusted":"false", "sort":"asc", "limit":50000})
                    s.setdefault("bar_objects", {})[leg] = identity({"path":path,"params":{"adjusted":"false","sort":"asc","limit":50000},"paginate":True})
                    if any(not first <= pd.Timestamp(b["t"],unit="ms",tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d") <= last for b in bars):
                        raise ValueError("Option bars outside requested development interval")
                if bucket == "120":
                    close, opening = calendar().session_close(pre), calendar().session_open(pre)
                    s["quote_cutoff_ns"] = int(close.value)
                    for leg, contract in s["legs"].items():
                        params = {"timestamp.gte":int(opening.value), "timestamp.lte":int(close.value),
                                  "sort":"timestamp","order":"desc","limit":1}
                        qr = cache.pages("Pre-close quote "+a["anchor_id"]+" "+leg,
                                         "/v3/quotes/"+quote(contract["ticker"],safe=""), params, paginate=False)
                        if qr and not int(opening.value) <= qr[0]["sip_timestamp"] <= int(close.value):
                            raise ValueError("Quote is outside the backward observation cutoff")
                        s.setdefault("pre_quotes", {})[leg] = qr
            result["anchors"].append({**a, "selected":selected, "bucket_exclusions":missing})
            result["objects"] = cache.used
            result["requests"] = cache.prior_count+len(cache.client.receipts)
            write_json(Path(output)/"download.json", result)
            print(f"Prepared anchors {len(result['anchors'])}/{len(rows)}; total requests {result['requests']}", flush=True)
        result["complete"] = len(result["anchors"]) == len(rows)
    except cache.access_failure as error:
        result["errors"].append({"reason":str(error),"at":now()})
    finally:
        result["objects"] = cache.used
        result["requests"] = cache.prior_count+len(cache.client.receipts)
        result["transport"]["final_bucket_intervals"] = cache.client.bucket_intervals
        result["finished_at"] = now()
        write_json(Path(output)/"download.json", result)
    return {"complete":result["complete"],"anchors":len(result["anchors"]),"planned_anchors":len(rows),"requests":result["requests"],"errors":result["errors"]}


def backward_mark(bars, when, sessions, max_age=3):
    """Last completed daily trade bar at/before date, measured in real sessions."""
    candidates = []
    for b in bars:
        d = pd.Timestamp(b["t"],unit="ms",tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d")
        if d <= when and d in sessions and b.get("c",0) > 0:
            candidates.append((d,b))
    if not candidates:
        return None
    d,b = max(candidates,key=lambda x:x[0])
    age = sessions.index(when)-sessions.index(d)
    if age > max_age:
        return None
    return {"price":float(b["c"]),"date":d,"age":age,"volume":float(b.get("v",0)),"bar_start_ms":b["t"]}


def prepare(download_path, output):
    """Freeze normalized sources; option feature/target arithmetic runs remotely."""
    download_path, output = Path(download_path), Path(output)
    r = read_json(download_path/"download.json")
    if not r["complete"]:
        raise ValueError("Incomplete acquisition cannot become the complete study snapshot")
    output.mkdir(parents=True,exist_ok=False)
    bars = {}
    for oid,saved in r["objects"].items():
        p = download_path/f"{oid}.json"
        if digest(p) != saved["sha256"]:
            raise ValueError("Acquired bytes changed")
        if saved["spec"]["path"].startswith("/v2/aggs/ticker/O"):
            bars[oid] = read_json(p)
    write_json(output/"option-sources.json", {"sessions":r["sessions"],"anchors":r["anchors"],"bar_objects":bars,
                                            "exclusions":r["exclusions"],"source_hash":digest(download_path/"download.json")})
    return {"anchors":len(r["anchors"]),"files":{"option-sources.json":digest(output/"option-sources.json")}}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    d=sub.add_parser("download")
    d.add_argument("--context",type=Path,required=True); d.add_argument("--snapshot",type=Path,required=True)
    d.add_argument("--output",type=Path,required=True); d.add_argument("--max-requests",type=int,default=2000)
    d.add_argument("--minimum-interval",type=float,default=12.5)
    s=sub.add_parser("prepare");s.add_argument("--download",type=Path,required=True);s.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    import json
    result=download(a.context,a.snapshot,a.output,a.max_requests,a.minimum_interval) if a.command=="download" else prepare(a.download,a.output)
    print(json.dumps(result))
    return 0 if result.get("complete",True) else 2


if __name__=="__main__":
    raise SystemExit(main())
