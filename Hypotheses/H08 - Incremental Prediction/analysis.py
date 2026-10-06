"""H08: development-only discovery; no simulated trades."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from discovery.methods import number, correlation, residuals, distance_correlation, pairs, folds, block_indices

def analyze(panel, meta, c, task):
    rows, loss_records = [], []
    families = {"disclosures": [f for f in meta["features"] if f.startswith("event__")], "sequences": ["sequence_a_before_b"], "all_events": meta["features"]}
    if c.get("interaction_controls"):
        families["disclosures_and_interactions"] = families["disclosures"]
    for h in c["horizons"]:
        for kind in ["return", "volatility"]:
            target = f"{kind}_{h}"
            p = panel.dropna(subset=[target] + meta["controls"] + meta["features"])
            for family, features in families.items():
                for model in ["ridge", "hist_gradient_boosting"]:
                    for fold, train, valid, start, stop in folds(p, h):
                        a, v = p.loc[train], p.loc[valid]
                        r = {"feature": family, "target": target, "horizon": h, "lag": 0, "model": model, "fold": fold, "rows": len(v), "training_rows": len(a), "validation_start": start, "validation_stop_exclusive": stop, "status": "measured", "reason": None}
                        if len(a) < c["min_rows"] or len(v) < c["min_rows"] or a[features].sum().sum() < c["min_positive"] or v[features].sum().sum() < c["min_positive"]:
                            r.update(status="inconclusive", reason="Insufficient training/validation rows or candidate events")
                        else:
                            train_features, valid_features = a[features].copy(), v[features].copy()
                            if family == "disclosures_and_interactions":
                                for control in c["interaction_controls"]:
                                    mean, sd = a[control].mean(), a[control].std()
                                    sd = sd if sd > 0 else 1
                                    for feature in features:
                                        name = feature + "_x_" + control
                                        train_features[name] = a[feature] * (a[control] - mean) / sd
                                        valid_features[name] = v[feature] * (v[control] - mean) / sd
                            possible = any(candidate_split_possible(train_features[f].to_numpy(), 30) for f in train_features)
                            r["candidate_tree_split_possible"] = possible
                            if model == "hist_gradient_boosting" and not possible:
                                r.update(status="inconclusive", reason="No candidate column can form two leaves of 30 training rows; this model cannot test the candidate")
                                rows.append(r)
                                continue
                            def estimator():
                                if model == "ridge":
                                    return make_pipeline(StandardScaler(), Ridge(alpha=10.0))
                                # Disable random early-stopping validation; no
                                # temporal tuning is hidden inside the estimator.
                                return HistGradientBoostingRegressor(max_iter=60, max_leaf_nodes=7, min_samples_leaf=30, l2_regularization=10, early_stopping=False, random_state=task["seed"])
                            base, aug = estimator(), estimator()
                            base.fit(a[meta["controls"]], a[target])
                            aug.fit(pd.concat([a[meta["controls"]], train_features], axis=1), a[target])
                            lb = (v[target].to_numpy() - base.predict(v[meta["controls"]])) ** 2
                            la = (v[target].to_numpy() - aug.predict(pd.concat([v[meta["controls"]], valid_features], axis=1))) ** 2
                            r.update(baseline_mse=number(lb.mean()), augmented_mse=number(la.mean()), paired_mse_improvement=number((lb - la).mean()), relative_mse_improvement=number((lb.mean() - la.mean()) / lb.mean()) if lb.mean() else None)
                            loss_records.extend({"date": d, "issuer": issuer, "feature": family, "target": target, "horizon": h, "model": model, "fold": fold, "difference": number(delta)} for d, issuer, delta in zip(v.date, v.issuer, lb - la))
                            if c.get("event_validation_scores"):
                                flag = v[[f for f in meta["features"] if f.startswith("event__")]].sum(axis=1) > 0
                                er = {**r, "feature": family + "__event_rows", "rows": int(flag.sum()),
                                      "positive_issuers": int(v.loc[flag, "issuer"].nunique()),
                                      "inference": "Paired chronological errors on labeled event rows; retrospective vendor clock, no trading claim"}
                                if er["rows"] < c["min_positive"] or er["positive_issuers"] < c["min_issuers"]:
                                    er.update(status="inconclusive", reason="Insufficient event validation support", baseline_mse=None,
                                              augmented_mse=None, paired_mse_improvement=None, relative_mse_improvement=None)
                                else:
                                    eb, ea = lb[flag.to_numpy()], la[flag.to_numpy()]
                                    er.update(baseline_mse=number(eb.mean()), augmented_mse=number(ea.mean()),
                                              paired_mse_improvement=number((eb - ea).mean()),
                                              relative_mse_improvement=number((eb.mean() - ea.mean()) / eb.mean()) if eb.mean() else None)
                                    loss_records.extend({"date": d, "issuer": issuer, "feature": er["feature"], "target": target,
                                                         "horizon": h, "model": model, "fold": fold, "difference": number(delta)}
                                                        for d, issuer, delta in zip(v.loc[flag].date, v.loc[flag].issuer, (lb - la)[flag.to_numpy()]))
                                rows.append(er)
                        rows.append(r)
    return rows, {"paired_losses": loss_records}


def candidate_split_possible(values, min_leaf):
    """Test training-only support for any threshold on a candidate column."""
    _, counts = np.unique(values, return_counts=True)
    cumulative = np.cumsum(counts)[:-1]
    return bool(np.any((cumulative >= min_leaf) & (len(values) - cumulative >= min_leaf)))


if __name__ == "__main__":
    import sys
    from discovery.cli import main
    raise SystemExit(main(["study", "--id", "H08", *sys.argv[1:]]))
