"""Free Databento metadata/estimates and tiny Massive quote access probes.

This prepares local coverage evidence only. The Databento endpoint allowlist
deliberately excludes time-series downloads and other billable operations.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = "https://hist.databento.com/v0/"
GET_METHODS = {
    "metadata.list_schemas", "metadata.get_dataset_range",
    "metadata.get_dataset_condition", "metadata.list_fields",
}
POST_METHODS = {
    "metadata.get_cost", "metadata.get_record_count",
    "metadata.get_billable_size", "symbology.resolve",
}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_call(call):
    method, params = call["method"], call["params"]
    if method not in GET_METHODS | POST_METHODS:
        raise ValueError("Only free metadata and symbology endpoints are permitted")
    if params.get("dataset") != "OPRA.PILLAR":
        raise ValueError("This check is confined to OPRA.PILLAR")
    if any("key" in str(k).lower() or "token" in str(k).lower() for k in params):
        raise ValueError("Credentials cannot be request parameters")
    if method in POST_METHODS:
        symbols = params.get("symbols")
        if not isinstance(symbols, str) or not symbols.strip() or "ALL_SYMBOLS" in symbols:
            raise ValueError("An explicit, bounded symbol list is required")
        if len(symbols.split(",")) > 100:
            raise ValueError("At most 100 explicit symbols per coverage request")
        if method == "symbology.resolve":
            start, end = params.get("start_date"), params.get("end_date")
        else:
            start, end = params.get("start"), params.get("end")
        if not start or not end or not ("2024-01-01" <= start[:10] <= end[:10] <= "2026-01-01"):
            raise ValueError("An explicit 2024–2025 development interval is required")
        if datetime.fromisoformat(start.replace("Z", "+00:00")) >= datetime.fromisoformat(end.replace("Z", "+00:00")):
            raise ValueError("Start must precede exclusive end")
    return method, params


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def databento_check(plan, output, key):
    calls = plan["databento_calls"]
    if not 1 <= len(calls) <= 60:
        raise ValueError("Expected 1–60 metadata calls")
    # Validate the whole plan before the first network request.
    validated = [validate_call(call) for call in calls]
    opener = build_opener(NoRedirect())
    auth = "Basic " + base64.b64encode((key + ":").encode()).decode()
    receipts = []
    for index, (call, (method, params)) in enumerate(zip(calls, validated), 1):
        if index > 1:
            time.sleep(0.25)
        url = GATEWAY + method
        data = None
        if method in GET_METHODS:
            url += "?" + urlencode(params)
        else:
            data = urlencode(params).encode()
        receipt = {"label": call["label"], "method": method, "params": params,
                   "retrieved_at_utc": stamp(), "http_status": None}
        try:
            request = Request(url, data=data, headers={"Authorization": auth,
                              "Accept": "application/json", "User-Agent": "GatorQuantHacks-local-coverage/1.0"})
            with opener.open(request, timeout=40) as response:
                receipt["http_status"] = response.status
                raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise ValueError("Metadata response exceeded coverage-check cap")
            value = json.loads(raw)
            # These endpoints return market metadata, never account credentials.
            # Refuse to retain an unexpected reflected credential.
            if key.encode() in raw:
                raise ValueError("Unexpected credential reflection; response not retained")
            name = f"databento-{index:02d}.json"
            (output / name).write_bytes(raw)
            receipt.update(raw_file=name, sha256=hashlib.sha256(raw).hexdigest(), result=value)
        except HTTPError as exc:
            receipt.update(http_status=exc.code, error="HTTP access/request failure; response body omitted")
        except (URLError, TimeoutError):
            receipt["error"] = "Network or timeout failure"
        receipts.append(receipt)
        write_json(output / "databento-receipts.json", receipts)
        print(f"Databento {call['label']}: HTTP {receipt['http_status']}")
    return receipts


def massive_check(plan, output, key):
    from check_massive_coverage import AccessFailure, Client

    probes = plan.get("massive_quote_probes", [])
    if len(probes) > 2:
        raise ValueError("At most two one-record Massive quote probes")
    for probe in probes:
        if not re.fullmatch(r"O:[A-Z.]+[0-9]{6}[CP][0-9]{8}", probe["ticker"]):
            raise ValueError("Unexpected option ticker")
        if not "2024-01-01" <= probe["date"] <= "2025-12-31":
            raise ValueError("Probe lies outside development")
    directory = output / "massive"
    directory.mkdir()
    client = Client(key, directory, len(probes))
    for probe in probes:
        try:
            client.get("quote-" + probe["date"], "/v3/quotes/" + probe["ticker"],
                       {"timestamp": probe["date"], "sort": "timestamp", "order": "desc", "limit": 1})
        except AccessFailure:
            pass
        write_json(directory / "receipts.json", client.receipts)
    return client.receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-massive", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    values = dotenv_values(ROOT / ".env")
    key = os.getenv("DATABENTO_API_KEY") or values.get("DATABENTO_API_KEY")
    if not key or key == "your_databento_api_key":
        raise SystemExit("DATABENTO_API_KEY is not configured in root .env")
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "plan.json", plan)
    summary = {"created_at_utc": stamp(), "scope": "Free OPRA metadata and bounded development quote coverage; no statistical study or Databento download",
               "databento": databento_check(plan, args.output, key)}
    if not args.skip_massive:
        massive_key = os.getenv("MASSIVE_API_KEY") or values.get("MASSIVE_API_KEY")
        if not massive_key:
            raise SystemExit("MASSIVE_API_KEY is not configured")
        summary["massive"] = massive_check(plan, args.output, massive_key)
    write_json(args.output / "coverage.json", summary)
    print("Coverage receipt:", args.output / "coverage.json")


if __name__ == "__main__":
    main()
