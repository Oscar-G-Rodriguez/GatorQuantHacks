"""H07: development-only discovery; no simulated trades."""
from __future__ import annotations

import numpy as np
import pandas as pd
from discovery.methods import number, correlation, residuals, distance_correlation, pairs, folds, block_indices

def analyze(panel, meta, c, task):
    rows = []
    b = f"event__{c['categories'][1]}"
    for h in c["horizons"]:
        for kind in ["return", "volatility"]:
            target = f"{kind}_{h}"
            p = panel.dropna(subset=[target]).copy()
            p["b_only"] = ((p[b] == 1) & (p.sequence_a_before_b == 0)).astype(int)
            # A and B from the same accession/date cannot form a sequence.
            x = np.column_stack([np.ones(len(p)), p.recent_a, p[b], p.sequence_a_before_b, p[meta["controls"]]])
            supported = np.linalg.matrix_rank(x) == x.shape[1]
            r = {"feature": "sequence_a_before_b", "target": target, "horizon": h, "lag": 0, "rows": len(p), "sequence_rows": int(p.sequence_a_before_b.sum()), "b_only_rows": int(p.b_only.sum()), "sequence_issuers": p.loc[p.sequence_a_before_b == 1, "issuer"].nunique(), "status": "measured", "reason": None}
            if not supported or min(r["sequence_rows"], r["b_only_rows"]) < c["min_positive"] or r["sequence_issuers"] < c["min_issuers"]:
                r.update(status="inconclusive", reason="Sparse sequences/comparison group or rank-deficient interaction design")
            else:
                r["interaction_coefficient"] = number(np.linalg.lstsq(x, p[target], rcond=None)[0][3])
            rows.append(r)
    if c.get("interaction_controls") or c.get("cotag_groups"):
        rows.extend(cross_variables(panel, meta, c))
    return rows, {"cross_variable_inference": "Exploratory adjusted linear association; no causal claim, coefficient interval or independent confirmation"}


def cross_variables(panel, meta, c):
    """Compare interaction terms with their main effects on the same rows.

    Continuous inputs use fixed early-development scales. Same-filing terms are
    prepared from exact CIK/accession matches, never a product of same-day tags.
    Fixed issuer effects remove issuer averages within each eligible cohort.
    """
    dates = sorted(panel.date.unique())
    cutoff = dates[max(1, int(.4 * len(dates)))]
    early = panel[panel.date < cutoff]
    center = early[meta["controls"]].mean()
    scale = early[meta["controls"]].std().replace(0, 1).fillna(1)
    result = []
    for category in c["categories"]:
        event = "event__" + category
        variables = [(name, None) for name in c.get("interaction_controls", [])]
        variables += [("context__" + group, "cotag__" + category + "__" + group) for group in c.get("cotag_groups", {})]
        for other, exact_term in variables:
            for h in c["horizons"]:
                for kind in ["return", "volatility"]:
                    target = f"{kind}_{h}"
                    needed = [target, event, other] + meta["controls"] + ([exact_term] if exact_term else [])
                    p = panel[panel.date >= cutoff].dropna(subset=list(dict.fromkeys(needed))).copy()
                    e = p[event].to_numpy(dtype=float)
                    z = ((p[meta["controls"]] - center) / scale).to_numpy(dtype=float)
                    main = p[other].to_numpy(dtype=float) if exact_term else ((p[other] - center[other]) / scale[other]).to_numpy(dtype=float)
                    term = p[exact_term].to_numpy(dtype=float) if exact_term else e * main
                    with_context = int(np.sum(term > 0)) if exact_term else None
                    without_context = int(np.sum((e == 1) & (term == 0))) if exact_term else None
                    r = {"feature": event, "other_feature": other, "statistic": "interaction_coefficient",
                         "target": target, "horizon": h, "lag": 0, "rows": len(p), "positive_rows": int(e.sum()),
                         "positive_issuers": int(p.loc[p[event] == 1, "issuer"].nunique()),
                         "with_context_events": with_context, "without_context_events": without_context,
                         "scale_training_end_exclusive": cutoff, "status": "inconclusive", "reason": None,
                         "coefficient_interval_available": False,
                         "interpretation": "Interaction beyond main effects, five past controls and fixed issuer effects; development-selected association"}
                    if len(p) < c["min_rows"] or r["positive_rows"] < c["min_positive"] or r["positive_issuers"] < c["min_issuers"]:
                        r["reason"] = "Insufficient event/issuer/cohort support"
                    elif exact_term and min(with_context, without_context) < c["min_positive"]:
                        r["reason"] = "Insufficient events with or without exact same-filing co-tag"
                    elif not exact_term and np.std(main[e == 1]) <= 1e-12:
                        r["reason"] = "No usable within-event variation in the second variable"
                    else:
                        # A continuous main effect already belongs to z. A co-tag
                        # main effect needs its own column alongside event/term.
                        arrays = [p[target].to_numpy(dtype=float), e, term] + [z[:, j] for j in range(z.shape[1])]
                        if exact_term:
                            arrays.append(main)
                        a = pd.DataFrame(np.column_stack(arrays), index=p.index)
                        a = a - a.groupby(p.issuer).transform("mean")
                        y, x = a.iloc[:, 0].to_numpy(), a.iloc[:, 1:].to_numpy()
                        if np.linalg.matrix_rank(x) != x.shape[1]:
                            r["reason"] = "Rank-deficient interaction/main-effect design"
                        else:
                            coef = np.linalg.lstsq(x, y, rcond=None)[0]
                            r.update(status="measured", interaction_coefficient=number(coef[1]),
                                     event_main_coefficient=number(coef[0]), reason=None)
                    result.append(r)
    return result


if __name__ == "__main__":
    import sys
    from discovery.cli import main
    raise SystemExit(main(["study", "--id", "H07", *sys.argv[1:]]))
