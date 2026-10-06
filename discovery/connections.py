"""Frozen H12–H17 connection studies; run scientific tasks on HiPerGator.

Provider preparation and packaging can run locally. All correlations, estimates,
resampling and prediction are called only by the scheduled task entry point.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import load_snapshot
from .io import ROOT, digest, identity, now, read_json, write_json
from .options_data import BUCKETS, BUFFERS, END, HORIZONS, PLAN_COMMITS, START, backward_mark, session_dates

STUDIES = {
    "H12":"H12 - Buffered Disclosure Relationships", "H13":"H13 - Option Implied Uncertainty",
    "H14":"H14 - Disclosure Option Repricing", "H15":"H15 - Maturity and Pricing Quality",
    "H16":"H16 - Disclosure Context and Sequences", "H17":"H17 - Connection Reliability and Prediction"}
GROUPS = {"cfo":["cfo_appointment"], "ceo":["ceo_departure"],
          "earnings":["quarterly_earnings","annual_earnings","preliminary_results"],
          "guidance":["guidance_issuance_or_update","guidance_withdrawal"],
          "compensation":["executive_compensation_change"], "debt":["debt_issuance"]}
CONTROLS = ["past_return_5","past_return_20","past_vol_20","past_log_volume","market_past_return_5"]
OFFSETS = [0,1,3,5]
RESAMPLES = 999


def seed(spec):
    return int(identity(spec)[:16],16) % 2**32


def scalar(value):
    return float(value) if np.isfinite(value) else None


def shifted(frame, columns, buffer, sessions):
    """Join actual calendar-session offsets; missing rows never compress time."""
    old=frame[["ticker","date"]+columns].copy()
    lookup={d:i for i,d in enumerate(sessions)}
    destination={d:sessions[i+buffer] for d,i in lookup.items() if i+buffer<len(sessions)}
    old["date"]=old.date.map(destination)
    # Several final sessions can shift beyond END. Drop those source join keys;
    # retaining repeated NaNs violates one-to-one validation without adding data.
    old=old.dropna(subset=["date"])
    return frame.drop(columns=columns).merge(old,on=["ticker","date"],how="left",validate="one_to_one")


def dense_prepare(snapshot_path, context_path, output):
    """Normalize existing covered context and recency without any scientific fit."""
    panel,meta,config=load_snapshot(snapshot_path)
    context_path,output=Path(context_path),Path(output)
    report=read_json(context_path/"download-report.json")
    if not report["complete"]:
        raise ValueError("Context acquisition is incomplete")
    source=[]
    for obj in report["objects"]:
        p=context_path/obj["file"]
        if digest(p)!=obj["sha256"]:
            raise ValueError("Context source changed")
        source+=read_json(p)
    sessions=session_dates()
    dates=np.array(sessions)
    known={str(r["cik"]).zfill(10) for r in source}
    panel.issuer=panel.issuer.astype(str).str.zfill(10)
    filings={}
    for r in source:
        key=(str(r["cik"]).zfill(10),r["accession_number"])
        f=filings.setdefault(key,{"date":r["filing_date"],"categories":set()})
        if f["date"]!=r["filing_date"]:
            raise ValueError("Filing date conflict")
        f["categories"].add(r["tertiary_category"])
    counts={}
    for (issuer,accession),f in filings.items():
        available=(pd.Timestamp(f["date"])+pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        i=int(dates.searchsorted(available))
        if i>=len(dates):
            continue
        for group,cats in GROUPS.items():
            if f["categories"] & set(cats):
                counts.setdefault((issuer,group),np.zeros(len(dates)))[i]=1.
    for group in GROUPS:
        values={(issuer,d):counts.get((issuer,group),np.zeros(len(dates)))[i] for issuer in known for i,d in enumerate(sessions)}
        panel["group__"+group]=[values.get((issuer,d),np.nan) for issuer,d in zip(panel.issuer,panel.date)]
        for window in [5,21,63]:
            recency={}
            for issuer in known:
                v=counts.get((issuer,group),np.zeros(len(dates)))
                for i,d in enumerate(sessions):
                    # Left-censor full-history windows; unknown early history is missing.
                    recency[(issuer,d)]=float(v[i-window:i].sum()>0) if i>=window else np.nan
            panel[f"recent__{group}__{window}"]=[recency.get((issuer,d),np.nan) for issuer,d in zip(panel.issuer,panel.date)]
    output.mkdir(parents=True,exist_ok=False)
    panel.to_csv(output/"panel.csv",index=False)
    write_json(output/"dense-config.json",{"sessions":sessions,"groups":GROUPS,"controls":CONTROLS,"offsets":OFFSETS,
                                         "horizons":HORIZONS,"resamples":RESAMPLES,"source_snapshot":meta["snapshot_id"],
                                         "context_source_hash":digest(context_path/"download-report.json"),"plan_commits":PLAN_COMMITS})
    return {"rows":len(panel),"covered_issuers":len(known),"files":{n:digest(output/n) for n in ["panel.csv","dense-config.json"]}}


def support(frame,feature,target,minimum=8):
    q=frame.dropna(subset=[feature,target]+CONTROLS)
    event=q[q[feature]!=0]
    result={"rows":len(q),"issuers":q.issuer.nunique(),"dates":q.date.nunique(),
            "positive_rows":len(event),"positive_issuers":event.issuer.nunique(),"status":"measured","reason":None}
    if len(q)<40 or q[feature].nunique()<2 or q[target].nunique()<2:
        result.update(status="inconclusive",reason="Insufficient rows or variation")
    elif feature not in CONTROLS and (len(event)<minimum or event.issuer.nunique()<3):
        result.update(status="inconclusive",reason="Insufficient positive event/issuer support")
    return q,result


def cluster_ols(frame,columns,target,focus,spec,bootstrap=True):
    """Within-issuer fit and exact repeated-cluster sufficient-statistic bootstrap."""
    numeric=columns+[target]
    w=frame[numeric]-frame.groupby("issuer")[numeric].transform("mean")
    x,y=w[columns].to_numpy(),w[target].to_numpy()
    if np.linalg.matrix_rank(x)<len(columns):
        return {"status":"inconclusive","reason":"Rank-deficient conditional design"}
    coefficient=np.linalg.lstsq(x,y,rcond=None)[0][columns.index(focus)]
    result={"coefficient":scalar(coefficient),"issuer_fixed_effects":True,"inference":"Descriptive discovery association; issuer-cluster pointwise uncertainty"}
    groups=[v.to_numpy() for _,v in frame.groupby("issuer").groups.items()]
    # Reset positions because callers can have noncontiguous retained indexes.
    position={idx:i for i,idx in enumerate(frame.index)}
    groups=[np.array([position[idx] for idx in g]) for g in groups]
    xx=np.array([x[g].T@x[g] for g in groups]);xy=np.array([x[g].T@y[g] for g in groups])
    leave=[]
    for i in range(len(groups)):
        a,b=xx.sum(axis=0)-xx[i],xy.sum(axis=0)-xy[i]
        if np.linalg.matrix_rank(a)==len(columns):
            leave.append(np.linalg.solve(a,b)[columns.index(focus)])
    result.update(leave_one_issuer_min=scalar(min(leave)) if leave else None,
                  leave_one_issuer_max=scalar(max(leave)) if leave else None)
    if bootstrap and len(groups)>=8:
        rng=np.random.default_rng(seed(spec));draws=[]
        for _ in range(RESAMPLES):
            pick=rng.integers(0,len(groups),len(groups))
            a,b=xx[pick].sum(axis=0),xy[pick].sum(axis=0)
            if np.linalg.matrix_rank(a)==len(columns):
                draws.append(np.linalg.solve(a,b)[columns.index(focus)])
        result["valid_bootstrap_draws"]=len(draws)
        if len(draws)>=900:
            lo,hi=np.quantile(draws,[.025,.975])
            result.update(ci_low=scalar(lo),ci_high=scalar(hi))
        else:
            result["uncertainty_reason"]="Fewer than 900 full-rank issuer-bootstrap draws"
    else:
        result["uncertainty_reason"]="Bootstrap omitted for descriptive map or fewer than eight issuers"
    return result


def correlation(x,y,rank=False):
    if len(x)<3 or np.std(x)==0 or np.std(y)==0:
        return None
    if rank:
        x=pd.Series(x).rank().to_numpy();y=pd.Series(y).rank().to_numpy()
    return scalar(np.corrcoef(x,y)[0,1])


def dense_relationships(panel,config):
    rows=[]
    features=CONTROLS+["group__"+g for g in GROUPS]
    context=[f"recent__{g}__{w}" for g in GROUPS for w in [5,21,63]]
    for buffer in OFFSETS:
        p=shifted(panel,features+context,buffer,config["sessions"])
        for first,second in itertools.combinations(features+context,2):
            q=p.dropna(subset=[first,second])
            spec={"method":"input_relationship","feature":first,"other":second,"buffer":buffer}
            r={**spec,"rows":len(q),"issuers":q.issuer.nunique(),"dates":q.date.nunique(),
               "pearson":correlation(q[first].to_numpy(),q[second].to_numpy()),
               "spearman":correlation(q[first].to_numpy(),q[second].to_numpy(),True)}
            r.update(status="measured" if r["pearson"] is not None else "inconclusive",reason=None if r["pearson"] is not None else "No variation")
            rows.append(r)
        for feature,h,kind in itertools.product(features,HORIZONS,["return","volatility"]):
            target=f"{kind}_{h}"
            q,r=support(p,feature,target)
            spec={"method":"buffered_conditional","feature":feature,"target":target,"horizon":h,"buffer":buffer}
            r.update(spec)
            if r["status"]=="measured":
                columns=list(dict.fromkeys(CONTROLS+[feature]))
                r.update(cluster_ols(q,columns,target,feature,spec,bootstrap=False))
                r.update(pearson=correlation(q[feature].to_numpy(),q[target].to_numpy()),
                         spearman=correlation(q[feature].to_numpy(),q[target].to_numpy(),True))
            rows.append(r)
    return rows,{}


def context_interactions(panel,config):
    rows=[]
    features=["group__"+g for g in GROUPS]+[f"recent__{g}__{w}" for g in GROUPS for w in [5,21,63]]
    for buffer in OFFSETS:
        p=shifted(panel,CONTROLS+features,buffer,config["sessions"])
        for lead,group,window,h,kind in itertools.product(["cfo","ceo"],["earnings","guidance","compensation","debt"],[5,21,63],HORIZONS,["return","volatility"]):
            a,b,target="group__"+lead,f"recent__{group}__{window}",f"{kind}_{h}"
            q=p.dropna(subset=CONTROLS+[a,b,target]).copy()
            event=q[q[a]==1]
            with_n=int((event[b]==1).sum());without_n=int((event[b]==0).sum())
            spec={"method":"prior_context_interaction","lead":lead,"context":group,"window":window,
                  "target":target,"horizon":h,"buffer":buffer}
            r={**spec,"rows":len(q),"issuers":q.issuer.nunique(),"event_rows":len(event),"event_issuers":event.issuer.nunique(),
               "with_context":with_n,"without_context":without_n,"status":"measured","reason":None}
            if min(with_n,without_n)<8 or event.issuer.nunique()<3:
                r.update(status="inconclusive",reason="Requires eight events on each side and three event issuers")
            else:
                q["interaction"]=q[a]*q[b]
                r.update(cluster_ols(q,CONTROLS+[a,b,"interaction"],target,"interaction",spec))
            rows.append(r)
    return rows,{}


def option_panel(sources,stock):
    """Features/targets from fixed historical contracts, computed on the cluster."""
    rows=[];ds=sources["sessions"]
    lookup=stock.set_index(["ticker","date"])
    for a in sources["anchors"]:
        for bucket,reason in a.get("bucket_exclusions",{}).items():
            for b,when in {"pre":a["pre"],**a["observations"]}.items():
                for max_age in [0,1,3]:
                    rows.append({"anchor_id":a["anchor_id"],"event_id":a["event_id"],"cohort":a["cohort"],
                                 "ticker":a["ticker"],"issuer":a["issuer"],"date":when,"bucket":bucket,"buffer":b,"max_age":max_age,
                                 "cfo":int("cfo_appointment" in a["categories"]),"ceo":int("ceo_departure" in a["categories"]),
                                 "compensation":int("executive_compensation_change" in a["same_filing_categories"]),
                                 "status":"inconclusive","reason":reason})
        for bucket,s in a["selected"].items():
            bars={leg:sources["bar_objects"][oid] for leg,oid in s["bar_objects"].items()}
            for b,when in {"pre":a["pre"],**a["observations"]}.items():
                for max_age in [0,1,3]:
                    r={"anchor_id":a["anchor_id"],"event_id":a["event_id"],"cohort":a["cohort"],"ticker":a["ticker"],
                       "issuer":a["issuer"],"date":when,"pre":a["pre"],"bucket":bucket,"buffer":b,"max_age":max_age,
                       "expiry":s["expiry"],"strike":s["strike"],"selection_moneyness":s["selection_moneyness"],
                       "cfo":int("cfo_appointment" in a["categories"]),"ceo":int("ceo_departure" in a["categories"]),
                       "compensation":int("executive_compensation_change" in a["same_filing_categories"]),
                       "earnings":int(bool(set(GROUPS["earnings"]) & set(a["same_filing_categories"]))),
                       "guidance":int(bool(set(GROUPS["guidance"]) & set(a["same_filing_categories"]))),
                       "status":"measured","reason":None}
                    # Quote coverage is distinct from daily-trade mark coverage.
                    # A missing trade must not hide an observed historical quote.
                    if bucket=="120" and b=="pre":
                        quotes=s.get("pre_quotes",{})
                        if all(quotes.get(leg) for leg in ["call","put"]):
                            for leg in ["call","put"]:
                                q=quotes[leg][0];bid,ask=q.get("bid_price"),q.get("ask_price")
                                r[leg+"_quote_age_seconds"]=(s["quote_cutoff_ns"]-q["sip_timestamp"])/1e9
                                r[leg+"_bid_size"]=q.get("bid_size")
                                r[leg+"_ask_size"]=q.get("ask_size")
                                if bid is not None and ask is not None and 0<=bid<=ask and ask>0:
                                    r[leg+"_relative_spread"]=(ask-bid)/((ask+bid)/2)
                                    r[leg+"_quote_mid"]=(ask+bid)/2
                            r["quote_leg_time_difference_seconds"]=abs(quotes["call"][0]["sip_timestamp"]-quotes["put"][0]["sip_timestamp"])/1e9
                    if when is None or when>=s["expiry"]:
                        r.update(status="inconclusive",reason="Observation missing or at/after expiry");rows.append(r);continue
                    marks={leg:backward_mark(v,when,ds,max_age) for leg,v in bars.items()}
                    if not all(marks.values()):
                        r.update(status="inconclusive",reason="Missing or stale call/put trade bar");rows.append(r);continue
                    c,p=marks["call"]["price"],marks["put"]["price"]
                    dte=(pd.Timestamp(s["expiry"])-pd.Timestamp(when)).days
                    spot=s["strike"]*np.exp(-.04*dte/365.25)+c-p
                    if spot<=0:
                        r.update(status="inconclusive",reason="Nonpositive approximate parity spot");rows.append(r);continue
                    r.update(call=c,put=p,premium_sum=c+p,parity_spot=spot,dte=dte,
                             implied_move=(c+p)/spot,normalized_uncertainty=(c+p)/spot/np.sqrt(dte/365.25),
                             asymmetry=(c-p)/(c+p),moneyness=s["strike"]/spot,
                             call_age=marks["call"]["age"],put_age=marks["put"]["age"],
                             age_difference=abs(marks["call"]["age"]-marks["put"]["age"]),
                             call_volume=marks["call"]["volume"],put_volume=marks["put"]["volume"],
                             call_contract=s["legs"]["call"]["ticker"],put_contract=s["legs"]["put"]["ticker"])
                    if (a["ticker"],when) in lookup.index:
                        st=lookup.loc[(a["ticker"],when)]
                        r.update({k:float(st[k]) for k in CONTROLS})
                    for h in HORIZONS:
                        i=ds.index(when)+h
                        end=ds[i] if i<len(ds) else None
                        r[f"target_end_{h}"]=end
                        if end is None or end>=s["expiry"]:
                            r[f"missing_{h}"]="development_or_expiry_boundary";continue
                        ex={leg:backward_mark(v,end,ds,max_age) for leg,v in bars.items()}
                        if not all(ex.values()):
                            r[f"missing_{h}"]="missing_or_stale_outcome_leg";continue
                        r[f"call_change_{h}"]=ex["call"]["price"]/c-1
                        r[f"put_change_{h}"]=ex["put"]["price"]/p-1
                        r[f"sum_change_{h}"]=(ex["call"]["price"]+ex["put"]["price"])/(c+p)-1
                        if (a["ticker"],when) in lookup.index:
                            r[f"stock_return_{h}"]=scalar(lookup.loc[(a["ticker"],when),f"return_{h}"])
                            r[f"stock_rms_{h}"]=scalar(lookup.loc[(a["ticker"],when),f"volatility_{h}"])
                    if bucket=="120" and b=="pre":
                        if all(leg+"_quote_mid" in r for leg in ["call","put"]):
                            r["quote_vs_trade_sum_fraction"]=(r["call_quote_mid"]+r["put_quote_mid"])/(c+p)-1
                    rows.append(r)
    result=pd.DataFrame(rows)
    expected=["bucket","buffer","max_age","status","cohort","cfo","ceo","issuer","date","anchor_id","event_id","compensation"]
    expected += ["implied_move","normalized_uncertainty","asymmetry","moneyness","dte","call_volume","put_volume","age_difference"]+CONTROLS
    expected += [f"{kind}_{h}" for kind in ["call_change","put_change","sum_change","stock_return","stock_rms","target_end"] for h in HORIZONS]
    for col in expected:
        if col not in result:result[col]=np.nan
    return result


def mean_contrast(frame,value,spec):
    """Paired event/prior-ordinary anchors, retaining missing pair exclusions."""
    event=frame[frame.cohort=="event"][["event_id","issuer",value]].dropna()
    ordinary=frame[frame.cohort=="ordinary"][["event_id",value]].dropna()
    q=event.merge(ordinary,on="event_id",suffixes=("_event","_ordinary"),validate="one_to_one")
    r={**spec,"pairs":len(q),"issuers":q.issuer.nunique(),"event_rows":len(event),"ordinary_rows":len(ordinary),
       "status":"measured","reason":None}
    if len(q)<8 or q.issuer.nunique()<3:
        return {**r,"status":"inconclusive","reason":"Fewer than eight complete pairs or three issuers"},q
    q["difference"]=q[value+"_event"]-q[value+"_ordinary"]
    r.update(mean_difference=scalar(q.difference.mean()),median_difference=scalar(q.difference.median()),
             units="Fractional option-price change or declared feature units; no strategy P&L")
    leave=[q[q.issuer!=issuer].difference.mean() for issuer in q.issuer.unique()]
    r.update(leave_one_issuer_min=scalar(min(leave)),leave_one_issuer_max=scalar(max(leave)))
    groups=[g.difference.to_numpy() for _,g in q.groupby("issuer")]
    if len(groups)>=8:
        rng=np.random.default_rng(seed(spec));draws=[]
        for _ in range(RESAMPLES):
            pick=rng.integers(0,len(groups),len(groups))
            draws.append(np.concatenate([groups[i] for i in pick]).mean())
        lo,hi=np.quantile(draws,[.025,.975]);r.update(ci_low=scalar(lo),ci_high=scalar(hi),valid_bootstrap_draws=RESAMPLES)
    else:
        r["uncertainty_reason"]="Fewer than eight paired issuers"
    return r,q


def option_relationships(options):
    rows=[]
    features=["implied_move","normalized_uncertainty","asymmetry","moneyness","dte","call_volume","put_volume","age_difference"]
    for bucket,b,max_age in itertools.product(BUCKETS,["pre"]+[str(x) for x in BUFFERS],[0,1,3]):
        q=options[(options.bucket==bucket)&(options.buffer==b)&(options.max_age==max_age)&(options.status=="measured")]
        # Input dependencies are measured on event anchors; ordinary copies must not double-count them.
        event=q[q.cohort=="event"]
        for first,second in itertools.combinations(features,2):
            p=event.dropna(subset=[first,second])
            spec={"method":"option_input_relationship","bucket":bucket,"buffer":b,"max_age":max_age,"feature":first,"other":second}
            r={**spec,"rows":len(p),"issuers":p.issuer.nunique(),"pearson":correlation(p[first].to_numpy(),p[second].to_numpy()),
               "spearman":correlation(p[first].to_numpy(),p[second].to_numpy(),True)}
            r.update(status="measured" if len(p)>=8 and p.issuer.nunique()>=3 and r["pearson"] is not None else "inconclusive")
            rows.append(r)
        for lead,h in itertools.product(["cfo","ceo"],HORIZONS):
            p=event[event[lead]==1]
            for target in [f"stock_rms_{h}",f"sum_change_{h}"]:
                z=p.dropna(subset=["implied_move",target]) if target in p else p.iloc[:0]
                spec={"method":"implied_uncertainty_outcome","bucket":bucket,"buffer":b,"max_age":max_age,"lead":lead,"horizon":h,"target":target}
                r={**spec,"rows":len(z),"issuers":z.issuer.nunique(),"status":"measured"}
                if len(z)<8 or z.issuer.nunique()<3:
                    r.update(status="inconclusive",reason="Insufficient event/issuer support")
                else:
                    r.update(pearson=correlation(z.implied_move.to_numpy(),z[target].to_numpy()),
                             spearman=correlation(z.implied_move.to_numpy(),z[target].to_numpy(),True))
                    if r["pearson"] is None:r.update(status="inconclusive",reason="No variation")
                rows.append(r)
    return rows,{}


def option_repricing(options):
    rows=[];pairs=[]
    for bucket,b,max_age,lead,h,kind in itertools.product(BUCKETS,["pre"]+[str(x) for x in BUFFERS],[0,1,3],["cfo","ceo"],HORIZONS,["call","put","sum"]):
        value=f"{kind}_change_{h}"
        q=options[(options.bucket==bucket)&(options.buffer==b)&(options.max_age==max_age)&(options[lead]==1)&(options.status=="measured")]
        spec={"method":"paired_option_repricing","bucket":bucket,"buffer":b,"max_age":max_age,"lead":lead,"horizon":h,"target":value}
        if value not in q:
            rows.append({**spec,"status":"inconclusive","reason":"No observed outcome before development/expiry boundary","pairs":0});continue
        r,p=mean_contrast(q,value,spec);rows.append(r)
        if len(p):
            pairs += [{**spec,**record} for record in p.to_dict("records")]
        # Exact same-filing compensation subgroup: not a planned/surprising text label.
        event=q[(q.cohort=="event")].dropna(subset=[value])
        first,second=event[event.compensation==1],event[event.compensation==0]
        subgroup={**spec,"method":"compensation_option_context","with_context":len(first),"without_context":len(second),
                  "issuers":event.issuer.nunique(),"status":"measured"}
        if min(len(first),len(second))<8 or event.issuer.nunique()<3:
            subgroup.update(status="inconclusive",reason="Requires eight outcomes in both exact compensation groups")
        else:
            subgroup.update(mean_difference=scalar(first[value].mean()-second[value].mean()),
                            inference="Raw selected subgroup contrast; not paired/causal and no interval")
        rows.append(subgroup)
    return rows,{"paired_option_rows":pairs}


def maturity_quality(options):
    rows=[]
    for b,max_age in itertools.product(["pre"]+[str(x) for x in BUFFERS],[0,1,3]):
        q=options[(options.buffer==b)&(options.max_age==max_age)]
        for bucket in BUCKETS:
            z=q[q.bucket==bucket]
            measured=z[z.status=="measured"]
            rows.append({"method":"mark_quality_coverage","buffer":b,"max_age":max_age,"bucket":bucket,
                         "attempted_anchors":len(z),"usable_anchors":len(measured),"missing_anchors":len(z)-len(measured),
                         "status":"measured","reason":"Coverage count, not an effect estimate"})
        for first,second,feature in itertools.product(BUCKETS,BUCKETS,["implied_move","normalized_uncertainty","asymmetry"]):
            if int(first)>=int(second):continue
            z=q[(q.cohort=="event")&(q.status=="measured")]
            a=z[z.bucket==first][["anchor_id","issuer",feature]]
            c=z[z.bucket==second][["anchor_id",feature]]
            p=a.merge(c,on="anchor_id",suffixes=("_first","_second"),validate="one_to_one")
            r={"method":"cross_maturity_relationship","buffer":b,"max_age":max_age,"bucket":first,"other_bucket":second,
               "feature":feature,"rows":len(p),"issuers":p.issuer.nunique(),"status":"measured"}
            if len(p)<8 or p.issuer.nunique()<3:r.update(status="inconclusive",reason="Insufficient paired maturity support")
            else:r.update(pearson=correlation(p[feature+"_first"].to_numpy(),p[feature+"_second"].to_numpy()),
                          mean_difference=scalar((p[feature+"_second"]-p[feature+"_first"]).mean()))
            rows.append(r)
    q=options[(options.buffer=="pre")&(options.bucket=="120")&(options.max_age==3)]
    for feature in ["call_relative_spread","put_relative_spread","call_quote_age_seconds","put_quote_age_seconds",
                    "quote_leg_time_difference_seconds","quote_vs_trade_sum_fraction"]:
        p=q.dropna(subset=[feature]) if feature in q else q.iloc[:0]
        r={"method":"quote_audit","feature":feature,"rows":len(p),"issuers":p.issuer.nunique(),"status":"measured" if len(p) else "inconclusive"}
        if len(p):r.update(median=scalar(p[feature].median()),p90=scalar(p[feature].quantile(.9)),maximum=scalar(p[feature].max()))
        rows.append(r)
    return rows,{}


def ridge_predictions(panel,config,options=None):
    """Fixed chronological augmentation on identical cohorts; no trading model."""
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    rows=[];losses=[]
    dates=sorted(panel.date.unique());cuts=[int(len(dates)*f) for f in [.4,.6,.8]]+[len(dates)]
    families={"disclosure_groups":["group__"+g for g in GROUPS],
              "groups_and_prior_context":["group__"+g for g in GROUPS]+[f"recent__{g}__{w}" for g in GROUPS for w in [5,21,63]]}
    for b,h,kind,(family,features),fold in itertools.product(OFFSETS,HORIZONS,["return","volatility"],families.items(),range(3)):
        p=shifted(panel,CONTROLS+features,b,config["sessions"])
        target=f"{kind}_{h}";p=p.dropna(subset=CONTROLS+features+[target,f"target_end_{h}"])
        start=dates[cuts[fold]];stop=dates[cuts[fold+1]] if cuts[fold+1]<len(dates) else "9999-12-31"
        train=p[(p.date<start)&(p[f"target_end_{h}"]<start)]
        valid=p[(p.date>=start)&(p.date<stop)]
        spec={"method":"chronological_ridge","buffer":b,"horizon":h,"target":target,"family":family,"fold":fold,
              "validation_start":start,"train_rows":len(train),"rows":len(valid),"status":"measured"}
        if len(train)<100 or len(valid)<40:
            rows.append({**spec,"status":"inconclusive","reason":"Insufficient chronological cohort"});continue
        baseline=make_pipeline(StandardScaler(),Ridge(alpha=10))
        augmented=make_pipeline(StandardScaler(),Ridge(alpha=10))
        baseline.fit(train[CONTROLS],train[target]);augmented.fit(train[CONTROLS+features],train[target])
        e0=(valid[target].to_numpy()-baseline.predict(valid[CONTROLS]))**2
        e1=(valid[target].to_numpy()-augmented.predict(valid[CONTROLS+features]))**2
        for cohort in ["pooled","event"]:
            take=np.ones(len(valid),dtype=bool) if cohort=="pooled" else ((valid.group__cfo==1)|(valid.group__ceo==1)).to_numpy()
            q=valid.iloc[np.flatnonzero(take)]
            r={**spec,"cohort":cohort,"rows":int(take.sum()),"issuers":q.issuer.nunique(),"dates":q.date.nunique()}
            if len(q)<8 or q.issuer.nunique()<3:
                rows.append({**r,"status":"inconclusive","reason":"Insufficient validation event/issuer support"});continue
            base=float(e0[take].mean());aug=float(e1[take].mean())
            r.update(baseline_mse=base,augmented_mse=aug,mean_loss_improvement=base-aug,relative_improvement=(base-aug)/base if base>0 else None)
            bydate=pd.DataFrame({"date":q.date.to_numpy(),"improvement":(e0-e1)[take]}).groupby("date").agg(total=("improvement","sum"),n=("improvement","size"))
            block=max(5,h)
            if len(bydate)>=4*block and cohort=="pooled":
                rng=np.random.default_rng(seed(r));stats=bydate.to_numpy();draws=[]
                for _ in range(RESAMPLES):
                    starts=rng.integers(0,len(stats)-block+1,int(np.ceil(len(stats)/block)))
                    indices=np.concatenate([np.arange(i,i+block) for i in starts])[:len(stats)]
                    sample=stats[indices];draws.append(sample[:,0].sum()/sample[:,1].sum())
                lo,hi=np.quantile(draws,[.025,.975]);r.update(ci_low=scalar(lo),ci_high=scalar(hi),date_block=block)
            else:r["uncertainty_reason"]="Sparse event dates or fewer than four outcome-length date blocks"
            rows.append(r)
            for date,record in bydate.iterrows():losses.append({**spec,"cohort":cohort,"date":date,"total_loss_improvement":float(record.total),"count":int(record.n)})
    return rows,{"paired_loss_by_date":losses}


def read_manifest(run):
    run=Path(run);m=read_json(run/"manifest.json")
    if identity({k:v for k,v in m.items() if k!="manifest_id"})!=m["manifest_id"]:
        raise ValueError("Connection manifest changed")
    for name,expected in {**m["code_files"],**m["input_files"]}.items():
        if digest(ROOT/name)!=expected:raise ValueError("Frozen file changed: "+name)
    return m


def freeze(snapshot,run,options=None):
    snapshot,run=Path(snapshot).resolve(),Path(run).resolve()
    if run.exists():raise ValueError("Refusing to overwrite a frozen run")
    files=list((ROOT/"discovery").glob("*.py"))+list((ROOT/"tests").glob("*.py"))+[ROOT/"pyproject.toml",ROOT/"uv.lock",ROOT/"research_config.py",ROOT/".python-version",ROOT/"tools/check_massive_coverage.py"]
    files += list((ROOT/"Hypotheses").glob("H*/analysis.py"))
    inputs=[snapshot/"panel.csv",snapshot/"dense-config.json"]
    if options:inputs.append(Path(options).resolve()/"option-sources.json")
    m={"schema":1,"created_at":now(),"run_id":run.name,"plan_commits":PLAN_COMMITS,"snapshot":snapshot.relative_to(ROOT).as_posix(),
       "option_sources":str((Path(options).resolve()/"option-sources.json").relative_to(ROOT)).replace("\\","/") if options else None,
       "code_files":{p.relative_to(ROOT).as_posix():digest(p) for p in files},
       "input_files":{p.relative_to(ROOT).as_posix():digest(p) for p in inputs},
       "studies":list(STUDIES) if options else ["H12","H16","H17"],"scope":"Statistical discovery, 2024–2025; no OOS or trading"}
    m["manifest_id"]=identity(m);run.mkdir(parents=True);write_json(run/"manifest.json",m)
    return m


def task(run,study):
    run=Path(run);m=read_manifest(run)
    if study not in m["studies"]:raise ValueError("Study outside frozen run")
    p=pd.read_csv(ROOT/m["snapshot"]/"panel.csv",dtype={"issuer":str})
    config=read_json(ROOT/m["snapshot"]/"dense-config.json")
    options=option_panel(read_json(ROOT/m["option_sources"]),p) if m["option_sources"] else None
    path=ROOT/"Hypotheses"/STUDIES[study]/"analysis.py"
    spec=importlib.util.spec_from_file_location("connection_"+study,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    destination=run/"studies"/study;destination.mkdir(parents=True,exist_ok=True)
    receipt={"study":study,"manifest_id":m["manifest_id"],"started_at":now(),"status":"error"}
    try:
        rows,details=module.analyze(p,config,options)
        pd.DataFrame(rows).to_csv(destination/"measurements.csv",index=False)
        for name,records in details.items():pd.DataFrame(records).to_csv(destination/(name+".csv"),index=False)
        if options is not None and study=="H15":options.to_csv(destination/"option-panel.csv",index=False)
        receipt.update(status="complete",attempts=len(rows),measured=sum(r["status"]=="measured" for r in rows),
                       files={f.name:digest(f) for f in destination.glob("*.csv")})
    except Exception as error:
        receipt["error_type"]=type(error).__name__;receipt["error"]=str(error)
        raise
    finally:
        receipt["finished_at"]=now();write_json(destination/"receipt.json",receipt)
    return receipt


def aggregate(run):
    run=Path(run);m=read_manifest(run);tables=[];statuses=[]
    for study in m["studies"]:
        d=run/"studies"/study
        if not (d/"receipt.json").exists():statuses.append({"study":study,"status":"missing"});continue
        r=read_json(d/"receipt.json");statuses.append(r)
        if r["manifest_id"]!=m["manifest_id"]:raise ValueError("Task identity differs")
        for f,h in r.get("files",{}).items():
            if digest(d/f)!=h:raise ValueError("Task output changed")
        if r["status"]=="complete":tables.append(pd.read_csv(d/"measurements.csv").assign(study=study))
    combined=pd.concat(tables,ignore_index=True) if tables else pd.DataFrame()
    combined.to_csv(run/"trials.csv",index=False)
    total=len(combined);measured=int((combined.status=="measured").sum()) if total else 0
    summary={"manifest_id":m["manifest_id"],"created_at":now(),"tasks":statuses,"attempts":total,"measured":measured,
             "inconclusive":total-measured,"search_family_size":total,
             "inference":"Unadjusted pointwise discovery intervals; 999 draws cannot resolve broad search-adjusted extreme tails",
             "complete":all(r.get("status")=="complete" for r in statuses) and len(statuses)==len(m["studies"])}
    write_json(run/"report.json",summary)
    (run/"REPORT.md").write_text(f"# {m['run_id']}\n\n{total} attempted comparisons; {measured} measured and {total-measured} inconclusive.\n\nAll tasks complete: {summary['complete']}. Full tables: trials.csv and studies/.\n\n2024–2025 statistical discovery. Pointwise intervals are unadjusted for {total} attempted cells; this is selected development evidence. No backtests or protected outcomes.\n",encoding="utf-8")
    return {k:v for k,v in summary.items() if k!="tasks"}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    prep=sub.add_parser("prepare");prep.add_argument("--snapshot",type=Path,required=True);prep.add_argument("--context",type=Path,required=True);prep.add_argument("--output",type=Path,required=True)
    fr=sub.add_parser("freeze");fr.add_argument("--snapshot",type=Path,required=True);fr.add_argument("--run",type=Path,required=True);fr.add_argument("--options",type=Path)
    t=sub.add_parser("task");t.add_argument("--run",type=Path,required=True);t.add_argument("--study",choices=STUDIES,required=True)
    a=sub.add_parser("aggregate");a.add_argument("--run",type=Path,required=True)
    args=p.parse_args()
    if args.command=="prepare":result=dense_prepare(args.snapshot,args.context,args.output)
    elif args.command=="freeze":result=freeze(args.snapshot,args.run,args.options)
    elif args.command=="task":result=task(args.run,args.study)
    else:result=aggregate(args.run)
    print(json.dumps(result))


if __name__=="__main__":main()
