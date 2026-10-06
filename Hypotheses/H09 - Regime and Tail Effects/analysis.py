"""H09: development-only discovery; no simulated trades."""
from __future__ import annotations

import numpy as np
import pandas as pd
from discovery.methods import number, correlation, residuals, distance_correlation, pairs, folds, block_indices

def analyze(panel, meta, c, task):
    rows = []
    dates = sorted(panel.date.unique())
    cutoff = dates[int(.4 * len(dates))]
    threshold = panel.loc[panel.date < cutoff, "past_vol_20"].median()
    for p, r in pairs(panel[panel.date >= cutoff], meta, c, [0]):
        for regime in ["low_past_vol", "high_past_vol"]:
            g = p[p.past_vol_20 >= threshold] if regime.startswith("high") else p[p.past_vol_20 < threshold]
            event, ordinary = g[g.x == 1].y, g[g.x == 0].y
            rr = {**r, "regime": regime, "rows": len(g), "positive_rows": len(event), "past_vol_threshold": number(threshold), "threshold_training_end_exclusive": cutoff}
            event_issuers = g.loc[g.x == 1, "issuer"].nunique()
            rr["positive_issuers_in_regime"] = event_issuers
            if len(event) < c["min_positive"] or len(ordinary) < c["min_rows"] or event_issuers < c["min_issuers"]:
                rr.update(status="inconclusive", reason="Sparse regime event or ordinary group")
            else:
                rr.update(status="measured", reason=None, event_mean=number(event.mean()), ordinary_mean=number(ordinary.mean()), event_q10=number(event.quantile(.1)), ordinary_q10=number(ordinary.quantile(.1)), event_q90=number(event.quantile(.9)), ordinary_q90=number(ordinary.quantile(.9)))
                if r["target"].startswith("return"):
                    rr.update(event_downside_probability=float((event < -.02).mean()), ordinary_downside_probability=float((ordinary < -.02).mean()), downside_threshold=-.02)
            rows.append(rr)
    return rows, {"scope": "Empirical conditional quantiles and fixed downside counts; no fitted quantile/probability forecast or causal regime identification"}


if __name__ == "__main__":
    import sys
    from discovery.cli import main
    raise SystemExit(main(["study", "--id", "H09", *sys.argv[1:]]))
