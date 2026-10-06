"""Scheduled, outcome-blind H22 preparation and fixed research helpers.

This module belongs to the registration 8c3e4e4. It intentionally constructs
market controls from prices, never from H21's precomputed future targets.
"""
from __future__ import annotations

from bisect import bisect_left
import csv
import json
import math
import os
from pathlib import Path
import re

import exchange_calendars as xc
import numpy as np
import pandas as pd

from discovery.io import digest, identity, read_json, write_json, now

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REGISTRATION = "8c3e4e43bceed5ffc0b170c7aa6fcfab2a2ed5a8"


def scheduled():
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("H22 scientific preparation/backtests require a scheduled HiPerGator job")


def csv_write(path, rows, fields=None):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def verify_manifest(run):
    run = Path(run); m = read_json(run / "manifest.json")
    if m["registration_commit"] != REGISTRATION:
        raise ValueError("Wrong H22 registration")
    if m["manifest_id"] != identity({k:v for k,v in m.items() if k != "manifest_id"}):
        raise ValueError("Manifest identity changed")
    for relative, h in m["files"].items():
        p = (ROOT / relative).resolve()
        if not p.is_relative_to(ROOT) or digest(p) != h:
            raise ValueError("Frozen member changed: " + relative)
    return m


def receipt(run, stage, files, extra=None):
    m = verify_manifest(run); run = Path(run)
    write_json(run / "receipts" / (stage + ".json"), {
        "manifest_id":m["manifest_id"], "job_id":os.environ.get("SLURM_JOB_ID"),
        "completed_at":now(), "status":"completed",
        "files":{str(Path(p).relative_to(run)).replace("\\","/"):digest(p) for p in files},
        **(extra or {})})


def classification(text):
    """Fixed conservative completion/receipt coding, with qualifying evidence."""
    if not text or not str(text).strip():
        return "unknown", "missing_excerpt"
    text = re.sub(r"\s+", " ", str(text)).strip()
    clauses = re.split(r"(?<=[.!?;])\s+", text)
    debt = re.compile(r"\b(notes?|bonds?|debentures?|debt|senior secured|senior unsecured)\b", re.I)
    completion = re.compile(r"\b(completed|closed|consummated|issued|sold)\b", re.I)
    receipt_word = re.compile(r"\b(received|receipt|raised|funded)\b", re.I)
    funds = re.compile(r"\b(proceeds|funding|financing)\b", re.I)
    conditional = re.compile(r"\b(will|expects?|intends?|plans?|proposed|if|not|no|never)\b|subject to|upon completion", re.I)
    good = [not conditional.search(c) for c in clauses]
    for i, c in enumerate(clauses):
        if not good[i] or not debt.search(c) or not completion.search(c):
            continue
        for j in [i, i-1, i+1]:
            if 0 <= j < len(clauses) and good[j] and receipt_word.search(clauses[j]) and funds.search(clauses[j]):
                return "completed", c if i == j else c + " " + clauses[j]
    # Future maturity/interest clauses do not make an already completed sale a
    # planned financing. Such text lacks our explicit-receipt evidence and is
    # unknown, rather than a valid planned-only negative control.
    if any(good[i] and debt.search(c) and completion.search(c) for i,c in enumerate(clauses)):
        return "unknown", "completion_without_explicit_receipt_wording"
    if conditional.search(text) and debt.search(text):
        return "planned", "no_unqualified_completion_and_receipt"
    return "unknown", "insufficient_affirmative_completion_and_receipt"


def bar_map(rows):
    result = {}
    for r in rows:
        day = pd.Timestamp(r["t"], unit="ms", tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d")
        if day in result:
            raise ValueError("Duplicate session bar")
        if r.get("c", 0) > 0:
            result[day] = r
    return result


def collect_debt(seen, issuer, ticker, r, session):
    """Many category excerpts in one accession remain one filing signal."""
    key=(issuer,r.get("accession_number"))
    if key in seen:
        if seen[key]["filing_date"] != r["filing_date"]:
            raise ValueError("Conflicting date for one filing identity")
        text=r.get("supporting_text")
        if text not in seen[key]["excerpts"]:seen[key]["excerpts"].append(text)
    else:
        seen[key]={"issuer":issuer,"ticker":ticker,"accession":r.get("accession_number"),
                   "filing_date":r["filing_date"],"session":session,"excerpts":[r.get("supporting_text")]}


def source_objects(run):
    run = Path(run); s = read_json(run / "input/source/source.json")
    if not s.get("complete"):
        raise ValueError("H21 source acquisition was incomplete")
    objects = {}
    for key, o in s["objects"].items():
        p = run / "input/source" / o["file"]
        if not o.get("complete") or digest(p) != o["sha256"]:
            raise ValueError("H21 object not complete or changed")
        objects[key] = read_json(p)
    return s, objects


def prior_features(stock, spy, dates):
    """At each close, controls use that close and earlier observed closes only."""
    close = pd.Series({d: r["c"] for d,r in stock.items()}).reindex(dates)
    volume = pd.Series({d: r.get("v",np.nan) for d,r in stock.items()}).reindex(dates)
    market = pd.Series({d: r["c"] for d,r in spy.items()}).reindex(dates)
    ret = close.pct_change(fill_method=None); mr = market.pct_change(fill_method=None)
    frame = pd.DataFrame({
        "momentum":close / close.shift(21)-1,
        "volatility":np.sqrt(ret.pow(2).rolling(21, min_periods=21).mean()),
        "volume_state":np.log(volume / volume.rolling(21,min_periods=21).mean()),
        "market_momentum":market / market.shift(21)-1,
        "market_volatility":np.sqrt(mr.pow(2).rolling(21,min_periods=21).mean())}, index=dates)
    # Missing sessions are not collapsed into a shorter 21-session interval.
    frame.loc[close.rolling(22,min_periods=22).count().lt(22),:] = np.nan
    return frame


def control_match(features, i, excluded, dates):
    if i < 84 or not np.isfinite(features.iloc[i].to_numpy()).all():
        return None, "insufficient_prior_features"
    training = features.iloc[:i].dropna()
    scale = training.std(ddof=0).to_numpy()
    if len(training) < 21 or not np.isfinite(scale).all():
        return None, "insufficient_past_scale"
    scale = np.maximum(scale, 1e-8)
    choices = []
    for j in range(max(21,i-252),i-83):
        if any(k in excluded for k in range(j-4,j+1)):
            continue
        diff = (features.iloc[j].to_numpy()-features.iloc[i].to_numpy())/scale
        if np.isfinite(diff).all() and np.max(np.abs(diff)) <= 2:
            choices.append((float(np.mean(diff**2)), -j, j))
    if not choices:
        return None, "no_prior_control_within_calipers"
    distance, _, j = min(choices)
    return j, distance


def prepare(run):
    scheduled(); m = verify_manifest(run); run = Path(run); cfg = read_json(HERE / "settings.json")
    s, objects = source_objects(run)
    cal = xc.get_calendar("XNYS",start=cfg["start"],end=cfg["end"])
    dates = [x.strftime("%Y-%m-%d") for x in cal.sessions]
    clock = {d:{"open_ns":int(cal.session_open(d).value),"close_ns":int(cal.session_close(d).value)} for d in dates}
    stocks = {}; spy = {}; actions = {}; raw = []; seen = {}
    for key, o in s["objects"].items():
        path = o["path"]
        if "/aggs/ticker/" in path and o["params"].get("adjusted") == "true":
            ticker = path.split("/ticker/")[1].split("/range/")[0]
            target = stocks.setdefault(ticker,{})
            for day, b in bar_map(objects[key]).items():
                if day in target and target[day] != b: raise ValueError("Conflicting cached stock bars")
                target[day] = b
        if path in {"/v3/reference/dividends","/v3/reference/splits"}:
            a = actions.setdefault(o["params"]["ticker"],{"dividends":[],"splits":[]})
            a[path.rsplit("/",1)[1]] += objects[key]
    spy = stocks["SPY"]
    issuer_ticker = {}
    for ticker, entry in sorted(s["mapping"].items()):
        if entry.get("cik"): issuer_ticker.setdefault(entry["cik"],ticker)
    filing_sessions = {}
    for c in s["disclosure_collections"]:
        ticker = issuer_ticker.get(c["cik"])
        for r in objects[c["object_id"]]:
            i = bisect_left(dates, (pd.Timestamp(r["filing_date"])+pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
            filing_sessions.setdefault(c["cik"],set()).add(i)
            if r.get("tertiary_category") != "debt_issuance": continue
            collect_debt(seen,c["cik"],ticker,r,i)
    for entry in seen.values():
        text=" ".join(str(t) for t in entry["excerpts"] if t)
        status,evidence=classification(text)
        raw.append({**entry,"text":text or None,"status":status,"evidence":evidence})
    features = {t:prior_features(stocks.get(t,{}),spy,dates) for t in set(issuer_ticker.values())}
    anchors = []; exclusions = []; groups = {}; repeats = {}
    for r in sorted(raw,key=lambda r:(r["session"],r["issuer"],str(r["accession"]))):
        if r["status"] not in {"completed","planned"}: continue
        if not r["ticker"] or r["session"]+1 >= len(dates):
            exclusions.append({**r,"reason":"mapping_or_clock_unavailable"});continue
        text_id = identity(re.sub(r"\s+"," ",str(r["text"])).strip().lower())
        repeat_key = (r["issuer"],text_id)
        if r["status"] == "completed" and repeat_key in repeats and r["session"]-repeats[repeat_key] <= 63:
            exclusions.append({**r,"reason":"suspected_repeated_completion_excerpt"});continue
        repeats[repeat_key] = r["session"]
        groups.setdefault((r["issuer"],r["session"],r["status"]),[]).append(r)
    for (issuer,i,status), filings in groups.items():
        ticker = filings[0]["ticker"]; pair_id = identity([issuer,i,status])[:20]
        j, distance = control_match(features[ticker],i,filing_sessions[issuer],dates)
        base = {"pair_id":pair_id,"issuer":issuer,"ticker":ticker,"event_status":status,
            "filing_date":min(r["filing_date"] for r in filings),"accessions":sorted(r["accession"] for r in filings),
            "match_distance":distance,"event_decision":dates[i]}
        roles = [("event" if status == "completed" else "planned",i)]
        if j is not None:
            roles.append(("ordinary",j))
            if j-21 >= 21: roles.append(("shifted",j-21))
        else: exclusions.append({**base,"reason":distance})
        for variant in cfg["variants"]:
            for role,k in roles:
                di = k + variant["delay"]
                if di+1 >= len(dates):
                    exclusions.append({**base,"variant":variant["id"],"role":role,"reason":"entry_outside_history"});continue
                f = features[ticker].iloc[di]
                if not np.isfinite(f.to_numpy()).all():
                    exclusions.append({**base,"variant":variant["id"],"role":role,"reason":"missing_prior_controls"});continue
                anchors.append({**base,"variant":variant["id"],"role":role,
                    "date":dates[di],"entry_date":dates[di+1],"session":di,"entry_session":di+1,
                    "features":{key:float(val) for key,val in f.items()}})
    out = run / "prepared"; out.mkdir(exist_ok=True)
    write_json(out / "anchors.json",anchors);write_json(out / "calendar.json",{"dates":dates,"clock":clock})
    write_json(out / "actions.json",actions);write_json(out / "coding.json",raw)
    csv_write(out / "exclusions.csv",exclusions or [{"reason":"none"}])
    audit=[]
    for positive in [True,False]:
        group=[r for r in raw if (r["status"] == "completed") == positive]
        audit.extend(sorted(group,key=lambda r:identity([cfg["seed"],r["issuer"],r["accession"]]))[:30])
    csv_write(out / "completion-audit.csv",audit)
    coverage=[]
    for year in range(2022,2026):
        for status in ["completed","planned","unknown"]:
            rows=[r for r in raw if r["filing_date"].startswith(str(year)) and r["status"] == status]
            coverage.append({"year":year,"classification":status,"filings":len(rows),"issuers":len({r["issuer"] for r in rows})})
    csv_write(out / "coverage.csv",coverage)
    files=list(out.glob("*"));receipt(run,"prepare",files,{"filings":len(raw),"anchors":len(anchors),"clock_assumed":True})
    print(json.dumps({"stage":"prepare","coverage":coverage,"anchors":len(anchors)},indent=2),flush=True)


def choose_call(rows, when, spot, variant):
    """Identity/maturity/moneyness selection; no subsequent bar access."""
    unique = {}
    for r in rows:
        if r.get("ticker") in unique and unique[r["ticker"]] != r:
            raise ValueError("Conflicting contract identity")
        unique[r.get("ticker")] = r
    calls=[]
    for r in unique.values():
        if (r.get("contract_type") != "call" or r.get("shares_per_contract") != 100
                or r.get("additional_underlyings") or r.get("exercise_style") not in {"american","european"}):continue
        dte = (pd.Timestamp(r["expiration_date"])-pd.Timestamp(when)).days
        if variant["range"][0] <= dte <= variant["range"][1]: calls.append(r)
    if not calls: return None
    expiry = min({r["expiration_date"] for r in calls},key=lambda d:(abs((pd.Timestamp(d)-pd.Timestamp(when)).days-variant["dte"]),d))
    chosen = min((r for r in calls if r["expiration_date"] == expiry),key=lambda r:(abs(float(r["strike_price"])-spot*(1+variant["otm"])),float(r["strike_price"]),r["ticker"]))
    if abs(float(chosen["strike_price"])/spot-1-variant["otm"]) > .0100000001: return None
    return chosen
