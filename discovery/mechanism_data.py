"""Local, resumable Massive acquisition for the registered H18–H20 round.

Contract/clock preparation belongs here. Statistical estimates and portfolio
replay are deliberately absent and execute later in scheduled compute jobs.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import exchange_calendars as xc
import pandas as pd
from dotenv import dotenv_values

from .io import ROOT, digest, identity, now, read_json, write_json as _atomic_write_json

REGISTRATION = "7688ad1d96303039d6e61ef2dcc6f19f21764a15"
CONFIG = ROOT / "config/mechanism-round1.json"
FOLDERS = {
    "H18": "H18 - CEO Departure Uncertainty Resolution",
    "H19": "H19 - Leadership Risk Concentration",
    "H20": "H20 - CFO Compensation Context",
}


def settings():
    return read_json(CONFIG)


def write_json(path, value):
    """Bounded retry for transient Windows destination locks, for all receipts."""
    for attempt in range(8):
        try:
            _atomic_write_json(path, value)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(min(.05 * 2**attempt, 1))


def checked_url(url):
    """Do not follow provider cursors off-host or retain credentials in URLs."""
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname != "api.massive.com"
            or parts.port not in (None, 443) or parts.username or parts.password):
        raise ValueError("Massive request must remain on the authorized API host")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k.lower() not in {"apikey", "api_key", "token", "access_token"}]
    return urlunsplit(("https", "api.massive.com", parts.path, urlencode(query), ""))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("API redirects are not followed")


class ApiCache:
    """Completed, content-verified objects; four workers share a pacing clock.

    Per-spec locks prevent duplicate requests from creating conflicting bytes.
    The cap counts reserved HTTP attempts, including failed/rate-limited calls.
    Every failure leaves an attempt receipt; no partial pagination is cached.
    """

    def __init__(self, folder, cfg):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.started = now()
        self.attempt_id = self.started.replace(":", "").replace("+", "_")
        self.attempt = self.folder / "attempts" / self.attempt_id
        self.attempt.mkdir(parents=True)
        self.key = os.getenv("MASSIVE_API_KEY") or dotenv_values(ROOT / ".env").get("MASSIVE_API_KEY")
        if not self.key or self.key.lower().startswith(("your_", "replace_", "paste_")):
            raise ValueError("MASSIVE_API_KEY must be configured locally")
        self.key = self.key.strip()
        self.cap = cfg["acquisition_new_request_cap_phase"]
        self.interval = cfg["acquisition_minimum_interval_seconds"]
        self.lock = threading.RLock()
        self.spec_locks = {}
        self.last_start = 0.0
        self.receipts, self.used = [], {}
        self.prior_count = sum(len(read_json(p).get("requests", []))
                               for p in self.folder.glob("attempts/*/receipt.json"))
        self.bucket_intervals, self.bucket_last = {}, {}
        for p in self.folder.glob("attempts/*/receipt.json"):
            for r in read_json(p).get("requests", []):
                if r.get("http_status") == 429:
                    self.bucket_intervals[r["bucket"]] = 12.5

    def save_receipts(self):
        with self.lock:
            receipt = {
                "started_at": self.started, "updated_at": now(),
                "prior_attempts": self.prior_count, "cap": self.cap,
                "requests": self.receipts,
            }
            # Windows indexers/sync clients can briefly hold the destination
            # open across an atomic replace. A bounded retry preserves the
            # same receipt and never turns an incomplete write into success.
            for attempt in range(8):
                try:
                    write_json(self.attempt / "receipt.json", receipt)
                    break
                except PermissionError:
                    if attempt == 7:
                        raise
                    time.sleep(min(.05 * 2**attempt, 1))

    def request(self, url, label):
        url = checked_url(url)
        bucket = urlsplit(url).path.split("/")[2]
        for retry in range(3):
            with self.lock:
                if self.prior_count + len(self.receipts) >= self.cap:
                    raise RuntimeError("Registered request cap exhausted; acquisition is partial")
                pace = max(self.interval, self.bucket_intervals.get(bucket, 0))
                wait = max(self.last_start + self.interval,
                           self.bucket_last.get(bucket, 0) + pace) - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                self.last_start = time.monotonic()
                self.bucket_last[bucket] = self.last_start
                receipt = {"label": label, "url": url, "bucket": bucket,
                           "at": now(), "http_status": None}
                self.receipts.append(receipt)
                number = len(self.receipts)
            retry_wait = None
            try:
                request = Request(url, headers={"Authorization": "Bearer " + self.key,
                                                "Accept": "application/json"})
                with build_opener(NoRedirect()).open(request, timeout=40) as response:
                    receipt["http_status"] = response.status
                    raw = response.read()
                p = self.attempt / f"response-{number:05d}.json"
                p.write_bytes(raw)
                receipt.update(file=p.name, sha256=digest(p))
                payload = json.loads(raw)
                receipt["rows"] = len(payload.get("results") or [])
                if payload.get("status") in {"ERROR", "NOT_AUTHORIZED"}:
                    receipt["error"] = "Provider reported API error"
                    raise RuntimeError("Provider API error; inspect ignored response evidence")
                return payload
            except HTTPError as error:
                receipt.update(http_status=error.code, error=f"HTTP {error.code}; body omitted")
                if error.code == 429 and retry < 2:
                    with self.lock:
                        self.bucket_intervals[bucket] = 12.5
                    try:
                        retry_wait = min(60, max(12.5, float(error.headers.get("Retry-After", 12.5))))
                    except (TypeError, ValueError):
                        retry_wait = 12.5
                else:
                    raise RuntimeError(receipt["error"]) from None
            except (URLError, TimeoutError, OSError):
                receipt["error"] = "Network request failed; no entitlement conclusion"
                raise RuntimeError(receipt["error"]) from None
            finally:
                self.save_receipts()
            if retry_wait is not None:
                time.sleep(retry_wait)
        raise RuntimeError("Rate-limit retries exhausted")

    def pages(self, label, path, params, paginate=True):
        spec = {"path": path, "params": params, "paginate": paginate}
        rid = identity(spec)
        with self.lock:
            spec_lock = self.spec_locks.setdefault(rid, threading.Lock())
        with spec_lock:
            p, rp = self.folder / f"{rid}.json", self.folder / f"{rid}.receipt.json"
            if p.exists() and rp.exists():
                saved = read_json(rp)
                if digest(p) != saved["sha256"] or saved["spec"] != spec:
                    raise ValueError("Cached object has changed")
                rows = read_json(p)
            else:
                url = checked_url("https://api.massive.com" + path + "?" + urlencode(params))
                rows, seen = [], set()
                while url:
                    if url in seen:
                        raise ValueError("Repeated pagination; object remains incomplete")
                    seen.add(url)
                    payload = self.request(url, label)
                    rows.extend(payload.get("results") or [])
                    next_url = payload.get("next_url") if paginate else None
                    url = checked_url(next_url) if next_url else None
                write_json(p, rows)
                saved = {"spec": spec, "sha256": digest(p), "rows": len(rows), "retrieved_at": now()}
                write_json(rp, saved)
            with self.lock:
                self.used[rid] = saved
            return rows, rid


def phase_window(phase, cfg, freeze=None, custom=None):
    if phase == "development":
        window = dict(cfg["development"])
    elif phase == "final-oos":
        if freeze is None:
            raise ValueError("Final data access requires the frozen development package")
        frozen = read_json(freeze)
        if frozen.get("config_sha256") != digest(CONFIG):
            raise ValueError("Final configuration differs from the development freeze")
        for relative, expected in frozen["code_files"].items():
            if digest(ROOT / relative) != expected:
                raise ValueError("Code differs from final freeze: " + relative)
        window = dict(cfg["final_oos"])
    elif phase == "sealed":
        if not custom or set(custom) != {"start", "end", "as_of"}:
            raise ValueError("Judge replay requires explicit start/end/as-of")
        window = dict(custom)
    else:
        raise ValueError("Unknown study phase")
    for d in window.values():
        date.fromisoformat(d)
    if not window["start"] <= window["end"] <= window["as_of"]:
        raise ValueError("Invalid phase boundaries")
    if (date.fromisoformat(window["as_of"]) - date.fromisoformat(window["start"])).days > 1100:
        raise ValueError("Replay interval exceeds the bounded research scope")
    return window


def session_calendar(window):
    cal = xc.get_calendar("XNYS", start=window["start"], end=window["as_of"])
    dates = [d.strftime("%Y-%m-%d") for d in cal.sessions
             if window["start"] <= d.strftime("%Y-%m-%d") <= window["as_of"]]
    clock = {d: {"open_ns": int(cal.session_open(d).value),
                 "close_ns": int(cal.session_close(d).value)} for d in dates}
    return dates, clock


def event_anchors(rows, universe, dates, cfg, window):
    grouped, exclusions = {}, []
    for r in rows:
        if not window["start"] <= r.get("filing_date", "") <= window["end"]:
            raise ValueError("Disclosure outside requested phase")
        tickers = r.get("tickers") or []
        if not isinstance(tickers, list):
            raise ValueError("Unexpected ticker mapping type")
        if not tickers:
            exclusions.append({"reason": "missing_ticker_mapping", "accession": r.get("accession_number")})
        for ticker in sorted(set(tickers) & set(universe)):
            if not r.get("cik") or not r.get("accession_number"):
                exclusions.append({"ticker": ticker, "reason": "missing_filing_identity"})
                continue
            key = (ticker, str(r["cik"]).zfill(10), r["accession_number"])
            g = grouped.setdefault(key, {"ticker": ticker, "issuer": key[1], "accession": key[2],
                                         "filing_date": r["filing_date"], "categories": []})
            if g["filing_date"] != r["filing_date"]:
                raise ValueError("Conflicting filing date for one identity")
            g["categories"].append(r["tertiary_category"])
    events = sorted(grouped.values(), key=lambda a: (a["filing_date"], a["issuer"], a["accession"], a["ticker"]))
    anchors = []
    for e in events:
        i = bisect_left(dates, e["filing_date"])
        assumed = bisect_left(dates, (pd.Timestamp(e["filing_date"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
        event_id = identity([e["ticker"], e["issuer"], e["accession"]])[:20]
        e = {**e, "categories": sorted(set(e["categories"])), "event_id": event_id}
        for cohort, shift in [("event", 0), ("ordinary", -cfg["ordinary_offset_sessions"])]:
            fi, di = i + shift, assumed + shift
            if fi < 0 or di + 1 >= len(dates):
                exclusions.append({**e, "cohort": cohort, "reason": "anchor_or_entry_outside_phase"})
                continue
            if cohort == "ordinary":
                day = pd.Timestamp(dates[fi])
                if any(x["issuer"] == e["issuer"] and abs((pd.Timestamp(x["filing_date"]) - day).days)
                       <= cfg["ordinary_exclusion_calendar_days"] for x in events):
                    exclusions.append({**e, "cohort": cohort, "reason": "ordinary_near_selected_event"})
                    continue
            anchors.append({**e, "anchor_id": event_id + "-" + cohort, "cohort": cohort,
                            "filing_session": fi, "decision_session": di,
                            "clock_status": "conditional_filing_plus_one_calendar_day; historical_vendor_release_unknown"})
    return anchors, exclusions


def same_day_bar(rows, day):
    found = [r for r in rows if pd.Timestamp(r["t"], unit="ms", tz="UTC")
             .tz_convert("America/New_York").strftime("%Y-%m-%d") == day and r.get("c", 0) > 0]
    if len(found) > 1:
        raise ValueError("Duplicate daily option bar")
    return found[0] if found else None


def standard_pairs(rows, when):
    unique, pairs = {}, {}
    for r in rows:
        ticker = r.get("ticker")
        if not ticker:
            continue
        if ticker in unique and unique[ticker] != r:
            raise ValueError("Conflicting contract identity")
        unique[ticker] = r
    for r in unique.values():
        if (r.get("shares_per_contract") != 100 or r.get("additional_underlyings")
                or r.get("exercise_style") not in {"american", "european"}
                or r.get("contract_type") not in {"call", "put"}):
            continue
        if r["expiration_date"] <= when:
            continue
        key = (r["expiration_date"], float(r["strike_price"]))
        p = pairs.setdefault(key, {})
        side = r["contract_type"]
        if side in p and p[side]["ticker"] != r["ticker"]:
            raise ValueError("Ambiguous paired strike")
        p[side] = r
    return {k: v for k, v in pairs.items() if set(v) == {"call", "put"}}


def choose_contracts(rows, when, cfg, fetch_bar):
    pairs = standard_pairs(rows, when)
    if not pairs:
        return {}, {b: "no_standard_paired_chain" for b in cfg["buckets"]}
    seed_expiry = min(k[0] for k in pairs)
    seed_strikes = sorted(k[1] for k in pairs if k[0] == seed_expiry)
    strike = seed_strikes[len(seed_strikes) // 2]
    spot = None
    for _ in range(8):
        legs = pairs[(seed_expiry, strike)]
        call, put = (fetch_bar(legs[s]["ticker"]) for s in ["call", "put"])
        if call is None or put is None:
            return {}, {b: "missing_decision_seed_pair" for b in cfg["buckets"]}
        years = (pd.Timestamp(seed_expiry) - pd.Timestamp(when)).days / 365.25
        spot = strike * math.exp(-cfg["rate"] * years) + call["c"] - put["c"]
        if not math.isfinite(spot) or spot <= 0:
            return {}, {b: "invalid_parity_seed" for b in cfg["buckets"]}
        new_strike = min(seed_strikes, key=lambda k: (abs(k - spot), k))
        if new_strike == strike:
            break
        strike = new_strike
    selections, exclusions = {}, {}
    for bucket, (lo, hi, target) in cfg["buckets"].items():
        eligible = [k for k in pairs if lo <= (pd.Timestamp(k[0])-pd.Timestamp(when)).days <= hi]
        if not eligible:
            exclusions[bucket] = "no_standard_pair_in_bucket"
            continue
        expiry, atm = min(eligible, key=lambda k: (abs((pd.Timestamp(k[0])-pd.Timestamp(when)).days-target),
                                                  k[0], abs(k[1]-spot), k[1]))
        legs = {"atm_call": pairs[(expiry, atm)]["call"], "atm_put": pairs[(expiry, atm)]["put"]}
        missing = {}
        strikes = sorted(k[1] for k in pairs if k[0] == expiry)
        for pct in cfg["otm_grid"]:
            key = str(pct)
            for side, direction, role in [("call", 1, "upper_call"), ("put", -1, "lower_put")]:
                wanted = spot * (1 + direction * pct)
                candidates = [k for k in strikes if (k >= wanted if direction == 1 else k <= wanted)]
                if not candidates:
                    missing[role + "_" + key] = "requested_otm_unavailable"
                    continue
                k = min(candidates, key=lambda x: (abs(x-wanted), x))
                distance = direction * (k / spot - 1)
                if abs(distance - pct) > cfg["maximum_otm_distance_error"]:
                    missing[role + "_" + key] = "achieved_otm_error_exceeds_limit"
                else:
                    legs[role + "_" + key] = pairs[(expiry, k)][side]
        selections[bucket] = {"expiry": expiry, "atm_strike": atm, "selection_spot": spot,
                              "dte": (pd.Timestamp(expiry)-pd.Timestamp(when)).days,
                              "legs": legs, "missing_legs": missing}
    return selections, exclusions


def backward_quote(rows, cutoff_ns, cfg):
    eligible = [q for q in rows if cutoff_ns - cfg["quote_max_age_seconds"] * 10**9
                <= q.get("sip_timestamp", 0) <= cutoff_ns]
    if not eligible:
        return None, "no_fresh_backward_quote"
    q = max(eligible, key=lambda r: (r["sip_timestamp"], r.get("sequence_number", 0)))
    bid, ask = q.get("bid_price", 0), q.get("ask_price", 0)
    if not (0 < bid <= ask):
        return None, "nonpositive_or_crossed_quote"
    if (ask - bid) / ((ask + bid) / 2) > cfg["quote_max_relative_spread"]:
        return None, "quote_spread_exceeds_limit"
    if q.get("bid_size", 0) < 1 or q.get("ask_size", 0) < 1:
        return None, "insufficient_displayed_size"
    return q, None


def download(output, phase="development", freeze=None, custom=None):
    cfg = settings()
    window = phase_window(phase, cfg, freeze, custom)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    existing = output / "source.json"
    if existing.exists() and read_json(existing).get("complete"):
        source = read_json(existing)
        if source["window"] != window or source["config_sha256"] != digest(CONFIG):
            raise ValueError("Existing complete acquisition is for a different frozen phase")
        for rid, receipt in source["objects"].items():
            if digest(output / "raw" / f"{rid}.json") != receipt["sha256"]:
                raise ValueError("Existing source object changed")
        return {"complete": True, "anchors": len(source["anchors"]), "reused_complete": True}
    if existing.exists():
        history = output / "checkpoints" / (now().replace(":", "").replace("+", "_") + ".json")
        history.parent.mkdir(parents=True, exist_ok=True)
        history.write_bytes(existing.read_bytes())
    if phase == "final-oos":
        exposure = output / "FINAL-EXPOSURE.json"
        if not exposure.exists():
            write_json(exposure, {"first_access_started_at": now(), "freeze_sha256": digest(freeze),
                                  "phase": phase, "window": window,
                                  "reason": "one registered final package; all attempts retained"})
    dates, clock = session_calendar(window)
    cache = ApiCache(output / "raw", cfg)
    source = {"schema": 1, "registration_commit": REGISTRATION, "phase": phase, "window": window,
              "config_sha256": digest(CONFIG), "started_at": now(), "complete": False,
              "sessions": dates, "clock": clock, "anchors": [], "exclusions": [], "objects": {}, "errors": []}

    def bars(ticker, start, end):
        rows, rid = cache.pages("Bars " + ticker, "/v2/aggs/ticker/" + quote(ticker, safe="")
                               + "/range/1/day/" + start + "/" + end,
                               {"adjusted": "false", "sort": "asc", "limit": 50000})
        for r in rows:
            day = pd.Timestamp(r["t"], unit="ms", tz="UTC").tz_convert("America/New_York").strftime("%Y-%m-%d")
            if not start <= day <= end:
                raise ValueError("Provider bar is outside the bounded phase request")
        return rows, rid

    try:
        universe = read_json(ROOT / cfg["universe_source"])["tickers"]
        if len(universe) != 100 or len(set(universe)) != 100:
            raise ValueError("Starter universe is not 100 distinct tickers")
        taxonomy, _ = cache.pages("Taxonomy", "/stocks/taxonomies/vX/disclosures", {"limit": 1000})
        if not set(cfg["categories"]) <= {r.get("tertiary_category") for r in taxonomy}:
            raise ValueError("Registered category missing from taxonomy")
        events = []
        for category in cfg["categories"]:
            rows, _ = cache.pages("Disclosures " + category, "/stocks/filings/8-K/vX/disclosures", {
                "tertiary_category": category, "filing_date.gte": window["start"], "filing_date.lte": window["end"],
                "limit": 1000, "sort": "filing_date.asc"})
            events.extend(rows)
        anchors, exclusions = event_anchors(events, universe, dates, cfg, window)
        source["exclusions"] = exclusions
        context = {}
        for issuer in sorted({a["issuer"] for a in anchors}):
            context[issuer], _ = cache.pages("Issuer context " + issuer, "/stocks/filings/8-K/vX/disclosures", {
                "cik": issuer, "filing_date.gte": window["start"], "filing_date.lte": window["end"],
                "limit": 1000, "sort": "filing_date.asc"})

        def acquire(anchor):
            item = {**anchor, "variants": {}, "context": [r for r in context[anchor["issuer"]]
                     if r["accession_number"] == anchor["accession"]] if anchor["cohort"] == "event" else []}
            for delay in cfg["decision_delays"]:
                di = anchor["decision_session"] + delay
                if di + 1 >= len(dates):
                    item["variants"][str(delay)] = {"reason": "delayed_entry_outside_phase"}
                    continue
                day, entry = dates[di], dates[di+1]
                contracts = []
                for expired in ["false", "true"]:
                    rows, _ = cache.pages("Chain " + anchor["anchor_id"], "/v3/reference/options/contracts", {
                        "underlying_ticker": anchor["ticker"], "as_of": day, "expired": expired,
                        "expiration_date.gte": (pd.Timestamp(day)+pd.Timedelta(days=21)).strftime("%Y-%m-%d"),
                        "expiration_date.lte": (pd.Timestamp(day)+pd.Timedelta(days=180)).strftime("%Y-%m-%d"),
                        "limit": 1000, "order": "asc", "sort": "ticker"})
                    contracts.extend(rows)
                selected, missing = choose_contracts(contracts, day, cfg, lambda ticker: same_day_bar(bars(ticker, day, day)[0], day))
                variant = {"decision_date": day, "entry_date": entry, "decision_session": di,
                           "entry_session": di+1, "selected": selected, "missing_buckets": missing}
                for bucket, selection in selected.items():
                    end = min(selection["expiry"], window["as_of"])
                    # The common backward window is fixed before the delay grid;
                    # it allows exact request reuse without reading future prices
                    # for any contract/decision selection.
                    first = dates[max(0, anchor["decision_session"]-10)]
                    selection["bar_objects"], selection["quotes"] = {}, {}
                    for role, contract in selection["legs"].items():
                        _, rid = bars(contract["ticker"], first, end)
                        selection["bar_objects"][role] = rid
                    if bucket == cfg["primary_bucket"]:
                        targets = {"entry": (di+1, "open"), "mechanism_5": (di+6, "close"),
                                   "mechanism_10": (di+11, "close")}
                        targets.update({str(h): (anchor["filing_session"]+h, "close") for h in cfg["filing_horizons"]})
                        if selection["expiry"] <= window["as_of"]:
                            targets["expiry"] = (bisect_left(dates, selection["expiry"]), "close")
                            if targets["expiry"][0] >= len(dates) or dates[targets["expiry"][0]] > selection["expiry"]:
                                targets["expiry"] = (targets["expiry"][0]-1, "close")
                        else:
                            selection["quotes"]["expiry"] = {"reason": "expiry_unresolved_at_fixed_cutoff"}
                        primary_roles = [r for r in selection["legs"] if r in {"atm_call", "atm_put", "upper_call_0.05", "lower_put_0.05"}]
                        # Registered entry/exit clock also supplies two fixed
                        # post-entry mechanism marks. Quote failures are data.
                        for label, (index, side) in targets.items():
                            if not di+1 <= index < len(dates) or dates[index] > selection["expiry"]:
                                selection["quotes"][label] = {"reason": "exit_before_entry_after_expiry_or_unresolved"}
                                continue
                            d = dates[index]
                            cutoff = clock[d]["open_ns"] + cfg["entry_minutes_after_open"]*60*10**9 if side == "open" else clock[d]["close_ns"]-cfg["exit_minutes_before_close"]*60*10**9
                            result = {"date": d, "cutoff_ns": cutoff, "legs": {}}
                            for role in primary_roles:
                                contract = selection["legs"][role]
                                quotes, rid = cache.pages("Quote " + anchor["anchor_id"] + " " + label,
                                    "/v3/quotes/"+quote(contract["ticker"], safe=""), {
                                        "timestamp.gte": cutoff-cfg["quote_max_age_seconds"]*10**9,
                                        "timestamp.lte": cutoff, "order": "desc", "sort": "timestamp", "limit": 1}, paginate=False)
                                q, reason = backward_quote(quotes, cutoff, cfg)
                                result["legs"][role] = {"quote": q, "reason": reason, "object_id": rid}
                            selection["quotes"][label] = result
                        # Missing scheduled primary liquidation is not deleted.
                        # Acquire the fixed next-session retry path as source
                        # preparation; the portfolio engine later decides which
                        # initiated positions actually require those quotes.
                        scheduled = selection["quotes"].get(str(cfg["primary_filing_horizon"]), {})
                        if scheduled.get("legs") and any(v.get("quote") is None for v in scheduled["legs"].values()):
                            ri = max(di+1, anchor["filing_session"]+cfg["primary_filing_horizon"]) + 1
                            while ri < len(dates) and dates[ri] <= selection["expiry"]:
                                d = dates[ri]
                                cutoff = clock[d]["close_ns"]-cfg["exit_minutes_before_close"]*60*10**9
                                retry_result = {"date": d, "cutoff_ns": cutoff, "legs": {}}
                                for role in primary_roles:
                                    contract = selection["legs"][role]
                                    qr, rid = cache.pages("Liquidation retry "+anchor["anchor_id"],
                                        "/v3/quotes/"+quote(contract["ticker"], safe=""), {
                                            "timestamp.gte": cutoff-cfg["quote_max_age_seconds"]*10**9,
                                            "timestamp.lte": cutoff, "order": "desc", "sort": "timestamp", "limit": 1}, paginate=False)
                                    q, reason = backward_quote(qr, cutoff, cfg)
                                    retry_result["legs"][role] = {"quote": q, "reason": reason, "object_id": rid}
                                selection["quotes"]["retry_"+d] = retry_result
                                if all(v["quote"] is not None for v in retry_result["legs"].values()):
                                    break
                                ri += 1
                item["variants"][str(delay)] = variant
            return item

        # HTTP preparation only: all workers share cap, immutable objects and
        # global 0.1-second pacing. No model/portfolio work occurs on the PC.
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(acquire, a) for a in anchors]
            try:
                for future in as_completed(futures):
                    item = future.result()
                    source["anchors"].append(item)
                    source["objects"] = dict(cache.used)
                    write_json(output / "source.partial.json", source)
                    print(f"Prepared {len(source['anchors'])}/{len(anchors)} anchors; new attempts={len(cache.receipts)}", flush=True)
            except Exception:
                for future in futures:
                    future.cancel()
                raise
        source["anchors"].sort(key=lambda a: (a["filing_date"], a["issuer"], a["accession"], a["ticker"], a["cohort"]))
        source["complete"] = len(source["anchors"]) == len(anchors)
    except Exception as error:
        source["errors"].append({"at": now(), "type": type(error).__name__,
                                 "reason": str(error) if isinstance(error, (ValueError, RuntimeError)) else "Unexpected source structure; inspect ignored evidence"})
        raise
    finally:
        cache.save_receipts()
        source["objects"] = dict(cache.used)
        source["finished_at"] = now()
        source["http_attempts"] = cache.prior_count + len(cache.receipts)
        write_json(existing, source)
    return {"complete": source["complete"], "anchors": len(source["anchors"]), "http_attempts": source["http_attempts"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--phase", choices=["development", "final-oos", "sealed"], default="development")
    p.add_argument("--freeze", type=Path)
    p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--as-of")
    a = p.parse_args()
    custom = {"start": a.start, "end": a.end, "as_of": a.as_of} if a.phase == "sealed" else None
    print(json.dumps(download(a.output, a.phase, a.freeze, custom)))


if __name__ == "__main__":
    main()
