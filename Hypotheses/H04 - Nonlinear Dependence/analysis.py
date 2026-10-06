"""H04: development-only discovery; no simulated trades."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_regression
from discovery.methods import number, correlation, residuals, distance_correlation, pairs, folds, block_indices

def analyze(panel, meta, c, task):
    rows = []
    rng = np.random.default_rng(task["seed"])
    for p, r in pairs(panel, meta, c, [0]):
        if r["status"] == "measured":
            # MI can use the whole eligible panel; only the quadratic-memory
            # distance estimator needs subsampling. Do not destroy rare-event
            # support for both measurements by sampling them together.
            mi = mutual_info_regression(p[["x"]], p.y, discrete_features=True, random_state=task["seed"])[0]
            r.update(mutual_information_nats=number(mi), mi_estimation_rows=len(p))
            sample = p.iloc[np.sort(rng.choice(len(p), min(len(p), c["nonlinear_max_rows"]), replace=False))]
            if (sample.x != 0).sum() < 4 or (sample.x == 0).sum() < 4:
                r.update(distance_correlation=None, distance_status="inconclusive", distance_reason="Too few events in bounded uniform subsample")
            else:
                r.update(distance_correlation=number(distance_correlation(sample.x, sample.y)), distance_status="measured")
            r.update(distance_estimation_rows=len(sample), inference="Descriptive estimators; neither direction nor conditional novelty nor an independence p-value")
        rows.append(r)
    return rows, {}


if __name__ == "__main__":
    import sys
    from discovery.cli import main
    raise SystemExit(main(["study", "--id", "H04", *sys.argv[1:]]))
