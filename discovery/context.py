"""Prepare an immutable development panel with exact same-filing context.

All work here is local data preparation. Statistical calculations still run
through the existing scheduled discovery task graph.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .data import load_snapshot
from .io import digest, identity, now, read_json, write_json


def attach_context(panel, config, context_rows, leads):
    p = panel.copy()
    issuers = set(str(r["cik"]).zfill(10) for r in context_rows)
    covered = p.issuer.astype(str).str.zfill(10).isin(issuers)
    dates = np.array(sorted(p.date.unique()))
    # The first 20 unavailable-control sessions are absent from panel. Context
    # mapping still uses actual dates; earlier tags never become first-day tags.
    index = {}
    for i, row in p.iterrows():
        index.setdefault((str(row.issuer).zfill(10), row.date), []).append(i)
    lead_keys = {(str(r["cik"]).zfill(10), r["accession_number"], r["tertiary_category"]) for r in leads}
    groups = config["cotag_groups"]
    for group in groups:
        p["context__" + group] = np.where(covered, 0.0, np.nan)
        for category in config["categories"]:
            p["cotag__" + category + "__" + group] = np.where(covered, 0.0, np.nan)
    filings = {}
    for r in context_rows:
        if not r.get("cik") or not r.get("accession_number") or not r.get("tertiary_category"):
            raise ValueError("Context rows require CIK, accession and category")
        if not config["start"] <= r.get("filing_date", "") <= config["end"]:
            raise ValueError("Context row lies outside development")
        key = (str(r["cik"]).zfill(10), r["accession_number"])
        item = filings.setdefault(key, {"date": r["filing_date"], "categories": set()})
        if item["date"] != r["filing_date"]:
            raise ValueError("One filing identity has conflicting dates")
        item["categories"].add(r["tertiary_category"])
    for (issuer, accession), filing in filings.items():
        available = (pd.Timestamp(filing["date"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        if not len(dates) or available < dates[0]:
            continue
        offset = dates.searchsorted(available)
        if offset == len(dates):
            continue
        row_indices = index.get((issuer, dates[offset]))
        if row_indices is None:
            continue
        cats = filing["categories"]
        for group, members in groups.items():
            if cats & set(members):
                p.loc[row_indices, "context__" + group] = 1.0
                for category in config["categories"]:
                    if category in cats and (issuer, accession, category) in lead_keys:
                        # Exclude source events absent from the frozen baseline;
                        # this run studies context, not a silent mapping repair.
                        for row_index in row_indices:
                            if p.loc[row_index, "event__" + category] == 1:
                                p.loc[row_index, "cotag__" + category + "__" + group] = 1.0
    return p


def prepare(base, context, output):
    panel, meta, config = load_snapshot(base)
    report = read_json(context / "download-report.json")
    if not report["complete"]:
        raise ValueError("Partial issuer context cannot become a complete snapshot")
    rows = []
    for obj in report["objects"]:
        source = context / obj["file"]
        if digest(source) != obj["sha256"]:
            raise ValueError("Context object hash mismatch")
        rows.extend(read_json(source))
    lead_path = context / "lead-context.json"
    if digest(lead_path) != report["lead_context_sha256"]:
        raise ValueError("Lead context hash mismatch")
    enriched = attach_context(panel, config, rows, read_json(lead_path))
    output.mkdir(parents=True, exist_ok=False)
    enriched.to_csv(output / "panel.csv", index=False)
    write_json(output / "config.json", config)
    result = {**meta, "created_at": now(), "provenance": {**meta["provenance"],
              "context": {"base_snapshot_id": meta["snapshot_id"], "download_report_sha256": digest(context / "download-report.json"),
                          "objects": [{"file": o["file"], "sha256": o["sha256"]} for o in report["objects"]],
                          "join": "CIK plus accession; filing+1 calendar day assumed, then next observed session close",
                          "scope": "Context is missing for issuers outside the existing lead sample; baseline events unchanged"}},
              "context_features": ["context__" + g for g in config["cotag_groups"]],
              "files": {n: digest(output / n) for n in ["panel.csv", "config.json"]}}
    result["quality"] = {**meta["quality"], "context_covered_rows": int(enriched[result["context_features"][0]].notna().sum()),
                         "context_feature_positive_rows": {f: int(enriched[f].sum()) for f in result["context_features"]}}
    result.pop("snapshot_id", None)
    result["snapshot_id"] = identity(result)
    write_json(output / "snapshot.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print({"snapshot_id": prepare(args.base, args.context, args.output)["snapshot_id"]})
