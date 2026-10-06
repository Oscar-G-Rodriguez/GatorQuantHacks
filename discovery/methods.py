"""Nine bounded discovery studies; every insufficient comparison remains visible.

These are first implementations of the README workflows, not a declaration that
every proposed method has been implemented or that a trading signal is proven.
"""
from __future__ import annotations

import importlib.util

import numpy as np
import pandas as pd

from .io import ROOT, STUDIES


def handler(study):
    """Load the implementation owned by its hypothesis folder."""
    path = ROOT / "Hypotheses" / STUDIES[study] / "analysis.py"
    spec = importlib.util.spec_from_file_location(f"discovery.study_{study}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.analyze


def number(x):
    return float(x) if np.isfinite(x) else None


def correlation(x, y, rank=False):
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    if rank:
        x, y = pd.Series(x).rank().to_numpy(), pd.Series(y).rank().to_numpy()
    return np.corrcoef(x, y)[0, 1]


def residuals(y, z):
    z = np.column_stack([np.ones(len(z)), z])
    return y - z @ np.linalg.lstsq(z, y, rcond=None)[0]


def moments(frame, group):
    """Sufficient statistics preserve row weighting without copying every row."""
    v = pd.DataFrame({"group": frame[group], "n": 1., "x": frame.x, "y": frame.y, "xx": frame.x ** 2, "yy": frame.y ** 2, "xy": frame.x * frame.y})
    return v.groupby("group", sort=True)[["n", "x", "y", "xx", "yy", "xy"]].sum().to_numpy()


def correlation_moments(v):
    n, x, y, xx, yy, xy = v
    if n < 3:
        return np.nan
    vx, vy = max(0., xx - x * x / n), max(0., yy - y * y / n)
    return (xy - x * y / n) / np.sqrt(vx * vy) if vx > 0 and vy > 0 else np.nan


def distance_correlation(x, y):
    """Biased descriptive sample distance correlation, O(nÂ²) bounded by config."""
    def centered(v):
        v = np.asarray(v)
        a = np.abs(v[:, None] - v[None, :])
        return a - a.mean(axis=0) - a.mean(axis=1)[:, None] + a.mean()
    a, b = centered(x), centered(y)
    denominator = np.sqrt(np.mean(a * a) * np.mean(b * b))
    return np.sqrt(max(0, np.mean(a * b)) / denominator) if denominator > 0 else np.nan


def pairs(panel, meta, c, lags=None):
    for feature in meta["features"]:
        for lag in (c["lags"] if lags is None else lags):
            frame = panel.copy()
            frame["x"] = frame.groupby("ticker", sort=False)[feature].shift(lag)
            # Guard against compressing missing control dates into short lags.
            if lag:
                prior = frame.groupby("ticker", sort=False).session.shift(lag)
                good = frame.session - prior == lag
                frame.loc[~good, "x"] = np.nan
            for h in c["horizons"]:
                for kind in ["return", "volatility"]:
                    target = f"{kind}_{h}"
                    p = frame.dropna(subset=["x", target] + meta["controls"]).copy()
                    p["y"] = p[target]
                    spec = {"feature": feature, "lag": lag, "target": target, "horizon": h}
                    positive = p[p.x != 0]
                    support = {"rows": len(p), "dates": p.date.nunique(), "issuers": p.issuer.nunique(), "positive_rows": len(positive), "positive_issuers": positive.issuer.nunique(), "positive_dates": positive.date.nunique()}
                    why = None
                    if len(p) < c["min_rows"] or p.x.nunique() < 2 or p.y.nunique() < 2:
                        why = "Too few rows or no feature/target variation"
                    elif support["positive_rows"] < c["min_positive"] or support["positive_issuers"] < c["min_issuers"]:
                        why = "Insufficient event/issuer support"
                    yield p, {**spec, **support, "status": "inconclusive" if why else "measured", "reason": why}












def folds(panel, h):
    """Date splits with actual target-end purge, not arbitrary row offsets."""
    dates = sorted(panel.date.unique())
    if len(dates) < 4:
        for i in range(3):
            empty = pd.Series(False, index=panel.index)
            yield i, empty, empty, None, None
        return
    cut = [int(len(dates) * f) for f in [.4, .6, .8]] + [len(dates)]
    for i in range(3):
        start = dates[cut[i]]
        stop = dates[cut[i + 1]] if cut[i + 1] < len(dates) else "9999-12-31"
        train = (panel.date < start) & (panel[f"target_end_{h}"] < start)
        valid = (panel.date >= start) & (panel.date < stop)
        yield i, train, valid, start, stop








def block_indices(dates, block, rng):
    """Moving date blocks carry the entire cross-section together.

    Uncertainty is conditional on the observed issuer panel; no claim of a
    two-way issuer population bootstrap. Consecutive blocks preserve temporal
    outcome overlap, subject to stationarity/block-length assumptions.
    """
    n = len(dates)
    starts = rng.integers(0, max(1, n - block + 1), size=int(np.ceil(n / block)))
    return np.concatenate([np.arange(s, min(n, s + block)) for s in starts])[:n]
