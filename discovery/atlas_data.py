"""Private, resumable H21 acquisition. No statistical fit or portfolio is run here."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

from dotenv import dotenv_values
from .io import ROOT, digest, identity, now, read_json, write_json

PLAN_COMMIT = "0ec92c584a197bd053bacb74e35c4f7b3a66d4a4"
TAXONOMY = ROOT / "data/cache/discovery/downloads/0d596c04eab44969/ca3356801b49ed13a94e46bcc6e510c6de53c77322b70b8bfc5fcc42cb0a7070.json"


class NetworkBlocked(RuntimeError): pass
class RequestBudget(RuntimeError): pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect refused before forwarding credentials")


def settings(path=None):
    c = read_json(path or ROOT / "config/disclosure-atlas.json")
    if c["start"] != "2022-01-01" or c["end"] != "2025-12-31":
        raise ValueError("H21 is restricted to the approved 2022-2025 discovery window")
    if len(c["categories"]) != 119 or len(set(c["categories"])) != 119:
        raise ValueError("Expected exactly 119 pinned types")
    if len(c["tickers"]) != 100 or len(set(c["tickers"])) != 100 or not c["no_trading"]:
        raise ValueError("Invalid approved universe or trading boundary")
    return c


class Store:
    """A shared request clock and atomic objects retain partial and failed attempts."""
    def __init__(self, folder, budget=5000, interval=.5):
        self.folder = Path(folder); self.folder.mkdir(parents=True, exist_ok=True)
        self.objects = self.folder / "objects"; self.objects.mkdir(exist_ok=True)
        self.attempt = self.folder / "requests" / now().replace(":", "")
        self.attempt.mkdir(parents=True, exist_ok=False)
        self.key = os.getenv("MASSIVE_API_KEY") or dotenv_values(ROOT / ".env").get("MASSIVE_API_KEY")
        if not self.key: raise ValueError("Set the existing local Massive key; do not put it in chat")
        self.budget, self.interval, self.calls, self.next_at = budget, interval, 0, 0.
        self.lock = threading.Lock(); self.entries = {}; self.failures = []
        self.legacy = {}
        for p in (ROOT / "data/cache/discovery/downloads").glob("*/*.receipt.json"):
            try:
                r = read_json(p); obj = p.with_name(p.name.replace(".receipt.json", ".json"))
                if obj.exists(): self.legacy[identity({"path": r["path"], "params": r["params"]})] = (obj, r)
            except (KeyError, ValueError): pass

    def _get(self, url, label):
        destination=urlparse(url)
        if (destination.scheme!="https" or destination.hostname!="api.massive.com"
                or destination.username is not None or destination.password is not None
                or destination.port not in (None,443) or "apikey=" in url.lower()):
            raise ValueError("Unsafe pagination destination or URL credentials")
        for retry in range(5):
            with self.lock:
                if self.calls >= self.budget: raise RequestBudget("Bounded request budget exhausted; resume from receipts")
                delay = max(0., self.next_at - time.monotonic())
                self.next_at = max(time.monotonic(), self.next_at) + self.interval
                self.calls += 1; number = self.calls
            if delay: time.sleep(delay)
            receipt = {"label": label, "url": url, "attempt": number, "started_at": now()}
            try:
                req = Request(url, headers={"Authorization": "Bearer " + self.key.strip(), "User-Agent": "H21-Massive-Research/1.0"})
                with build_opener(NoRedirect()).open(req, timeout=30) as response:
                    if urlparse(response.url).hostname != "api.massive.com": raise ValueError("Unexpected redirect")
                    raw = response.read(); receipt["http_status"] = response.status
                payload = json.loads(raw)
                receipt.update(sha256=hashlib.sha256(raw).hexdigest(), finished_at=now())
                (self.attempt / f"{number:06d}.json").write_bytes(raw)
                write_json(self.attempt / f"{number:06d}.receipt.json", receipt)
                return payload
            except HTTPError as error:
                receipt.update(http_status=error.code, finished_at=now())
                write_json(self.attempt / f"{number:06d}.receipt.json", receipt)
                if error.code in (429, 500, 502, 503, 504) and retry < 4:
                    time.sleep(min(30, 2 ** retry * 2)); continue
                raise RuntimeError(f"{label}: HTTP {error.code}") from None
            except (URLError, TimeoutError, OSError) as error:
                receipt.update(error=type(error).__name__, finished_at=now())
                write_json(self.attempt / f"{number:06d}.receipt.json", receipt)
                if getattr(getattr(error, "reason", error), "winerror", None) == 10013:
                    raise NetworkBlocked("Windows socket access denied; retry with approved network access") from None
                if retry < 4: time.sleep(2 ** retry); continue
                raise RuntimeError(f"{label}: network access failed ({type(error).__name__})") from None

    def pages(self, label, path, params, optional=False,paginate=True):
        spec={"path":path,"params":params,**({"paginate":False} if not paginate else {})}
        oid = identity(spec); obj = self.objects / f"{oid}.json"
        receipt_path = self.objects / f"{oid}.receipt.json"
        try:
            # Find an exact earlier bounded sample by its spec identity; do
            # not scan or adopt a full stream as though it were one sample.
            if not paginate and path.startswith('/v3/quotes/') and params.get('limit')==1:
                for p in (ROOT/'data/cache/massive-mechanisms').glob(f'*/development/raw/{oid}.receipt.json'):
                    r=read_json(p);old=p.with_name(p.name.replace('.receipt.json','.json'))
                    if r.get('spec')==spec and r['rows']<=1 and old.exists():
                        self.legacy[oid]=(old,{**r,'path':path,'params':params})
            if obj.exists() and receipt_path.exists():
                r = read_json(receipt_path)
                if not r.get("complete") or digest(obj) != r["sha256"]: raise ValueError("Cached source identity changed")
                self.entries[oid] = r; return read_json(obj)
            if oid in self.legacy:
                old, r = self.legacy[oid]
                if digest(old) != r["sha256"]: raise ValueError("Legacy source identity changed")
                obj.write_bytes(old.read_bytes())
                r = {"path": path, "params": params, "file": f"objects/{obj.name}", "sha256": digest(obj), "complete": True,
                     "reused_from": str(old.relative_to(ROOT)), "retrieved_at": r.get("retrieved_at"), "rows": len(read_json(obj))}
                write_json(receipt_path, r); self.entries[oid] = r; return read_json(obj)
            url = "https://api.massive.com" + path + "?" + urlencode(params)
            seen, rows, count = set(), [], 0
            while url:
                if url in seen: raise ValueError("Pagination cycle")
                seen.add(url); count += 1
                if count > 10000: raise RuntimeError("Pagination limit reached; source remains incomplete")
                page = self._get(url, label); result = page.get("results", [])
                if isinstance(result, dict): result = [result]
                if not isinstance(result, list): raise ValueError("Unexpected provider result grain")
                rows.extend(result); url = page.get("next_url") if paginate else None
            write_json(obj, rows)
            r = {"path": path, "params": params, "file": f"objects/{obj.name}", "sha256": digest(obj), "rows": len(rows),
                 "retrieved_at": now(), "pages": count, "complete": True,"scope":"all_pages" if paginate else "bounded_first_page"}
            write_json(receipt_path, r); self.entries[oid] = r
            return rows
        except Exception as error:
            failure = {"label": label, "path": path, "params": params, "error": str(error), "optional": optional, "recorded_at": now()}
            with self.lock: self.failures.append(failure)
            if isinstance(error, (NetworkBlocked, RequestBudget)): raise
            if optional: return None
            raise


def acquire(output, budget=5000, workers=8, interval=.5):
    c = settings(); output = Path(output); store = Store(output, budget, interval)
    taxonomy_file = output / "taxonomy.json"
    if digest(TAXONOMY) != c["taxonomy_sha256"]: raise ValueError("Pinned taxonomy changed")
    taxonomy_file.write_bytes(TAXONOMY.read_bytes())
    mapping, collections = {}, []
    report = {"study": "H21", "plan_commit": PLAN_COMMIT, "started_at": now(), "settings": c, "complete": False}
    def ticker_data(ticker):
        escaped = quote(ticker, safe="")
        details = store.pages("issuer metadata " + ticker, f"/v3/reference/tickers/{escaped}", {"date": c["end"]}, optional=True)
        cik = str(details[0].get("cik", "")).zfill(10) if details else ""
        if cik == "0000000000": cik = ""
        with store.lock: mapping[ticker] = {"cik": cik or None, "metadata_available": details is not None}
        for start, end in [("2022-01-01", "2023-12-31"), ("2024-01-01", "2025-12-31")]:
            store.pages("daily prices " + ticker, f"/v2/aggs/ticker/{escaped}/range/1/day/{start}/{end}",
                        {"adjusted": "true", "sort": "asc", "limit": 50000}, optional=True)
        store.pages("split metadata " + ticker, "/v3/reference/splits", {"ticker": ticker, "execution_date.gte": c["start"], "execution_date.lte": c["end"], "limit": 1000}, optional=True)
        store.pages("dividend metadata " + ticker, "/v3/reference/dividends", {"ticker": ticker, "ex_dividend_date.gte": c["start"], "ex_dividend_date.lte": c["end"], "limit": 1000}, optional=True)
        return ticker
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(ticker_data, ticker) for ticker in c["tickers"] + [c["benchmark"]]]
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                future.result(); print(f"Market inputs: {i}/101; HTTP attempts: {store.calls}", flush=True)
        by_cik = {}
        for ticker in c["tickers"]:
            cik = mapping.get(ticker, {}).get("cik")
            by_cik.setdefault(cik or "ticker:" + ticker, []).append(ticker)
        def filings(item):
            cik, tickers = item; params = {"filing_date.gte": c["start"], "filing_date.lte": c["end"], "limit": 1000, "sort": "filing_date.asc"}
            params["cik" if not cik.startswith("ticker:") else "tickers"] = cik if not cik.startswith("ticker:") else tickers[0]
            rows = store.pages("all-category filings " + tickers[0], "/stocks/filings/8-K/vX/disclosures", params)
            return {"cik": cik, "tickers": tickers, "object_id": identity({"path": "/stocks/filings/8-K/vX/disclosures", "params": params}), "rows": len(rows)}
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(filings, item) for item in by_cik.items()]
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                collections.append(future.result()); print(f"All-category issuer histories: {i}/{len(futures)}; HTTP attempts: {store.calls}", flush=True)
        report["complete"] = True
    finally:
        report.update(finished_at=now(), calls=store.calls, objects=store.entries, failures=store.failures,
                      mapping=mapping, disclosure_collections=collections, taxonomy_file="taxonomy.json", taxonomy_sha256=digest(taxonomy_file))
        report["source_id"] = identity({k:v for k,v in report.items() if k != "source_id"})
        write_json(output / "source.json", report)
    return report


def load_source(folder):
    folder = Path(folder); source = read_json(folder / "source.json")
    if not source["complete"]: raise ValueError("All-category filing acquisition is incomplete")
    if identity({k:v for k,v in source.items() if k != "source_id"}) != source["source_id"]: raise ValueError("Source manifest changed")
    if settings() != source["settings"]: raise ValueError("Source settings differ from frozen research settings")
    taxonomy = read_json(folder / source["taxonomy_file"])
    if digest(folder / source["taxonomy_file"]) != source["taxonomy_sha256"]: raise ValueError("Taxonomy changed")
    objects = {}
    for oid, entry in source["objects"].items():
        p = folder / entry["file"]
        if digest(p) != entry["sha256"]: raise ValueError("Source object changed")
        objects[oid] = read_json(p)
    return source, taxonomy, objects


def main():
    p = argparse.ArgumentParser(); p.add_argument("--output", required=True); p.add_argument("--budget", type=int, default=5000)
    p.add_argument("--workers", type=int, default=8); p.add_argument("--interval", type=float, default=.5)
    a = p.parse_args(); acquire(a.output, a.budget, a.workers, a.interval)


if __name__ == "__main__": main()
