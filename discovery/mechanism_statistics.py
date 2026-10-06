"""Registered inference with clustered resampling and matured chronological fits."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


def cluster_sample(frame, rng, column="issuer"):
    groups = {k: v for k, v in frame.groupby(column, sort=True)}
    keys = list(groups)
    # Concatenation is essential: isin would discard bootstrap multiplicity.
    return pd.concat([groups[keys[i]] for i in rng.integers(0, len(keys), len(keys))], ignore_index=True)


def coefficient(frame, target, features=(), parameter=0):
    x = np.column_stack([np.ones(len(frame))] + [frame[c].to_numpy(float) for c in features])
    if len(frame) < 2*x.shape[1] or np.linalg.matrix_rank(x) != x.shape[1]:
        return None
    # Scaling improves conditioning without changing the requested coefficient.
    scales = np.std(x, axis=0)
    scales[scales == 0] = 1
    xs = x/scales
    if np.linalg.cond(xs) > 1e8:
        return None
    return float((np.linalg.lstsq(xs, frame[target].to_numpy(float), rcond=None)[0]/scales)[parameter])


def infer(frame, target, cfg, features=(), parameter=0, primary=True):
    needed = [target, "issuer"] + list(features)
    f = frame.dropna(subset=needed) if all(c in frame for c in needed) else pd.DataFrame()
    result = {"observations": len(f), "issuers": int(f.issuer.nunique()) if len(f) else 0,
              "status": "inconclusive", "reason": "insufficient_support", "primary": primary}
    minimum = cfg["minimum_primary_events"] if primary else 4
    issuers = cfg["minimum_primary_issuers"] if primary else 3
    if len(f) < minimum or result["issuers"] < issuers:
        return result
    estimate = coefficient(f, target, features, parameter)
    if estimate is None:
        result["reason"] = "rank_condition_or_parameter_support"
        return result
    draws = cfg["primary_bootstrap_draws"] if primary else cfg["secondary_bootstrap_draws"]
    alpha = cfg["family_alpha"]/cfg["primary_family_size"] if primary else .05
    rng = np.random.default_rng(cfg["seed"])
    samples = []
    for _ in range(draws):
        b = coefficient(cluster_sample(f, rng), target, features, parameter)
        if b is not None:
            samples.append(b)
    result.update(estimate=estimate, requested_draws=draws, valid_draws=len(samples),
                  confidence_level=1-alpha)
    if len(samples) < .8*draws:
        result["reason"] = "too_many_unsupported_bootstrap_fits"
        return result
    lo, hi = np.quantile(samples, [alpha/2, 1-alpha/2])
    leave = [coefficient(f.loc[f.issuer != issuer], target, features, parameter) for issuer in sorted(f.issuer.unique())]
    good = [v for v in leave if v is not None]
    equal = f.groupby("issuer")[target].mean().mean()
    result.update(status="measured", reason=None, ci_low=float(lo), ci_high=float(hi),
                  issuer_equal_mean=float(equal), leave_one_min=min(good) if good else None,
                  leave_one_max=max(good) if good else None, unsupported_leave_one=len(leave)-len(good))
    if "filing_session" in f:
        blocks = f.filing_session.astype(int)//cfg["date_block_sessions"]
        block_count = int(blocks.nunique())
        result["date_blocks"] = block_count
        result["date_block_status"] = "inconclusive"
        if block_count >= cfg["minimum_date_blocks"]:
            bf = f.assign(date_block=blocks)
            block_draws = [coefficient(cluster_sample(bf, rng, "date_block"), target, features, parameter)
                           for _ in range(cfg["secondary_bootstrap_draws"])]
            block_draws = [v for v in block_draws if v is not None]
            if len(block_draws) >= .8*cfg["secondary_bootstrap_draws"]:
                blo, bhi = np.quantile(block_draws, [.025, .975])
                result.update(date_block_status="measured", date_block_low=float(blo), date_block_high=float(bhi))
    return result


def pair(frame, columns):
    """One ordinary counterpart per exact event/settings, retaining unmatched rows."""
    keys = ["event_id", "delay", "bucket", "otm"]
    event = frame.loc[frame.cohort == "event"]
    ordinary = frame.loc[frame.cohort == "ordinary"]
    common = event.merge(ordinary, on=keys, suffixes=("_event", "_ordinary"), validate="one_to_one")
    out = common[keys].copy()
    out["issuer"] = common.issuer_event
    out["filing_session"] = common.filing_session_event
    out["filing_date"] = common.filing_date_event
    for c in columns:
        if c in frame:
            out[c] = common[c+"_event"]-common[c+"_ordinary"]
    return out


def chronological(frame, target, baseline, augmented, cfg):
    """Past-only scaling; purge by actual target maturity rather than row distance."""
    rows = []
    folds = [("2024-06-30", "2024-07-01", "2024-12-31"),
             ("2024-12-31", "2025-01-01", "2025-06-30"),
             ("2025-06-30", "2025-07-01", "2025-12-31")]
    needed = list(dict.fromkeys([target, "filing_date", "target_end"] + baseline + augmented))
    f = frame.dropna(subset=needed) if all(c in frame for c in needed) else pd.DataFrame()
    for end, start, stop in folds:
        base = {"train_end": end, "validation_start": start, "validation_end": stop,
                "target": target, "status": "inconclusive"}
        if f.empty:
            rows.append({**base, "reason": "missing_complete_features"}); continue
        train = f.loc[(f.filing_date <= end) & (f.target_end < start)]
        test = f.loc[(f.filing_date >= start) & (f.filing_date <= stop) & (f.target_end <= stop)]
        if len(train) < max(12, 2*(len(augmented)+1)) or len(test) < 4:
            rows.append({**base, "reason": "sparse_matured_fold", "train_rows": len(train), "test_rows": len(test)}); continue
        errors = []
        for cols in [baseline, augmented]:
            scaler = StandardScaler().fit(train[cols])
            model = Ridge(alpha=cfg["ridge_alpha"]).fit(scaler.transform(train[cols]), train[target])
            pred = model.predict(scaler.transform(test[cols]))
            errors.append(float(np.mean((test[target]-pred)**2)))
        rows.append({**base, "status": "measured", "reason": None, "train_rows": len(train), "test_rows": len(test),
                     "last_training_target_end": train.target_end.max(), "baseline_mse": errors[0],
                     "augmented_mse": errors[1], "relative_mse_improvement": 1-errors[1]/errors[0] if errors[0] else None})
    return rows


def train_prediction(frame,target,cfg):
    baseline=["uncertainty","momentum"]
    augmented=baseline+["earnings","guidance","debt"]
    if target=="rms":augmented+=["verified_terms"]
    needed=[target,"target_end","filing_date"]+augmented
    f=frame.dropna(subset=needed)
    f=f.loc[(f.target_end<=cfg["development"]["as_of"])&(f.filing_date<=cfg["development"]["end"])]
    if len(f)<max(12,2*(len(augmented)+1)):
        return {"status":"inconclusive","reason":"insufficient_complete_development_training","train_rows":len(f)}
    models={}
    for name,columns in [("baseline",baseline),("augmented",augmented)]:
        scaler=StandardScaler().fit(f[columns]);model=Ridge(alpha=cfg["ridge_alpha"]).fit(scaler.transform(f[columns]),f[target])
        models[name]={"columns":columns,"mean":scaler.mean_.tolist(),"scale":scaler.scale_.tolist(),
                      "coefficient":model.coef_.tolist(),"intercept":float(model.intercept_)}
    return {"status":"trained","train_rows":len(f),"last_training_target_end":f.target_end.max(),"target":target,"models":models}


def evaluate_prediction(frame,frozen):
    if frozen.get("status")!="trained":return {"status":"inconclusive","reason":"development_model_unavailable"}
    models=frozen["models"];target=frozen["target"]
    needed=list(dict.fromkeys([target]+[c for m in models.values() for c in m["columns"]]))
    f=frame.dropna(subset=needed)
    if len(f)<4:return {"status":"inconclusive","reason":"insufficient_common_final_rows","test_rows":len(f)}
    errors={}
    for name,m in models.items():
        x=(f[m["columns"]].to_numpy(float)-np.array(m["mean"]))/np.array(m["scale"])
        prediction=x@np.array(m["coefficient"])+m["intercept"]
        errors[name]=float(np.mean((f[target].to_numpy(float)-prediction)**2))
    return {"status":"measured","test_rows":len(f),"baseline_mse":errors["baseline"],"augmented_mse":errors["augmented"],
            "relative_mse_improvement":1-errors["augmented"]/errors["baseline"] if errors["baseline"] else None,
            "training_last_target_end":frozen["last_training_target_end"],"transform":"frozen development scaling; no final fitting"}
