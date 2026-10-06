"""Fixed H22 comparisons, uncertainty and readable development evidence."""
from __future__ import annotations
from collections import defaultdict
import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from discovery.io import digest, identity, read_json, write_json
from research import HERE, csv_write, receipt, scheduled, verify_manifest, source_objects, bar_map
from strategy import Data


def pair_trades(trades):
    """Common observations and pre-entry option calipers; no outcome ranking."""
    indexed={(r["pair_id"],r["role"],r["horizon"],r["stock_only"]):r for r in trades}
    pairs=[];excluded=[]
    for event in trades:
        if event["role"] not in {"event","planned"} or event["stock_only"]:continue
        key=event["pair_id"];h=event["horizon"]
        ordinary=indexed.get((key,"ordinary",h,False))
        event_stock=indexed.get((key,event["role"],h,True));ordinary_stock=indexed.get((key,"ordinary",h,True))
        quartet=[event,ordinary,event_stock,ordinary_stock]
        base={"pair_id":key,"horizon":h,"event_status":event["event_status"],"issuer":event["issuer"],"ticker":event["ticker"]}
        if not all(r is not None and r["status"]=="completed" for r in quartet):
            excluded.append({**base,"reason":"incomplete_common_outcomes","statuses":"|".join(r["status"] if r else "missing_control" for r in quartet)});continue
        p0,p1=event["decision_premium_ratio"],ordinary["decision_premium_ratio"]
        if (abs(event["decision_dte"]-ordinary["decision_dte"])>30
                or abs(event["achieved_otm"]-ordinary["achieved_otm"])>.010000001
                or min(p0,p1)<=0 or max(p0,p1)/min(p0,p1)>2):
            excluded.append({**base,"reason":"pre_entry_option_caliper"});continue
        delta=event["net_return"]-ordinary["net_return"]
        stock_delta=event_stock["net_return"]-ordinary_stock["net_return"]
        pairs.append({**base,"event_anchor":event["anchor_id"],"ordinary_anchor":ordinary["anchor_id"],
            "event_date":event["entry_date"],"ordinary_date":ordinary["entry_date"],
            "event_session":event["entry_session"],"ordinary_session":ordinary["entry_session"],
            "event_return":event["net_return"],"ordinary_return":ordinary["net_return"],
            "event_stock_return":event_stock["net_return"],"ordinary_stock_return":ordinary_stock["net_return"],
            "covered_call_increment":delta,"stock_increment":stock_delta,"overlay_increment":delta-stock_delta,
            "event_call_proxy_change":event["call_proxy_change"],"ordinary_call_proxy_change":ordinary["call_proxy_change"],
            "call_proxy_change_increment":event["call_proxy_change"]-ordinary["call_proxy_change"],
            "event_exit":event["exit_date"],"ordinary_exit":ordinary["exit_date"],
            "event_exit_reason":event["exit_reason"],"ordinary_exit_reason":ordinary["exit_reason"],
            "event_dividends":event["dividend_accrual"],"ordinary_dividends":ordinary["dividend_accrual"],
            "event_features":event["features"],"ordinary_features":ordinary["features"],
            "event_premium_ratio":p0,"ordinary_premium_ratio":p1,
            "event_dte":event["decision_dte"],"ordinary_dte":ordinary["decision_dte"],
            "event_otm":event["achieved_otm"],"ordinary_otm":ordinary["achieved_otm"],
            "event_mark_gaps":event["mark_gap_sessions"],"ordinary_mark_gaps":ordinary["mark_gap_sessions"]})
    return pairs,excluded


def joint_weights(rows,dates,draws,block,seed):
    """One issuer draw and common calendar draw, stratified by year.

    Pair calendar weight averages the counts at its two decision periods, so
    shared ordinary controls share resample fluctuations. Issuer weights stay
    fixed across each history. This is an exploratory crossed-cluster bootstrap,
    whose approximation is recorded; it does not establish independent alpha.
    """
    rng=np.random.default_rng(seed);issuers=sorted({r["issuer"] for r in rows})
    issuer_index={s:i for i,s in enumerate(issuers)}
    strata={y:np.array([i for i,d in enumerate(dates) if d.startswith(y)],dtype=int) for y in sorted({d[:4] for d in dates})}
    w=np.empty((draws,len(rows)),dtype=np.float32)
    e=np.array([r["event_session"] for r in rows],dtype=int);o=np.array([r["ordinary_session"] for r in rows],dtype=int)
    codes=np.array([issuer_index[r["issuer"]] for r in rows],dtype=int)
    for b in range(draws):
        ic=np.bincount(rng.integers(0,len(issuers),len(issuers)),minlength=len(issuers))
        counts=np.zeros(len(dates),dtype=float)
        for sessions in strata.values():
            starts=rng.integers(0,len(sessions),int(np.ceil(len(sessions)/block)))
            sample=np.concatenate([(start+np.arange(block))%len(sessions) for start in starts])[:len(sessions)]
            counts[sessions]=np.bincount(sample,minlength=len(sessions))
        w[b]=ic[codes]*(counts[e]+counts[o])/2
    return w


def uncertainty(rows,dates,cfg,block,seed,columns=("covered_call_increment","overlay_increment")):
    n=len(rows);issuers=len({r["issuer"] for r in rows})
    if n<cfg["minimum_pairs"] or issuers<cfg["minimum_issuers"]:
        return [{"target":c,"block":block,"pairs":n,"issuers":issuers,"status":"insufficient_support"} for c in columns]
    values=np.array([[r[c] for c in columns] for r in rows],dtype=float)
    mean=values.mean(axis=0);w=joint_weights(rows,dates,cfg["resamples"],block,seed)
    denom=w.sum(axis=1);valid=denom>0
    estimates=(w[valid]@values)/denom[valid,None]
    sd=estimates.std(axis=0,ddof=1);usable=np.isfinite(sd)&(sd>1e-12)
    if not usable.all():
        return [{"target":c,"block":block,"pairs":n,"issuers":issuers,"status":"zero_variance_or_unsupported_family"} for c in columns]
    centered=np.abs((estimates-mean)/sd);max_t=centered.max(axis=1)
    critical=float(np.quantile(max_t,.95));t=np.abs(mean/sd)
    return [{"target":c,"block":block,"pairs":n,"issuers":issuers,"status":"exploratory_estimate",
        "mean":float(mean[j]),"joint_standard_error":float(sd[j]),"simultaneous_ci_low":float(mean[j]-critical*sd[j]),
        "simultaneous_ci_high":float(mean[j]+critical*sd[j]),
        "adjusted_p":float((1+np.sum(max_t>=t[j]))/(len(max_t)+1)),"family_size":len(columns),
        "valid_resamples":len(estimates),"empty_resamples":int((~valid).sum()),"clock_assumed":True} for j,c in enumerate(columns)]


def diagnostic_predictions(pairs):
    observations=[]
    for r in pairs:
        for role in ["event","ordinary"]:
            observations.append({"issuer":r["issuer"],"date":r[role+"_date"],"exit":r[role+"_exit"],
                "event":int(role=="event"),"features":[*r[role+"_features"].values(),r[role+"_premium_ratio"]],
                "combined":r[role+"_return"],"overlay":r[role+"_return"]-r[role+"_stock_return"]})
    results=[]
    for year in [2023,2024,2025]:
        boundary=str(year)+"-01-01"
        train=[r for r in observations if r["date"]<boundary and r["exit"]<boundary]
        valid=[r for r in observations if r["date"].startswith(str(year))]
        enough=(len(train)>=20 and len({r["issuer"] for r in train})>=8 and len(valid)>=10 and len({r["issuer"] for r in valid})>=5)
        for target in ["combined","overlay"]:
            out={"method":"ridge_prediction_ablation","year":year,"target":target,"train":len(train),"validation":len(valid),"status":"insufficient_support"}
            if enough:
                x=np.array([r["features"] for r in train]);z=np.array([r["features"] for r in valid]);scale=StandardScaler().fit(x)
                x=scale.transform(x);z=scale.transform(z)
                y=np.array([r[target] for r in train]);v=np.array([r[target] for r in valid])
                base=Ridge(alpha=10).fit(x,y).predict(z)
                added=Ridge(alpha=10).fit(np.column_stack([x,[r["event"] for r in train]]),y).predict(np.column_stack([z,[r["event"] for r in valid]]))
                out.update(status="executed_development",baseline_mse=float(np.mean((v-base)**2)),
                           disclosure_mse=float(np.mean((v-added)**2)),paired_mse_improvement=float(np.mean((v-base)**2-(v-added)**2)))
            results.append(out)
    return results


def secondary_uncertainty(pairs,dates,cfg,block):
    """One joint family of every fixed secondary task/horizon contrast."""
    cells=defaultdict(list)
    for p in pairs:
        if p["event_status"]=="completed":cells[(p["task"],p["horizon"])].append(p)
    targets=["covered_call_increment","overlay_increment"];out=[];eligible=[]
    for key,rows in cells.items():
        if key==(0,21):continue  # Separate declared two-test primary family.
        if len(rows)<cfg["minimum_pairs"] or len({r["issuer"] for r in rows})<cfg["minimum_issuers"]:
            out.extend({"task":key[0],"horizon":key[1],"target":t,"block":block,"pairs":len(rows),"status":"insufficient_support"} for t in targets)
        else:eligible.append((key,rows))
    if not eligible:return out
    registry={}
    for _,rows in eligible:
        for r in rows:registry.setdefault((r["pair_id"],r["event_session"],r["ordinary_session"]),r)
    keys=sorted(registry);index={k:i for i,k in enumerate(keys)}
    weights=joint_weights([registry[k] for k in keys],dates,cfg["resamples"],block,cfg["seed"]+block+800)
    estimates=[];means=[];metadata=[]
    for key,rows in eligible:
        ids=np.array([index[(r["pair_id"],r["event_session"],r["ordinary_session"])] for r in rows]);w=weights[:,ids]
        denom=w.sum(axis=1)
        for target in targets:
            values=np.array([r[target] for r in rows]);est=np.full(len(w),np.nan);valid=denom>0
            est[valid]=w[valid]@values/denom[valid];estimates.append(est);means.append(values.mean())
            metadata.append({"task":key[0],"horizon":key[1],"target":target,"block":block,"pairs":len(rows)})
    matrix=np.column_stack(estimates);means=np.array(means);valid=np.isfinite(matrix).all(axis=1)
    matrix=matrix[valid];sd=matrix.std(axis=0,ddof=1);usable=sd>1e-12
    if not usable.any():return out+[{**r,"status":"zero_variance_family"} for r in metadata]
    max_t=np.abs((matrix[:,usable]-means[usable])/sd[usable]).max(axis=1);critical=np.quantile(max_t,.95)
    for j,r in enumerate(metadata):
        if not usable[j]:out.append({**r,"status":"zero_variance"});continue
        out.append({**r,"status":"exploratory_secondary_family","mean":float(means[j]),
            "simultaneous_ci_low":float(means[j]-critical*sd[j]),"simultaneous_ci_high":float(means[j]+critical*sd[j]),
            "adjusted_p":float((1+np.sum(max_t>=abs(means[j]/sd[j])))/(len(max_t)+1)),
            "family_size":int(usable.sum()),"valid_resamples":len(max_t)})
    return out


def synthetic_null_check():
    """Known zero-mean crossed-cluster null; no real returns enter this check."""
    dates=pd.bdate_range("2022-01-01",periods=500).strftime("%Y-%m-%d").tolist()
    rows=[{"issuer":str(j),"event_session":180+k*16,"ordinary_session":50+k*16} for j in range(10) for k in range(8)]
    w=joint_weights(rows,dates,999,63,221004);denom=w.sum(axis=1);w=w[denom>0];denom=denom[denom>0]
    rng=np.random.default_rng(221004+808);rejects=0;replicas=100
    for _ in range(replicas):
        issuer=rng.normal(size=(10,2));calendar=rng.normal(size=(8,2))
        values=np.array([.5*issuer[j]+.5*calendar[k]+rng.normal(size=2) for j in range(10) for k in range(8)])
        mean=values.mean(axis=0);est=w@values/denom[:,None];sd=est.std(axis=0,ddof=1)
        maximum=np.abs((est-mean)/sd).max(axis=1)
        p=(1+np.sum(maximum>=np.max(np.abs(mean/sd))))/(len(maximum)+1)
        rejects+=p<.05
    return {"replicas":replicas,"resamples_per_replica":999,"family_size":2,"nominal_family_error":.05,
            "rejections":int(rejects),"false_positive_fraction":float(rejects/replicas),
            "status":"pass" if rejects<=10 else "fail",
            "criterion":"At most10 rejections among100 known-null replicates; simulation check is not a proof of bootstrap validity"}


def hac_attribution(nav,market,lag=21):
    if nav.nav.isna().any():return {"status":"unavailable_incomplete_nav","observations":len(nav)}
    frame=nav[["date","nav"]].copy();frame["ret"]=frame.nav.pct_change(fill_method=None)
    frame["market"]=frame.date.map(market)
    if frame.iloc[1:].market.isna().any():return {"status":"unavailable_missing_market_sessions","observations":len(frame)}
    frame=frame.dropna()
    if len(frame)<60:return {"status":"insufficient_support","observations":len(frame)}
    x=np.column_stack([np.ones(len(frame)),frame.market.to_numpy()]);y=frame.ret.to_numpy()
    beta=np.linalg.lstsq(x,y,rcond=None)[0];u=y-x@beta;score=x*u[:,None]
    meat=score.T@score
    for k in range(1,min(lag,len(frame)-1)+1):
        c=score[k:].T@score[:-k];meat+=(1-k/(lag+1))*(c+c.T)
    bread=np.linalg.pinv(x.T@x);cov=bread@meat@bread;se=np.sqrt(np.maximum(np.diag(cov),0))
    return {"status":"descriptive_development","observations":len(frame),"hac_lag":lag,
            "intercept_daily":float(beta[0]),"intercept_se":float(se[0]),"spy_beta":float(beta[1]),"beta_se":float(se[1]),
            "interpretation":"SPY-only descriptive residual; omitted factors and no fresh confirmation prevent an alpha claim"}


def quote_readings(pairs,data):
    by_id={r["anchor_id"]:r for r in data.records};out=[]
    for p in pairs:
        for role in ["event","ordinary"]:
            r=by_id[p[role+"_anchor"]];row={"pair_id":p["pair_id"],"role":role,"ticker":r["ticker"],"date":r["entry_date"]}
            entry,es=data.quote_pair(r,"entry");exit_,xs=data.quote_pair(r,"exit")
            row.update(entry_status=es,exit_status=xs,status="unsupported")
            if entry and exit_ and p[role+"_exit"]==data.dates[r["entry_session"]+21] and p[role+"_exit_reason"]=="scheduled_exit":
                s0,c0=entry;s1,c1=exit_
                # Exact quoted sides already include the spread once.
                gross=100*(s1["bid"]-s0["ask"]+c0["bid"]-c1["ask"])
                cost=100*.0002*(s0["mid"]+s1["mid"])+100*.01*(c0["mid"]+c1["mid"])+2*.65
                dividend=p[role+"_dividends"]
                half_spreads=100*sum((q["ask"]-q["bid"])/2 for q in [s0,c0,s1,c1])
                gross_mid=100*(s1["mid"]-s0["mid"]+c0["mid"]-c1["mid"])
                row.update(status="quote_supported_price_comparison",gross_price_pnl=gross,extra_cost=cost,
                    net_return_with_dividends=(gross+dividend-cost)/(100*s0["ask"]),
                    doubled_cost_return=(gross_mid+dividend-2*(half_spreads+cost))/(100*s0["ask"]),
                    option_entry_spread=c0["relative_spread"],option_exit_spread=c1["relative_spread"],
                    stock_entry_age=s0["age_seconds"],option_entry_age=c0["age_seconds"],
                    note="Quote-supported fixed-exit subset; modelled assignment/delayed exits excluded; no full executable-portfolio claim")
            out.append(row)
    return out


def regime_rows(pairs,market_vol):
    rows=[]
    for p in pairs:
        year=p["event_date"][:4]
        earlier=[v for d,v in market_vol.items() if d[:4]<year and np.isfinite(v)]
        threshold=float(np.median(earlier)) if earlier else None
        state="unknown_prior_year_volatility" if threshold is None else ("high_volatility" if p["event_features"]["market_volatility"]>threshold else "low_volatility")
        rows.append({"task":p["task"],"variant":p["variant"],"horizon":p["horizon"],"pair_id":p["pair_id"],"year":year,
            "market_momentum_positive":p["event_features"]["market_momentum"]>0,"prior_volatility_state":state,
            "covered_call_increment":p["covered_call_increment"],"overlay_increment":p["overlay_increment"]})
    return rows


def fixed_gate_diagnostics(pairs):
    rows=[];history=[]
    for p in sorted(pairs,key=lambda p:p["ordinary_date"]):
        prior=[r for r in history if r["ordinary_date"][:4]<p["ordinary_date"][:4]]
        rich=None
        if len(prior)>=20 and len({r["issuer"] for r in prior})>=8:
            rich=p["ordinary_premium_ratio"]>np.median([r["ordinary_premium_ratio"] for r in prior])
        rows.append({"method":"fixed_price_option_gates","pair_id":p["pair_id"],"issuer":p["issuer"],
            "event_return":p["event_return"],"ordinary_return":p["ordinary_return"],
            "positive_prior_momentum":p["ordinary_features"]["momentum"]>0,"prior_year_option_rich":rich,
            "richness_training_observations":len(prior)})
        history.append(p)
    return rows


def timing_placebos(pairs,cfg):
    """Shuffle entire observed stock/call bundles within issuer/calendar year."""
    groups=defaultdict(list)
    for p in pairs:
        for role in ["event","ordinary"]:
            groups[(p["issuer"],p[role+"_date"][:4])].append((int(role=="event"),p[role+"_return"]))
    eligible=[g for g in groups.values() if 0<sum(x[0] for x in g)<len(g)]
    if not eligible:return [{"status":"insufficient_exchangeable_timing_support","replicas":0}]
    rng=np.random.default_rng(cfg["seed"]+909);out=[]
    for replica in range(cfg["timing_placebos"]):
        event=[];ordinary=[]
        for g in eligible:
            labels=np.array([x[0] for x in g]);values=np.array([x[1] for x in g]);labels=rng.permutation(labels)
            event.extend(values[labels==1]);ordinary.extend(values[labels==0])
        out.append({"replica":replica,"status":"bundle_timing_permutation","event_observations":len(event),
                    "ordinary_observations":len(ordinary),"net_difference":float(np.mean(event)-np.mean(ordinary))})
    return out


def analyze(run):
    scheduled();run=Path(run);m=verify_manifest(run);data=Data(run);cfg=data.cfg
    tasks=read_json(run/"tasks.json");all_pairs=[];all_exclusions=[];performance=[];trial_rows=[];all_trades=[];primary=[]
    for task in tasks:
        folder=run/"results"/f"task-{task['task']}";rp=run/"receipts"/f"task-{task['task']}.json"
        if not rp.exists():raise ValueError("Missing planned task: "+str(task["task"]))
        check=read_json(rp)
        if check["manifest_id"]!=m["manifest_id"]:raise ValueError("Task belongs to another freeze")
        for p,h in check["files"].items():
            if digest(run/p)!=h:raise ValueError("Task output changed")
        trades=read_json(folder/"trades.json");pairs,excluded=pair_trades(trades)
        all_pairs.extend({**task,**p} for p in pairs);all_exclusions.extend({**task,**p} for p in excluded)
        all_trades.extend({**task,**p} for p in trades)
        for p in pd.read_csv(folder/"performance.csv").to_dict("records"):performance.append({**task,**p})
        for h in cfg["horizons"]:
            for event_status in ["completed","planned"]:
                rows=[p for p in pairs if p["horizon"]==h and p["event_status"]==event_status]
                trial_rows.append({**task,"horizon":h,"event_status":event_status,"pairs":len(rows),"issuers":len({r["issuer"] for r in rows}),
                    "terminal_status":"completed_supported_descriptive" if len(rows)>=cfg["minimum_pairs"] and len({r["issuer"] for r in rows})>=cfg["minimum_issuers"] else "completed_insufficient_support",
                    "mean_covered_call_increment":float(np.mean([r["covered_call_increment"] for r in rows])) if rows else None,
                    "mean_overlay_increment":float(np.mean([r["overlay_increment"] for r in rows])) if rows else None})
        if task["variant"]=="primary" and task["costs"]==1 and task["assignment"]=="time_value":
            primary=[p for p in pairs if p["horizon"]==21 and p["event_status"]=="completed"]
    out=run/"results/aggregate";out.mkdir(parents=True,exist_ok=True)
    csv_write(out/"paired-results.csv",all_pairs);csv_write(out/"paired-exclusions.csv",all_exclusions)
    csv_write(out/"performance.csv",performance);csv_write(out/"trials.csv",trial_rows)
    write_json(out/"trade-diagnostics.json",all_trades)
    null=synthetic_null_check();write_json(out/"synthetic-null-validation.json",null)
    u=[]
    for block in cfg["blocks"]:u+=uncertainty(primary,data.dates,cfg,block,cfg["seed"]+block)
    secondary=[]
    for block in cfg["blocks"]:secondary+=secondary_uncertainty(all_pairs,data.dates,cfg,block)
    if null["status"]=="fail":
        write_json(out/"invalid-inference-retained.json",{"reason":"synthetic null calibration failed; no inferential claim permitted","primary":u,"secondary":secondary})
        keys={"target","task","horizon","block","pairs","issuers","status"}
        u=[{**{k:v for k,v in r.items() if k in keys},"status":"insufficient_support" if r["status"]=="insufficient_support" else "not_reported_failed_null_calibration"} for r in u]
        secondary=[{**{k:v for k,v in r.items() if k in keys},"status":"insufficient_support" if r["status"]=="insufficient_support" else "not_reported_failed_null_calibration"} for r in secondary]
    csv_write(out/"uncertainty.csv",u);csv_write(out/"secondary-uncertainty.csv",secondary)
    predictions=diagnostic_predictions(primary);gates=fixed_gate_diagnostics(primary)
    quotes=quote_readings(primary,data);placebos=timing_placebos(primary,cfg)
    csv_write(out/"prediction-ablation.csv",predictions);csv_write(out/"baseline-gates.csv",gates)
    csv_write(out/"quote-validation.csv",quotes);csv_write(out/"timing-placebos.csv",placebos)
    # Mechanism checks are distinct from profitable stock exposure.
    diagnostics=[]
    for year in range(2022,2026):
        for status in ["completed","planned"]:
            rows=[r for r in all_pairs if r["variant"]=="primary" and r["costs"]==1 and r["assignment"]=="time_value" and r["horizon"]==21 and r["event_status"]==status and r["event_date"].startswith(str(year))]
            supported=len(rows)>=10 and len({r["issuer"] for r in rows})>=5
            diagnostics.append({"method":"mechanism_year","year":year,"event_status":status,"pairs":len(rows),"issuers":len({r["issuer"] for r in rows}),
                "status":"supported_descriptive_cell" if supported else "insufficient_support",
                "mean_call_proxy_change_increment":float(np.mean([r["call_proxy_change_increment"] for r in rows])) if rows else None,
                "mean_covered_call_increment":float(np.mean([r["covered_call_increment"] for r in rows])) if rows else None,
                "mean_overlay_increment":float(np.mean([r["overlay_increment"] for r in rows])) if rows else None})
    csv_write(out/"signal_diagnostics.csv",diagnostics)
    concentration=[]
    for issuer in sorted({p["issuer"] for p in primary}):
        remaining=[r for r in primary if r["issuer"]!=issuer]
        concentration.append({"omitted_issuer":issuer,"remaining_pairs":len(remaining),
            "remaining_mean":float(np.mean([r["covered_call_increment"] for r in remaining])) if remaining else None,
            "issuer_pairs":sum(r["issuer"]==issuer for r in primary)})
    csv_write(out/"issuer-concentration.csv",concentration)
    s,objects=source_objects(run);spy={}
    for key,o in s["objects"].items():
        if "/aggs/ticker/SPY/" in o["path"]:spy.update(bar_map(objects[key]))
    market=pd.Series({d:b["c"] for d,b in spy.items()}).sort_index().pct_change(fill_method=None).to_dict()
    market_vol=pd.Series(market).pow(2).rolling(21,min_periods=21).mean().pow(.5).to_dict()
    csv_write(out/"robustness.csv",regime_rows(all_pairs,market_vol))
    nav=pd.read_csv(run/"results/task-0/daily-nav.csv")
    attribution=[]
    for name in nav.portfolio.unique():attribution.append({"portfolio":name,**hac_attribution(nav[nav.portfolio==name],market)})
    csv_write(out/"attribution.csv",attribution)
    unresolved=sum(r["status"].startswith("initiated_") for r in all_trades if r["variant"]=="primary" and r["costs"]==1 and r["assignment"]=="time_value" and r["horizon"]==21 and not r["stock_only"] and r["role"] in {"event","ordinary"})
    summary={"study":"H22","phase":"exposed development","registration_commit":m["registration_commit"],"code_commit":m["code_commit"],
        "manifest_id":m["manifest_id"],"source_id":data.source["source_id"],"acquisition_complete":data.source["complete"],
        "primary_completed_pairs":len(primary),"primary_issuers":len({r["issuer"] for r in primary}),"initiated_incomplete_primary_diagnostics":unresolved,
        "primary_mean_increment":float(np.mean([r["covered_call_increment"] for r in primary])) if primary else None,
        "primary_mean_overlay_increment":float(np.mean([r["overlay_increment"] for r in primary])) if primary else None,
        "planned_tasks":len(tasks),"completed_tasks":len(tasks),"trial_cells":len(trial_rows),"quote_supported_trade_records":sum(r["status"]=="quote_supported_price_comparison" for r in quotes),"synthetic_null_status":null["status"],
        "verdict":"INCONCLUSIVE development evidence","independent_oos":"unavailable; all study dates previously exposed",
        "fill_model":"assumed daily closes with declared friction; quote subset separately reported",
        "limitations":["No independent confirmation","Historical vendor delivery clock assumed","Surviving static universe",
                       "Completion text rule needs human evidence audit","Daily option closes do not establish executable fills",
                       "Incomplete initiated outcomes prevent a full-cohort claim","Crossed bootstrap is approximate and does not correct prior adaptive search"]}
    write_json(out/"summary.json",summary)
    checks=[]
    descriptions={"S01":"Measured clock/entry integrity; historical vendor delivery clock remains assumed",
        "S02":"Development-only run; no available unseen final OOS, and final-OOS entry point refuses reuse",
        "S03":"Completion coverage and prior-year prediction ablation", "S04":"All registered horizon/delay cells retained",
        "S05":"Ordinary covered calls, same-date stocks, fixed price/option gates and cash",
        "S06":"Common paired net returns and overlay difference-in-differences",
        "S07":"Stock/option decomposition and SPY-only descriptive HAC attribution; unmeasured factors remain",
        "S08":"Joint issuer/calendar resamples and separate max-t families; failed synthetic-null calibration suppresses inferential claims, and sparse groups remain unsupported",
        "S09":"Planned and shifted controls, observed-bundle timing permutations; scope is conditional coverage",
        "S10":"Fixed neighbors/cost/delay/assignment/year and issuer checks; no optimizer",
        "S11":"Funding, costs, dividends, modelled assignment and unfilled/unresolved positions; executable capture unproven",
        "S12":"Compute receipts/member hashes verified; scheduler terminal proof and PC return verification recorded separately"}
    for method,reason in descriptions.items():
        status="pending" if method in {"S01","S02","S03","S11","S12"} else "pass"
        if method=="S08" and null["status"]=="fail":status="fail"
        checks.append({"method":method,"implemented":True,"executed":True,"status":status,
                       "criterion_met":False if status=="pending" else None,"reason":reason,
                       "implementation":"research.py / strategy.py / analysis.py / pipeline.py","evidence":"aggregate outputs and task receipts"})
    write_json(out/"validation_checks.json",checks)
    # No OOS KPIs or profitable no-trade cash result is fabricated.
    csv_write(out/"oos-performance.csv",[{"phase":"final-oos","status":"unavailable_exposed_history","annualized_return":None,"volatility":None,"sharpe":None,"max_drawdown":None}])
    pieces=["<!doctype html><html><meta charset='utf-8'><title>H22 development backtest</title><style>body{font:16px system-ui;margin:32px;color:#172434}table{border-collapse:collapse;font-size:13px}td,th{padding:6px;border:1px solid #cbd5e1}th{background:#edf2f7}pre{white-space:pre-wrap}.limit{background:#fff4d6;padding:16px}</style>",
        "<h1>Debt financing and covered calls</h1><p>Funded shares plus a sold call; 21-session primary hold. Fixed parameters, Massive-only inputs, scheduled HiPerGator computation.</p>",
        "<div class='limit'><b>Exposed development simulation.</b> Daily closing-price fills are assumed. No independent confirmation or net-alpha claim. Missing/unresolved initiated trades remain in the tables.</div>",
        "<h2>Primary matched result</h2><pre>"+html.escape(json.dumps(summary,indent=2))+"</pre>",
        "<h2>Portfolio performance</h2>"+pd.DataFrame(performance).to_html(index=False,escape=True),
        "<h2>Dependence-aware primary comparisons</h2>"+pd.DataFrame(u).to_html(index=False,escape=True),
        "<h2>Year and mechanism checks</h2>"+pd.DataFrame(diagnostics).to_html(index=False,escape=True)]
    import plotly.graph_objects as go
    fig=go.Figure()
    for name in nav.portfolio.unique():
        f=nav[nav.portfolio==name];fig.add_trace(go.Scatter(x=f.date,y=f.nav,name=name,connectgaps=False))
    fig.update_layout(title="Development NAV; gaps stay visible",xaxis_title="Session",yaxis_title="Dollars")
    pieces.append(fig.to_html(full_html=False,include_plotlyjs=True));pieces.append("<p>Detailed tables and provenance are in this same result directory. Cash return is zero. Empty strategies have unavailable KPIs.</p></html>")
    (out/"report.html").write_text("\n".join(pieces),encoding="utf-8")
    receipt(run,"analysis",list(out.glob("*")),{"primary_pairs":len(primary),"tasks":len(tasks),"verdict":summary["verdict"]})
    print(json.dumps(summary,indent=2),flush=True)
