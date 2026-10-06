"""H03: development-only discovery; no simulated trades."""
from __future__ import annotations

import numpy as np
import pandas as pd
from discovery.methods import number, correlation, residuals, distance_correlation, pairs, folds, block_indices

def analyze(panel, meta, c, task):
    rows = []
    for p, r in pairs(panel, meta, c):
        if r["status"] == "measured":
            r.update(pearson=number(correlation(p.x, p.y)), spearman=number(correlation(p.x, p.y, True)))
            # Within-date estimates avoid pooling levels across issuers; dates
            # without cross-sectional feature variation are visibly unsupported.
            estimates = [correlation(g.x, g.y) for _, g in p.groupby("date") if len(g) >= 3]
            estimates = [v for v in estimates if np.isfinite(v)]
            r.update(within_date_mean_pearson=number(np.mean(estimates)) if estimates else None, supported_cross_section_dates=len(estimates))
        rows.append(r)
    return rows, {}


if __name__ == "__main__":
    import sys
    from discovery.cli import main
    raise SystemExit(main(["study", "--id", "H03", *sys.argv[1:]]))
