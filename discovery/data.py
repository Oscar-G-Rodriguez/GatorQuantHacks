"""Past-only daily features and outcomes confined to an explicit development window."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .io import digest, identity, read_json, write_json

CONTROLS = ["past_return_5", "past_return_20", "past_vol_20", "past_log_volume", "market_past_return_5"]


def validate_config(c):
    start, end = pd.Timestamp(c["start"]), pd.Timestamp(c["end"])
    if not pd.Timestamp("2024-01-01") <= start < end <= pd.Timestamp("2025-12-31"):
        raise ValueError("This Massive development adapter accepts only 2024-2025; later/sealed windows are excluded")
    for key in ("horizons", "lags"):
        values = c[key]
        if not values or len(values) != len(set(values)) or any(type(v) is not int or v < (1 if key == "horizons" else 0) or v > 252 for v in values):
            raise ValueError(f"Invalid {key}")
    if not 1 <= c["resamples"] <= 100000 or not 1 <= c["resample_batch"] <= c["resamples"]:
        raise ValueError("Invalid resampling budget")
    if c["block_sessions"] < max(c["horizons"]) or c["sequence_sessions"] < 1:
        raise ValueError("Block length must cover the largest overlapping target horizon")
    if len(set(c["categories"])) != len(c["categories"]) or len(c["categories"]) < 2:
        raise ValueError("Supply at least two distinct categories for the sequence study")
    return c


def build_panel(bars, events, c):
    """At date t close, controls use t and earlier; outcomes start after t.

    Missing issuer sessions are NOT compressed into shorter multi-day outcomes.
    A benchmark-observed date grid defines trading sessions; missing bars leave
    affected features/outcomes absent, never backward filled.
    """
    validate_config(c)
    bars, events = bars.copy(), events.copy()
    bars["date"] = pd.to_datetime(bars["date"])
    if bars.duplicated(["ticker", "date"]).any():
        raise ValueError("Duplicate ticker/date bars")
    if bars.empty or (bars["close"] <= 0).any() or (~np.isfinite(bars["close"])).any():
        raise ValueError("Empty/nonpositive/nonfinite closes")
    if (bars["volume"] < 0).any():
        raise ValueError("Negative volume")
    if not bars["date"].between(c["start"], c["end"]).all():
        raise ValueError("Input bars cross the development boundary")
    benchmark = bars[bars.ticker == c["benchmark"]].set_index("date").sort_index()
    if len(benchmark) < 60:
        raise ValueError("Insufficient benchmark grid; at least 60 observed sessions needed")
    dates = benchmark.index
    if not bars.date.isin(dates).all():
        raise ValueError("Issuer bars outside benchmark-observed session grid")
    if events.empty:
        events = pd.DataFrame(columns=["ticker", "issuer", "filing_date", "available_date", "accession", "category"])
    else:
        if events[["ticker", "issuer", "accession", "category", "filing_date", "available_date"]].isna().any().any():
            raise ValueError("Event identity/clock fields cannot be missing")
        for name in ("filing_date", "available_date"):
            events[name] = pd.to_datetime(events[name])
        if not events.filing_date.between(c["start"], c["end"]).all():
            raise ValueError("Event filings cross the development boundary")
        if (events.available_date <= events.filing_date).any():
            raise ValueError("Daily adapter requires availability after filing date")
        events = events.drop_duplicates(["issuer", "ticker", "accession", "category"])
    parts = []
    for ticker in sorted(set(bars.ticker) - {c["benchmark"]}):
        g = bars[bars.ticker == ticker].set_index("date").reindex(dates)
        close, ret = g.close, g.close.pct_change(fill_method=None)
        p = pd.DataFrame({"date": dates, "ticker": ticker, "close": close.values})
        p["session"] = np.arange(len(dates))
        p["past_return_5"] = close.pct_change(5, fill_method=None).values
        p["past_return_20"] = close.pct_change(20, fill_method=None).values
        p["past_vol_20"] = ret.rolling(20, min_periods=20).std().values
        p["past_log_volume"] = np.log1p(g.volume).values
        p["market_past_return_5"] = benchmark.close.pct_change(5, fill_method=None).values
        for h in c["horizons"]:
            forward = pd.concat([ret.shift(-j) for j in range(1, h + 1)], axis=1)
            complete = forward.notna().all(axis=1)
            p[f"return_{h}"] = (close.shift(-h) / close - 1).where(complete).values
            p[f"volatility_{h}"] = np.sqrt((forward ** 2).mean(axis=1)).where(complete).values
            p[f"target_end_{h}"] = pd.Series(dates, index=dates).shift(-h).values
        e = events[events.ticker == ticker].copy()
        p["issuer"] = str(e.issuer.iloc[0]) if len(e) else ticker
        if len(e) and e.issuer.nunique() > 1:
            raise ValueError("Ticker maps to multiple issuers; resolve symbol history first")
        aligned = []
        for row in e.itertuples():
            i = dates.searchsorted(row.available_date)
            if i < len(dates) and row.category in c["categories"]:
                aligned.append((int(i), row))
        # Availability is one date, never repeated on every later day.
        for cat in c["categories"]:
            p[f"event__{cat}"] = 0.0
            for i, row in aligned:
                if row.category == cat:
                    p.loc[i, f"event__{cat}"] = 1.0
        a, b = c["categories"][:2]
        p["sequence_a_before_b"] = 0.0
        p["recent_a"] = 0.0
        for i in range(len(dates)):
            p.loc[i, "recent_a"] = float(any(row.category == a and 0 < i - j <= c["sequence_sessions"] for j, row in aligned))
        for i, second in aligned:
            if second.category == b and any(first.category == a and 0 < i - j <= c["sequence_sessions"] and first.filing_date < second.filing_date and first.accession != second.accession for j, first in aligned):
                p.loc[i, "sequence_a_before_b"] = 1.0
        parts.append(p)
    if not parts:
        raise ValueError("No research issuers beside the benchmark")
    panel = pd.concat(parts, ignore_index=True).sort_values(["date", "ticker"]).reset_index(drop=True)
    features = [f"event__{cat}" for cat in c["categories"]] + ["sequence_a_before_b"]
    # Inputs excluded when missing; outcomes excluded separately for each horizon.
    panel = panel.dropna(subset=CONTROLS)
    for col in ["date"] + [f"target_end_{h}" for h in c["horizons"]]:
        panel[col] = pd.to_datetime(panel[col]).dt.strftime("%Y-%m-%d")
    quality = {
        "rows": len(panel), "issuers": panel.issuer.nunique(), "tickers": panel.ticker.nunique(),
        "dates": panel.date.nunique(), "benchmark_sessions": len(dates),
        "missing_issuer_bar_rows": sum(int(len(dates) - len(bars[bars.ticker == t])) for t in set(bars.ticker) - {c["benchmark"]}),
        "event_source_rows": len(events), "event_rows_not_aligned_within_grid": len(events) - sum(len(events[(events.ticker == t) & (events.available_date <= dates[-1])]) for t in set(bars.ticker) - {c["benchmark"]}),
        "feature_positive_rows": {f: int(panel[f].sum()) for f in features},
        "target_missing_rows": {f"{kind}_{h}": int(panel[f"{kind}_{h}"].isna().sum()) for h in c["horizons"] for kind in ["return", "volatility"]},
        "weighting": "Equal eligible ticker-date rows; share classes may overweight an issuer",
        "limits": ["Retrospective labels; assumed next-calendar-day availability, aligned to next observed session close", "Observed benchmark dates are a data-derived session grid, not an independently verified exchange calendar", "No pre-2024 event history; sequence features are left-censored", "Split-adjusted price returns exclude dividends; no trade/P&L interpretation"],
    }
    return panel, features, quality


def snapshot(output, bars, events, c, provenance):
    output = Path(output)
    panel, features, quality = build_panel(bars, events, c)
    output.mkdir(parents=True, exist_ok=False)
    panel.to_csv(output / "panel.csv", index=False)
    write_json(output / "config.json", c)
    meta = {"schema": 1, "created_at": provenance.get("created_at"), "provenance": provenance, "features": features, "controls": CONTROLS, "quality": quality, "files": {n: digest(output / n) for n in ["panel.csv", "config.json"]}}
    meta["snapshot_id"] = identity(meta)
    write_json(output / "snapshot.json", meta)
    return meta


def load_snapshot(path):
    path = Path(path)
    meta = read_json(path / "snapshot.json")
    unsigned = {k: v for k, v in meta.items() if k != "snapshot_id"}
    if identity(unsigned) != meta["snapshot_id"]:
        raise ValueError("Snapshot manifest changed")
    for name, expected in meta["files"].items():
        if digest(path / name) != expected:
            raise ValueError(f"Snapshot hash mismatch: {name}")
    config = validate_config(read_json(path / "config.json"))
    panel = pd.read_csv(path / "panel.csv")
    return panel, meta, config
