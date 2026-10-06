"""H10: development-only discovery; no simulated trades."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from discovery.methods import number, correlation, residuals, distance_correlation, pairs, folds, block_indices

def analyze(panel, meta, c, task):
    dates = sorted(panel.date.unique())
    cut = dates[int(.4 * len(dates))]
    p = panel[panel.date < cut]
    features = meta["controls"] + meta["features"]
    active = [f for f in features if p[f].nunique() > 1]
    rows = []
    for i, a in enumerate(features):
        for b in features[i + 1:]:
            valid = a in active and b in active
            rows.append({"feature": a, "other_feature": b, "rows": len(p), "status": "measured" if valid else "inconclusive", "reason": None if valid else "Constant feature in early training window", "pearson": number(correlation(p[a], p[b])) if valid else None, "spearman": number(correlation(p[a], p[b], True)) if valid else None})
    extra = {"training_stop_exclusive": cut, "constant_features": [f for f in features if f not in active]}
    if active:
        x = StandardScaler().fit_transform(p[active])
        fit = PCA().fit(x)
        extra.update(pca_features=active, explained_variance_ratio=fit.explained_variance_ratio_.tolist(), loadings=fit.components_.tolist(), inference="Training-only linear redundancy; correlation does not prove interchangeable predictive information")
    # Optional context is known only for the lead issuers downloaded. Pairwise
    # cohorts preserve that missingness instead of coding other issuers as zero.
    context = meta.get("context_features", [])
    for i, a in enumerate(context):
        for b in meta["controls"] + [f for f in meta["features"] if f.startswith("event__")] + context[i + 1:]:
            q = p.dropna(subset=[a, b])
            valid = len(q) >= c["min_rows"] and q[a].nunique() > 1 and q[b].nunique() > 1
            rows.append({"feature": a, "other_feature": b, "rows": len(q), "issuers": q.issuer.nunique(),
                         "status": "measured" if valid else "inconclusive", "reason": None if valid else "Insufficient pairwise context coverage/variation",
                         "pearson": number(correlation(q[a], q[b])) if valid else None,
                         "spearman": number(correlation(q[a], q[b], True)) if valid else None,
                         "inference": "Early-development input association on context-covered issuers; no future target"})
    return rows, extra


if __name__ == "__main__":
    import sys
    from discovery.cli import main
    raise SystemExit(main(["study", "--id", "H10", *sys.argv[1:]]))
