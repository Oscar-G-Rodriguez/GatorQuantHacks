"""Chronological paired forecast comparisons and dependence-aware exploratory inference."""
from __future__ import annotations

import time
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

from .atlas_features import CONTROLS, TextFeatures, eligible_columns, feature_matrix, pattern_catalog,fitting_catalog
from .io import identity


def support(panel, active, mask):
    a = panel.loc[mask & active, ["issuer", "date"]].drop_duplicates()
    return {"activations": len(a), "issuers": a.issuer.nunique(), "dates": a.date.nunique()}


def outer_masks(panel, horizon, year, target):
    start, end = pd.Timestamp(year=year, month=1, day=1), pd.Timestamp(year=year+1, month=1, day=1)
    ready = panel[CONTROLS].notna().all(axis=1) & panel[target].notna()
    train = ready & (panel.date < start) & (panel[f"target_end_{horizon}"] < start)
    test = ready & panel.date.between(start, end, inclusive="left")
    return train.to_numpy(), test.to_numpy()


def inner_masks(panel, train, horizon, fraction=.2):
    dates = np.sort(panel.loc[train, "date"].unique())
    if len(dates) < 60: return np.zeros(len(panel), bool), np.zeros(len(panel), bool)
    boundary = pd.Timestamp(dates[int(len(dates)*(1-fraction))])
    return (train & (panel.date < boundary).to_numpy() & (panel[f"target_end_{horizon}"] < boundary).to_numpy(),
            train & (panel.date >= boundary).to_numpy())


def candidates(config):
    return [{"model":"ridge", "alpha":a} for a in config["ridge_alphas"]] + [{"model":"boosting", "depth":d} for d in config["boosting_depths"]]


def estimator(spec, config):
    if spec["model"] == "ridge":
        return make_pipeline(SimpleImputer(strategy="constant", fill_value=0, keep_empty_features=True), StandardScaler(), Ridge(alpha=spec["alpha"]))
    return make_pipeline(SimpleImputer(strategy="constant", fill_value=0, keep_empty_features=True),
                         HistGradientBoostingRegressor(max_depth=spec["depth"], max_iter=config["boosting_iterations"],
                         learning_rate=config["boosting_learning_rate"], random_state=config["seed"], early_stopping=False))


def group_inputs(panel, patterns, contexts, documents, catalog, mask, group, config, option_values=None):
    base = panel[CONTROLS].to_numpy(dtype=float)
    columns = eligible_columns(patterns, panel, mask, config)
    tags = [j for j in columns if catalog[j]["family"] == "tag"]
    parts = [base]; details = {"eligible_patterns": len(columns), "eligible_labels": len(tags), "text_rank": 0}
    if group.startswith("option"):
        if option_values is None: raise ValueError("No option input panel")
        parts.append(option_values)
    if group in ("labels", "patterns", "text", "option_labels", "option_patterns", "option_text"):
        parts.append(patterns[:, tags].toarray())
    if group in ("patterns", "option_patterns"):
        extra = [j for j in columns if catalog[j]["family"] != "tag"]
        parts.extend([patterns[:, extra].toarray(), np.nan_to_num(contexts), np.isnan(contexts).astype(float)])
        # Event interactions use prior market states, centered/scaled only by the estimator.
        for name in ("return20", "vol20", "volume_state"):
            parts.append(patterns[:, tags].toarray()*panel[name].to_numpy()[:,None])
    if group in ("text", "option_text"):
        fitted = TextFeatures(config).fit(documents[mask]); parts.append(fitted.transform(documents)); details["text_rank"] = fitted.rank
    return np.column_stack(parts), details


def fit_group(panel, y, patterns, contexts, documents, catalog, train, test, group, config, horizon, option_values=None):
    inner_train, inner_test = inner_masks(panel, train, horizon, config["inner_validation_fraction"])
    if inner_train.sum() < 60 or inner_test.sum() < 20: return None, [], "Insufficient purged inner training/validation"
    x, inner_details = group_inputs(panel, patterns, contexts, documents, catalog, inner_train, group, config, option_values)
    trials = []; best, best_loss = None, np.inf
    for spec in candidates(config):
        start = time.perf_counter()
        trial = {**spec, "group": group, "inner_train_rows": int(inner_train.sum()), "inner_test_rows": int(inner_test.sum()), **inner_details}
        try:
            with threadpool_limits(limits=1):
                model = estimator(spec, config); model.fit(x[inner_train], y[inner_train], **{model.steps[-1][0]+"__sample_weight":panel.weight.to_numpy()[inner_train]})
                pred = model.predict(x[inner_test])
            loss = float(np.average((y[inner_test]-pred)**2, weights=panel.weight.to_numpy()[inner_test]))
            trial.update(status="measured", inner_mse=loss)
            if loss < best_loss - 1e-12: best, best_loss = spec, loss
        except Exception as error: trial.update(status="failed", reason=type(error).__name__ + ": " + str(error))
        trial["seconds"] = time.perf_counter()-start; trials.append(trial)
    if best is None: return None, trials, "All declared settings failed"
    x, outer_details = group_inputs(panel, patterns, contexts, documents, catalog, train, group, config, option_values)
    with threadpool_limits(limits=1):
        model = estimator(best, config); model.fit(x[train], y[train], **{model.steps[-1][0]+"__sample_weight":panel.weight.to_numpy()[train]})
        prediction = model.predict(x[test])
    return {"prediction": prediction, "selected": best, "inner_mse": best_loss, **outer_details}, trials, None


def forecast_cell(panel, filings, config, horizon, lag, kind, catalog=None, option_values=None, checkpoint=None):
    catalog = catalog or fitting_catalog(pattern_catalog(filings, config),config)
    patterns, contexts, documents, active = feature_matrix(panel, filings, catalog, config, lag)
    target = f"{kind}_{horizon}"; y = panel[target].to_numpy(); weights = panel.weight.to_numpy()
    all_trials, comparisons, losses = [], [], []
    groups = ["market", "labels", "patterns", "text"]
    if option_values is not None: groups += ["option", "option_labels", "option_patterns", "option_text"]
    for year in config["fold_years"]:
        train, test = outer_masks(panel, horizon, year, target)
        common = np.ones(len(panel), bool) if option_values is None else np.isfinite(option_values).all(axis=1)
        fitted = {}
        for group in groups:
            group_train, group_test = train.copy(), test.copy()
            if group.startswith("option"): group_train &= common; group_test &= common
            tr, va = support(panel, active, group_train), support(panel, active, group_test)
            row = {"comparison_id": identity({"year":year,"horizon":horizon,"lag":lag,"kind":kind,"group":group}),
                   "year":year,"horizon":horizon,"lag":lag,"kind":kind,"group":group,"train_rows":int(group_train.sum()),
                   "validation_rows":int(group_test.sum()),"train_activations":tr["activations"],"train_issuers":tr["issuers"],
                   "validation_activations":va["activations"],"validation_issuers":va["issuers"]}
            if tr["activations"] < config["train_min_activations"] or tr["issuers"] < config["train_min_issuers"] or va["activations"] < config["validation_min_activations"] or va["issuers"] < config["validation_min_issuers"]:
                comparisons.append({**row,"status":"unsupported","reason":"Insufficient independent train/validation activation support"}); continue
            result, trial, error = fit_group(panel,y,patterns,contexts,documents,catalog,group_train,group_test,group,config,horizon,option_values)
            for t in trial: all_trials.append({**row, **t, "stage":"inner_selection"})
            if error:
                comparisons.append({**row,"status":"unsupported","reason":error});continue
            indices = np.flatnonzero(group_test); prediction = result.pop("prediction")
            fitted[group] = (indices,prediction)
            baseline = "option" if group.startswith("option") else "market"
            mse = float(np.average((y[indices]-prediction)**2,weights=weights[indices]))
            summary = {**row, **result,"status":"measured","mse":mse,"baseline":baseline}
            if group != baseline and baseline in fitted:
                bi, bp = fitted[baseline]
                if not np.array_equal(bi,indices): raise ValueError("Paired prediction cohort differs")
                difference = (y[indices]-bp)**2 - (y[indices]-prediction)**2
                base_loss = float(np.average((y[indices]-bp)**2,weights=weights[indices]))
                summary["mse_improvement"] = float(np.average(difference,weights=weights[indices]))
                summary["relative_improvement"] = summary["mse_improvement"]/base_loss if base_loss>0 else None
                event = active[indices]
                summary["event_improvement"] = float(np.average(difference[event],weights=weights[indices][event])) if event.any() else None
                losses.append({"comparison_id":row["comparison_id"],"rows":indices,"values":difference})
                # Activated-category readings of the exact same frozen baseline and augmentation.
                for column, entry in enumerate(catalog):
                    activated = patterns[indices,column].toarray().ravel()>0
                    flag = patterns[:,column].toarray().ravel()>0
                    s, ts = support(panel, flag, group_test), support(panel, flag, group_train)
                    reason = s["activations"] < config["validation_min_activations"] or s["issuers"] < config["validation_min_issuers"] or ts["activations"] < config["train_min_activations"] or ts["issuers"] < config["train_min_issuers"]
                    pattern_id=identity({"parent":row["comparison_id"],"pattern":entry["name"]})
                    comparisons.append({**row,"comparison_id":pattern_id,
                        "pattern":entry["name"],"family":entry["family"],"status":"unsupported" if reason else "measured",
                        "reason":"Insufficient distinct issuer-date training/validation support" if reason else None,
                        "train_activations":ts["activations"],"train_issuers":ts["issuers"],
                        "validation_activations":s["activations"],"validation_issuers":s["issuers"],
                        "event_improvement":None if reason else float(np.average(difference[activated],weights=weights[indices][activated]))})
                    if not reason: losses.append({"comparison_id":pattern_id,"rows":indices[activated],"values":difference[activated]})
            comparisons.append(summary)
        for augmented,baseline in [("patterns","labels"),("text","labels"),("option_patterns","option_labels"),("option_text","option_labels")]:
            if augmented not in fitted or baseline not in fitted:continue
            ix,pred=fitted[augmented];bi,bp=fitted[baseline]
            if not np.array_equal(ix,bi):raise ValueError("Ablation cohorts differ")
            difference=(y[ix]-bp)**2-(y[ix]-pred)**2
            key=identity({"year":year,"horizon":horizon,"lag":lag,"kind":kind,"group":augmented,"baseline":baseline})
            comparisons.append({"comparison_id":key,"year":year,"horizon":horizon,"lag":lag,"kind":kind,"group":augmented,"baseline":baseline,
                "status":"measured","mse_improvement":float(np.average(difference,weights=weights[ix])),"validation_rows":len(ix),"comparison_scope":"paired_global_ablation"})
            losses.append({"comparison_id":key,"rows":ix,"values":difference})
        if checkpoint: checkpoint(year,comparisons,all_trials,losses)
    return comparisons, all_trials, losses


def joint_weights(issuers, session_ids, block_length, rng):
    unique = np.unique(issuers); sampled = rng.choice(unique,len(unique),replace=True)
    issuer_counts = {name:int((sampled==name).sum()) for name in unique}
    size = int(np.max(session_ids))+1; counts = np.zeros(size)
    # Same calendar block draw for every issuer preserves common market shocks.
    starts = rng.integers(0,max(1,size-block_length+1),size=int(np.ceil(size/block_length)))
    seq = np.concatenate([np.arange(start,min(start+block_length,size)) for start in starts])[:size]
    np.add.at(counts,seq,1)
    return np.array([issuer_counts[x] for x in issuers])*counts[session_ids]


def romano_wolf(observed, centered_draws):
    """Stepdown null maxima use centered studentized perturbations, never raw tails."""
    observed = np.asarray(observed); draws = np.asarray(centered_draws)
    order = np.argsort(-np.abs(observed)); adjusted = np.ones(len(observed)); previous = 0.
    raw=np.ones(len(observed));maximum=np.zeros(len(draws))
    for column in order[::-1]:
        maximum=np.maximum(maximum,np.abs(draws[:,column]))
        raw[column]=(1+np.sum(maximum>=abs(observed[column])))/(1+len(maximum))
    for column in order:
        previous=max(previous,float(raw[column]));adjusted[column]=previous
    return adjusted


def resample_losses(frame, samples, block_length, seed):
    columns = sorted(frame.comparison_id.unique()); issuers = frame.issuer.to_numpy(); session = frame.session.to_numpy(dtype=int)
    ids = {name:i for i,name in enumerate(columns)}; index=np.array([ids[x] for x in frame.comparison_id])
    value=frame.value.to_numpy(); weight=frame.weight.to_numpy(); n=len(columns)
    denominator=np.bincount(index,weights=weight,minlength=n)
    point=np.bincount(index,weights=weight*value,minlength=n)/denominator
    draws=np.full((samples,n),np.nan);rng=np.random.default_rng(seed)
    for b in range(samples):
        w=weight*joint_weights(issuers,session,block_length,rng);total=np.bincount(index,weights=w,minlength=n)
        draws[b]=np.divide(np.bincount(index,weights=w*value,minlength=n),total,out=np.full(n,np.nan),where=total>0)
    return columns, point, draws
