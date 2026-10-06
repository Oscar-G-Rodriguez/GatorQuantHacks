"""Outcome-blind scheduled preparation after financing registration b4159e2.

Borrowed infrastructure: H22 funded-study source validation and past matching.
Standard taxonomy membership replaces H22's narrow wording classifier entirely.
"""
from __future__ import annotations

from bisect import bisect_left
import csv
import json
import os
from pathlib import Path
import random

import exchange_calendars as xc
import numpy as np
import pandas as pd

from discovery.io import ROOT, digest, identity, read_json, write_json, now

CONFIG = ROOT / "config/financing-round2.json"
REGISTRATION = "b4159e2917248d588072ef5d9ae55bd88c3f8063"


def scheduled():
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Real financing preparation and calculations require a scheduled HiPerGator allocation")


def csv_write(path, rows, fields=None):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or sorted({k for row in rows for k in row}) or ["status"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def verify_manifest(run):
    m = read_json(Path(run)/"manifest.json")
    if m.get("registration_commit") != REGISTRATION:
        raise ValueError("Registration identity differs")
    if m["manifest_id"] != identity({k:v for k,v in m.items() if k != "manifest_id"}):
        raise ValueError("Manifest content identity differs")
    for relative, expected in m["files"].items():
        target = (ROOT/relative).resolve()
        if not target.is_relative_to(ROOT.resolve()) or digest(target) != expected:
            raise ValueError("Immutable manifest member differs: "+relative)
    return m


def receipt(run, stage, files, extra=None):
    m = verify_manifest(run); run = Path(run)
    write_json(run/"receipts"/(stage+".json"), {
        "manifest_id":m["manifest_id"], "job_id":os.environ.get("SLURM_JOB_ID"),
        "completed_at":now(), "status":"completed",
        "files":{Path(p).relative_to(run).as_posix():digest(p) for p in files}, **(extra or {})})


def normalize_cik(value):
    value = str(value or "").strip()
    return value.zfill(10) if value.isdigit() else None


def bar_map(rows):
    result = {}
    for r in rows:
        d = pd.Timestamp(r["t"], unit="ms", tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d")
        if d in result and result[d] != r:
            raise ValueError("Conflicting duplicate session bar")
        if r.get("c",0) > 0: result[d] = r
    return result


def source_objects(run):
    directory = Path(run)/"input/source"; source = read_json(directory/"source.json")
    if not source.get("complete"): raise ValueError("Disclosure source pagination is incomplete")
    objects = {}
    for key, obj in source["objects"].items():
        target = (directory/obj["file"]).resolve()
        if not target.is_relative_to(directory.resolve()) or not obj.get("complete") or digest(target)!=obj["sha256"]:
            raise ValueError("Disclosure source member incomplete or altered")
        objects[key] = read_json(target)
    return source, objects


def collect_filings(collections, objects, mapping, dates):
    """CIK/accession is the filing; labels/text never create independent copies."""
    issuers = {}; exclusions = []
    for ticker, entry in sorted(mapping.items()):
        cik = normalize_cik(entry.get("cik"))
        if cik:
            if cik in issuers: exclusions.append({"issuer":cik,"ticker":ticker,"reason":"secondary_universe_share_class"})
            else: issuers[cik] = ticker
    seen = {}
    for collection in collections:
        cik = normalize_cik(collection.get("cik"))
        for row in objects[collection["object_id"]]:
            accession = row.get("accession_number")
            if not cik or not accession or not row.get("filing_date"):
                exclusions.append({"issuer":cik,"accession":accession,"reason":"missing_filing_identity_or_date"}); continue
            key = (cik, str(accession))
            release = (pd.Timestamp(row["filing_date"])+pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            if key not in seen:
                seen[key] = {"issuer":cik,"ticker":issuers.get(cik),"accession":str(accession),
                    "filing_date":row["filing_date"],"availability_session":bisect_left(dates,release),
                    "labels":[],"records":[]}
            filing = seen[key]
            if filing["filing_date"] != row["filing_date"]: raise ValueError("Conflicting date for a filing")
            label = row.get("tertiary_category")
            if label and label not in filing["labels"]: filing["labels"].append(label)
            if row not in filing["records"]: filing["records"].append(row)
    for filing in seen.values(): filing["labels"].sort()
    return sorted(seen.values(),key=lambda x:(x["issuer"],x["filing_date"],x["accession"])), issuers, exclusions


def in_study(filing, study):
    return set(study["labels"]).issubset(set(filing["labels"]))


def prior_features(stock, spy, dates):
    close = pd.Series({d:r["c"] for d,r in stock.items()}).reindex(dates)
    volume = pd.Series({d:r.get("v",np.nan) for d,r in stock.items()}).reindex(dates)
    market = pd.Series({d:r["c"] for d,r in spy.items()}).reindex(dates)
    r = close.pct_change(fill_method=None); mr = market.pct_change(fill_method=None)
    frame = pd.DataFrame({"momentum":close/close.shift(21)-1,
        "volatility":np.sqrt(r.pow(2).rolling(21,min_periods=21).mean()),
        "volume_state":np.log(volume.rolling(21,min_periods=21).mean()),
        "market_momentum":market/market.shift(21)-1,
        "market_volatility":np.sqrt(mr.pow(2).rolling(21,min_periods=21).mean())}, index=dates)
    frame.loc[close.rolling(22,min_periods=22).count().lt(22),:] = np.nan
    frame.loc[market.rolling(22,min_periods=22).count().lt(22),:] = np.nan
    return frame


def control_match(features, i, excluded, dates=None, candidates=None, lookback=(84,252), max_z=2):
    if i >= len(features) or i < lookback[0] or not np.isfinite(features.iloc[i].to_numpy()).all():
        return None, "insufficient_prior_features"
    train = features.iloc[:i].dropna()
    if len(train)<21: return None,"insufficient_prior_scale"
    scale = np.maximum(train.std(ddof=0).to_numpy(),1e-8)
    eligible = range(max(21,i-lookback[1]),i-lookback[0]+1) if candidates is None else candidates
    choices = []
    for j in eligible:
        if not 21<=j<i or not lookback[0]<=i-j<=lookback[1]: continue
        if candidates is None and any(k in excluded for k in range(j-4,j+1)): continue
        diff = (features.iloc[j].to_numpy()-features.iloc[i].to_numpy())/scale
        if np.isfinite(diff).all() and np.max(np.abs(diff))<=max_z:
            choices.append((float(np.mean(diff**2)),-j,j))
    if not choices: return None,"no_prior_control_within_calipers"
    distance,_,j = min(choices)
    return j,distance


def choose_contract(rows, when, spot, variant, shape):
    kind = "call" if shape=="covered_call" else "put"
    sign = 1 if kind=="call" else -1
    unique = {}
    for row in rows:
        ticker = row.get("ticker")
        if not ticker: continue
        if ticker in unique and unique[ticker] != row: raise ValueError("Conflicting contract identity")
        unique[ticker] = row
    eligible = []
    for row in unique.values():
        if row.get("contract_type")!=kind or row.get("shares_per_contract")!=100 or row.get("additional_underlyings"):
            continue
        if row.get("exercise_style") not in {"american","european"}: continue
        dte = (pd.Timestamp(row["expiration_date"])-pd.Timestamp(when)).days
        if variant["range"][0]<=dte<=variant["range"][1]: eligible.append(row)
    if not eligible: return None
    expiry = min({r["expiration_date"] for r in eligible},key=lambda d:(abs((pd.Timestamp(d)-pd.Timestamp(when)).days-variant["dte"]),d))
    chosen = min((r for r in eligible if r["expiration_date"]==expiry),
        key=lambda r:(abs(float(r["strike_price"])-spot*(1+sign*variant["otm"])),float(r["strike_price"]),r["ticker"]))
    if abs(float(chosen["strike_price"])/spot-1-sign*variant["otm"])>.0100000001: return None
    return chosen


def placebo_map(filings, cfg):
    """Freeze all shifts before fitting/outcome analysis; never redraw coverage."""
    groups = sorted({(r["issuer"],int(r["filing_date"][:4])) for r in filings})
    rng = random.Random(cfg["seed"])
    return [{"replica":rep,"shifts":[{"issuer":issuer,"year":year,
        "offset":rng.randint(*cfg["placebo_session_offset_range"])} for issuer,year in groups]}
        for rep in range(cfg["timing_placebos"])]


def build_anchors(filings, features, dates, cfg, scope="full", variant_ids=None):
    exclusions = []; coverage = []; anchors = []
    filing_sessions = {}
    for f in filings: filing_sessions.setdefault(f["issuer"],set()).add(f["availability_session"])
    for study in cfg["studies"]:
        cohort = [f for f in filings if in_study(f,study)]
        for year in range(2022,2026):
            subset = [f for f in cohort if f["filing_date"].startswith(str(year))]
            coverage.append({"study":study["id"],"year":year,"filings":len(subset),
                "issuers":len({f["issuer"] for f in subset}),"wording_exclusions":0})
        if scope=="pilot":
            cohort = [f for year in range(2022,2026) for f in
                sorted((f for f in cohort if f["filing_date"].startswith(str(year))),
                    key=lambda f:(f["issuer"],f["accession"]))[:cfg["pilot_events_per_study_year"]]]
        groups = {}
        for f in cohort:
            groups.setdefault((f["issuer"],f["availability_session"]),[]).append(f)
        for (issuer,available), bundle in sorted(groups.items()):
            ticker = bundle[0]["ticker"]
            if not ticker or ticker not in features:
                exclusions.append({"study":study["id"],"issuer":issuer,"reason":"unmapped_or_missing_market_history"});continue
            pair = identity([study["id"],issuer,available,sorted(f["accession"] for f in bundle)])[:24]
            for variant in cfg["variants"]:
                if variant_ids and variant["id"] not in variant_ids: continue
                if scope=="pilot" and [study["id"],variant["id"]] not in cfg["pilot_task_spec"]: continue
                delay = study["delay"]+variant["extra_delay"]; i = available+delay
                base = {"study":study["id"],"issuer":issuer,"ticker":ticker,"pair_id":pair,"variant":variant["id"],
                    "accessions":sorted(f["accession"] for f in bundle),"filing_date":min(f["filing_date"] for f in bundle),
                    "availability_session":available,"event_decision":dates[i] if i<len(dates) else None}
                if i+1>=len(dates): exclusions.append({**base,"reason":"entry_outside_history"});continue
                frame = features[ticker]
                if not np.isfinite(frame.iloc[i].to_numpy()).all():
                    exclusions.append({**base,"reason":"missing_prior_features"});continue
                j,distance = control_match(frame,i,filing_sessions[issuer],dates,lookback=tuple(cfg["ordinary_lookback"]),max_z=cfg["match_max_z"])
                roles = [("event",i,distance)]
                if j is not None: roles.append(("ordinary",j,distance))
                else: exclusions.append({**base,"reason":distance,"role":"ordinary"})
                for label in study.get("component_controls",[]):
                    other = "underwriting_agreement" if label=="debt_issuance" else "debt_issuance"
                    candidates = {f["availability_session"]+delay for f in filings if f["issuer"]==issuer and label in f["labels"] and other not in f["labels"]}
                    k,dist = control_match(frame,i,set(),dates,candidates,tuple(cfg["component_lookback"]),cfg["match_max_z"])
                    role = "debt_only" if label=="debt_issuance" else "underwriting_only"
                    if k is not None: roles.append((role,k,dist))
                    else: exclusions.append({**base,"reason":dist,"role":role})
                for role,k,dist in roles:
                    for shape in cfg["shapes"]:
                        anchor = {**base,"shape":shape,"role":role,"date":dates[k],"entry_date":dates[k+1],
                            "session":k,"entry_session":k+1,"match_distance":dist,
                            "features":{key:float(v) for key,v in frame.iloc[k].items()}}
                        anchor["anchor_id"] = identity([study["id"],pair,variant["id"],shape,role,dates[k]])[:24]
                        anchors.append(anchor)
    return anchors,coverage,exclusions


def prepare(run):
    scheduled(); m = verify_manifest(run); run = Path(run); cfg = read_json(CONFIG)
    source,objects = source_objects(run)
    cal = xc.get_calendar("XNYS",start=cfg["start"],end=cfg["end"])
    dates = [x.strftime("%Y-%m-%d") for x in cal.sessions]
    clock = {d:{"open_ns":int(cal.session_open(d).value),"close_ns":int(cal.session_close(d).value)} for d in dates}
    stocks = {}; actions = {}
    for key,obj in source["objects"].items():
        path = obj["path"]
        if "/aggs/ticker/" in path and obj["params"].get("adjusted")=="true":
            ticker = path.split("/ticker/")[1].split("/range/")[0]
            target = stocks.setdefault(ticker,{})
            for d,row in bar_map(objects[key]).items():
                if d in target and target[d]!=row: raise ValueError("Conflicting adjusted stock observations")
                target[d] = row
        if path in {"/v3/reference/dividends","/v3/reference/splits"}:
            target = actions.setdefault(obj["params"]["ticker"],{"dividends":[],"splits":[]})
            for row in objects[key]:
                if row not in target[path.rsplit("/",1)[1]]: target[path.rsplit("/",1)[1]].append(row)
    if "SPY" not in stocks: raise ValueError("Missing required SPY history")
    filings,mapping,source_exclusions = collect_filings(source["disclosure_collections"],objects,source["mapping"],dates)
    frames = {t:prior_features(stocks.get(t,{}),stocks["SPY"],dates) for t in set(mapping.values())}
    anchors,coverage,exclusions = build_anchors(filings,frames,dates,cfg,m.get("scope","full"))
    out = run/"prepared";out.mkdir(exist_ok=True)
    write_json(out/"anchors.json",anchors);write_json(out/"calendar.json",{"dates":dates,"clock":clock})
    write_json(out/"actions.json",actions);write_json(out/"filings.json",filings)
    write_json(out/"features.json",{t:{d:{k:float(v) if np.isfinite(v) else None for k,v in row.items()} for d,row in f.iterrows()} for t,f in frames.items()})
    write_json(out/"placebo-map.json",placebo_map(filings,cfg))
    csv_write(out/"coverage.csv",coverage);csv_write(out/"exclusions.csv",source_exclusions+exclusions)
    write_json(out/"summary.json",{"scope":m.get("scope","full"),"source_id":source["source_id"],"filings":len(filings),
        "anchors":len(anchors),"coverage":coverage,"source_complete":True,"clock_assumed":True,"placebo_maps":cfg["timing_placebos"]})
    receipt(run,"prepare",list(out.glob("*")),{"filings":len(filings),"anchors":len(anchors)})
    print(json.dumps(read_json(out/"summary.json")),flush=True)


def prepare_placebo(run, replica):
    """Stage exact shifted requests on compute nodes, without outcome selection."""
    scheduled(); verify_manifest(run);run = Path(run);cfg = read_json(CONFIG)
    dates = read_json(run/"prepared/calendar.json")["dates"]
    raw = read_json(run/"prepared/filings.json");shifts = read_json(run/"prepared/placebo-map.json")[replica]
    offsets = {(r["issuer"],r["year"]):r["offset"] for r in shifts["shifts"]}
    by_year = {y:[i for i,d in enumerate(dates) if d.startswith(str(y))] for y in range(2022,2026)}
    moved = []
    for f in raw:
        i = f["availability_session"]
        if i>=len(dates): continue
        year = int(dates[i][:4]);pool = by_year[year];offset = offsets.get((f["issuer"],int(f["filing_date"][:4])))
        if offset is None: continue
        clone = {**f,"availability_session":pool[(pool.index(i)+offset)%len(pool)]}
        moved.append(clone)
    fs = read_json(run/"prepared/features.json")
    frames = {t:pd.DataFrame.from_dict(rows,orient="index").reindex(dates) for t,rows in fs.items()}
    anchors,coverage,exclusions = build_anchors(moved,frames,dates,cfg,variant_ids={"primary"})
    directory = run/"placebos"/str(replica)/"prepared";directory.mkdir(parents=True,exist_ok=True)
    write_json(directory/"anchors.json",anchors);write_json(directory/"calendar.json",read_json(run/"prepared/calendar.json"))
    csv_write(directory/"exclusions.csv",exclusions);write_json(directory/"map.json",shifts)
    receipt(run,"placebo-prepare-"+str(replica),list(directory.glob("*")),{"replica":replica,"anchors":len(anchors)})
