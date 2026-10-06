"""H05: development-only discovery; no simulated trades."""
from __future__ import annotations

import numpy as np
import pandas as pd
from discovery.methods import number, correlation, residuals, distance_correlation, pairs, folds, block_indices

def analyze(panel, meta, c, task):
    rows = []
    for p, r in pairs(panel, meta, c, [0]):
        if r["status"] == "measured":
            # Fixed issuer effects remove time-invariant issuer levels. No future
            # factor returns or target values enter the controls.
            # Within-issuer demeaning is equivalent to including issuer dummy
            # columns and keeps the linear system small for a large universe.
            cols = meta["controls"] + ["x", "y"]
            within = p[cols] - p.groupby("issuer")[cols].transform("mean")
            z = within[meta["controls"]].to_numpy()
            rx, ry = residuals(within.x.to_numpy(), z), residuals(within.y.to_numpy(), z)
            if np.dot(rx, rx) < 1e-12:
                r.update(status="inconclusive", reason="Candidate is collinear with controls")
            else:
                r.update(partial_pearson=number(correlation(rx, ry)), adjusted_coefficient=number(np.dot(rx, ry) / np.dot(rx, rx)), controls=meta["controls"], issuer_fixed_effects=True, inference="Descriptive linear conditional association; no causal identification")
        rows.append(r)
    return rows, {}


if __name__ == "__main__":
    import sys
    from discovery.cli import main
    raise SystemExit(main(["study", "--id", "H05", *sys.argv[1:]]))
