"""H06: development-only discovery; no simulated trades."""
from __future__ import annotations

import numpy as np
import pandas as pd
from discovery.methods import number, correlation, residuals, distance_correlation, pairs, folds, block_indices

def analyze(panel, meta, c, task):
    rows = []
    pair_records, balance_records = [], []
    dates = sorted(panel.date.unique())
    # Learn distance scales only on the earliest 40% of development dates.
    cutoff = dates[max(1, int(.4 * len(dates)))]
    early = panel[panel.date < cutoff]
    scale = early[meta["controls"]].std().replace(0, 1).fillna(1).to_numpy()
    for p, r in pairs(panel[panel.date >= cutoff], meta, c, [0]):
        if r["status"] == "measured":
            differences, distances, event_dates, issuers = [], [], [], []
            event_covariates, control_covariates = [], []
            for _, g in p.groupby("issuer"):
                controls = g[(g.x == 0) & (g[meta["features"]].sum(axis=1) == 0)]
                used = set()
                for e in g[g.x == 1].sort_values("date").itertuples():
                    d = pd.Timestamp(e.date)
                    pool = controls[(pd.to_datetime(controls.date) - d).abs().dt.days <= 60]
                    # Disjoint outcomes prevent a convenient control sharing the
                    # event's outcome window. Matching never sees either outcome.
                    pool = pool[pool[f"target_end_{r['horizon']}"] < e.date]
                    pool = pool[~pool.index.isin(used)]
                    if pool.empty:
                        continue
                    v = np.array([getattr(e, name) for name in meta["controls"]])
                    distance = np.sqrt(np.mean(((pool[meta["controls"]].to_numpy() - v) / scale) ** 2, axis=1))
                    best = int(np.argmin(distance))
                    if distance[best] > 2:
                        continue
                    row = pool.iloc[best]
                    used.add(pool.index[best])
                    differences.append(e.y - row.y)
                    distances.append(distance[best])
                    event_dates.append(e.date)
                    issuers.append(e.issuer)
                    event_covariates.append(v)
                    control_covariates.append(row[meta["controls"]].to_numpy(dtype=float))
                    pair_records.append({"feature": r["feature"], "target": r["target"], "horizon": r["horizon"],
                                         "issuer": e.issuer, "event_date": e.date, "control_date": row.date,
                                         "event_outcome": number(e.y), "control_outcome": number(row.y),
                                         "difference": number(e.y - row.y), "control_distance": number(distance[best])})
            r.update(matched_pairs=len(differences), matched_issuers=len(set(issuers)), matched_dates=len(set(event_dates)), average_control_distance=number(np.mean(distances)) if distances else None, matched_mean_difference=number(np.mean(differences)) if differences else None, scale_training_end_exclusive=cutoff, inference="Later-development events matched to prior same-issuer ordinary days without replacement, within 60 calendar days and disjoint outcomes, RMS standardized caliper 2; descriptive, no causal claim")
            if len(differences) < c["min_positive"] or len(set(issuers)) < c["min_issuers"]:
                r.update(status="inconclusive", reason="Insufficient matched pairs/issuers")
            if differences:
                r["matched_median_difference"] = number(np.median(differences))
                balance = (np.mean(event_covariates, axis=0) - np.mean(control_covariates, axis=0)) / scale
                r["max_absolute_standardized_control_difference"] = number(np.max(np.abs(balance)))
                balance_records.extend({"feature": r["feature"], "target": r["target"], "horizon": r["horizon"],
                                        "control": name, "standardized_mean_difference": number(value),
                                        "standardizer": "Early-development panel SD; descriptive balance, no causal threshold"}
                                       for name, value in zip(meta["controls"], balance))
                values, ids = np.asarray(differences), np.asarray(issuers)
                leave_one = [values[ids != issuer].mean() for issuer in sorted(set(issuers)) if np.any(ids != issuer)]
                r["leave_one_issuer_minimum"] = number(min(leave_one)) if leave_one else None
                r["leave_one_issuer_maximum"] = number(max(leave_one)) if leave_one else None
                r["matched_pair_interval_available"] = False
        rows.append(r)
    return rows, {"matched_pairs": pair_records, "covariate_balance": balance_records,
                  "inference": "Retained pairs, balance and issuer sensitivity are descriptive; dependent paired confidence intervals remain unimplemented"}


if __name__ == "__main__":
    import sys
    from discovery.cli import main
    raise SystemExit(main(["study", "--id", "H06", *sys.argv[1:]]))
