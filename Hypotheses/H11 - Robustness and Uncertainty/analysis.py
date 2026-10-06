"""H11: development-only discovery; no simulated trades."""
from __future__ import annotations

import numpy as np
import pandas as pd
from discovery.methods import number, correlation, residuals, distance_correlation, pairs, folds, block_indices
from discovery.methods import moments, correlation_moments

def analyze(panel, meta, c, task):
    rows = []
    rng = np.random.default_rng(task["seed"])
    for p, r in pairs(panel, meta, c):
        if r["status"] != "measured":
            rows.append(r)
            continue
        dates = sorted(p.date.unique())
        if len(dates) < 4 * c["block_sessions"]:
            r.update(status="inconclusive", reason="Fewer than four configured date blocks")
            rows.append(r)
            continue
        x, y = p.x.to_numpy(), p.y.to_numpy()
        date_moments = moments(p, "date")
        issuer_moments = moments(p, "issuer")
        observed = correlation(x, y)
        draws = []
        for _ in range(task["draws"]):
            ix = block_indices(dates, c["block_sessions"], rng)
            v = correlation_moments(date_moments[ix].sum(axis=0))
            if np.isfinite(v):
                draws.append(number(v))
        # These bootstrap distributions are NOT null distributions/p-values.
        r.update(pearson=number(observed), bootstrap_values=draws, requested_draws=task["draws"], valid_draws=len(draws), method="Moving date-block bootstrap, observed issuers fixed")
        total = date_moments.sum(axis=0)
        exclusions = [correlation_moments(total - row) for row in issuer_moments]
        exclusions = [v for v in exclusions if np.isfinite(v)]
        r.update(leave_one_issuer_min=number(min(exclusions)) if exclusions else None, leave_one_issuer_max=number(max(exclusions)) if exclusions else None)
        rows.append(r)
    losses = pd.DataFrame(task.get("paired_losses", []))
    families = ["disclosures", "sequences", "all_events"]
    if c.get("interaction_controls"):
        families.append("disclosures_and_interactions")
    if c.get("event_validation_scores"):
        families += [f + "__event_rows" for f in list(families)]
    planned = [(feature, f"{kind}_{h}", h, model) for feature in families for h in c["horizons"] for kind in ["return", "volatility"] for model in ["ridge", "hist_gradient_boosting"]]
    for feature, target, h, model in planned:
        p = losses[(losses.feature == feature) & (losses.target == target) & (losses.model == model)] if not losses.empty else losses
        if p.empty:
            rows.append({"feature": feature, "target": target, "horizon": h, "lag": 0, "model": model, "statistic": "paired_mse_improvement", "rows": 0, "status": "inconclusive", "reason": "No supported chronological paired predictions; retained in planned search family"})
            continue
        dates = sorted(p.date.unique())
        r = {"feature": feature, "target": target, "horizon": int(h), "lag": 0, "model": model, "statistic": "paired_mse_improvement", "rows": len(p), "dates": len(dates), "status": "measured", "reason": None, "folds_observed": sorted(p.fold.unique().tolist())}
        if len(dates) < 4 * c["block_sessions"]:
            r.update(status="inconclusive", reason="Fewer than four validation date blocks")
        else:
            values = p.difference.to_numpy()
            sums = p.groupby("date", sort=True).difference.agg(["sum", "count"]).to_numpy()
            draws = []
            for _ in range(task["draws"]):
                total, count = sums[block_indices(dates, c["block_sessions"], rng)].sum(axis=0)
                draws.append(float(total / count))
            exclusions = [p[p.issuer != i].difference.mean() for i in p.issuer.unique() if len(p[p.issuer != i])]
            r.update(paired_mse_improvement=number(values.mean()), bootstrap_values=draws, requested_draws=task["draws"], valid_draws=len(draws), leave_one_issuer_min=number(min(exclusions)) if exclusions else None, leave_one_issuer_max=number(max(exclusions)) if exclusions else None, method="Moving validation-date blocks of paired held-development losses; observed issuers fixed")
        rows.append(r)
    return rows, {}


if __name__ == "__main__":
    import sys
    from discovery.cli import main
    raise SystemExit(main(["study", "--id", "H11", *sys.argv[1:]]))
