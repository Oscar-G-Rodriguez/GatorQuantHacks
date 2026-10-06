"""Immutable H21 runs. Real-data scientific commands require a Slurm allocation."""
from __future__ import annotations

import argparse
import html
import itertools
import json
import os
import pickle
import time
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

from .io import ROOT, digest, identity, now, read_json, write_json
from .atlas_data import settings, load_source, PLAN_COMMIT
from .atlas_features import normalize, build_panel, pattern_catalog, feature_matrix, fitting_catalog, CONTROLS, KINDS, scramble
from .atlas_statistics import forecast_cell, joint_weights, romano_wolf, support
from .atlas_responses import response_cell,matched_values
from .atlas_statistics import outer_masks

FOLDER = ROOT / "Hypotheses/H21 - Massive Disclosure Research Atlas"


def scheduled():
    if not os.environ.get("SLURM_JOB_ID"): raise RuntimeError("H21 real scientific work requires a scheduled HiPerGator allocation")


def create_manifest(source, run, options=None):
    source, run = Path(source).resolve(), Path(run).resolve()
    if not source.is_relative_to(ROOT) or not run.is_relative_to(ROOT): raise ValueError("Use private repository run paths")
    s,t,o=load_source(source); run.mkdir(parents=True,exist_ok=False)
    code=list((ROOT/"discovery").glob("*.py"))+list((ROOT/"tests").glob("test_atlas*.py"))
    code += [ROOT/"pyproject.toml",ROOT/"uv.lock",ROOT/".python-version",ROOT/"config/disclosure-atlas.json",FOLDER/"analysis.py",FOLDER/"Hypothesis.md",FOLDER/"Atlas Review.ipynb",ROOT/"docs/discovery/atlas.md"]
    m={"schema":1,"study":"H21","created_at":now(),"plan_commit":PLAN_COMMIT,"source":source.relative_to(ROOT).as_posix(),
       "run":run.relative_to(ROOT).as_posix(),"source_sha256":digest(source/"source.json"),"source_id":s["source_id"],
       "settings":s["settings"],"code":{p.relative_to(ROOT).as_posix():digest(p) for p in sorted(code)},"sealed_excluded":True}
    m["code_commit"]=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    m["task_mapping"]={"cells":cells(m["settings"]),"pilot_cells":[0,35,76,127],
        "placebo_replicas":list(range(m["settings"]["placebos"])),"resample_blocks":m["settings"]["block_lengths"],
        "resample_batches":int(np.ceil(m["settings"]["resamples"]/m["settings"]["resample_batch"])),
        "seeds":{"models_and_text":m["settings"]["seed"],"placebo":"seed + 100000 + replica",
            "resample":"seed + block*1000000 + draw"}}
    if options:
        options=Path(options).resolve()
        if not options.is_relative_to(ROOT):raise ValueError("Options source must be private local repository data")
        osource=read_json(options/"options-source.json")
        if not osource["complete"]:raise ValueError("Freeze complete option coverage, including explicit unavailable inputs")
        m.update(options_source=options.relative_to(ROOT).as_posix(),options_sha256=digest(options/"options-source.json"))
    m["manifest_id"]=identity(m);write_json(run/"manifest.json",m);return m


def manifest(run,verify_code=True,allow_frozen=False):
    run=Path(run);m=read_json(run/"manifest.json")
    if identity({k:v for k,v in m.items() if k!="manifest_id"})!=m["manifest_id"]:raise ValueError("Manifest changed")
    if verify_code:
        for name,value in m["code"].items():
            current=ROOT/name;frozen=run/"frozen-code"/name
            if not current.exists() or digest(current)!=value:
                if not allow_frozen or not frozen.exists() or digest(frozen)!=value:raise ValueError("Frozen code changed: "+name)
    if digest(ROOT/m["source"]/"source.json")!=m["source_sha256"]:raise ValueError("Frozen source changed")
    if m.get("options_source") and digest(ROOT/m["options_source"]/"options-source.json")!=m["options_sha256"]:raise ValueError("Frozen options changed")
    return m


def write_table(path, rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+f".{os.getpid()}.tmp")
    pd.DataFrame(rows).to_csv(temporary,index=False);os.replace(temporary,path)


def receipt(run, stage, files, state="completed",extra=None):
    m=manifest(run);run=Path(run)
    result={"manifest_id":m["manifest_id"],"stage":stage,"state":state,"finished_at":now(),"slurm_job_id":os.getenv("SLURM_JOB_ID"),
            "files":{p.relative_to(run).as_posix():digest(p) for p in files},**(extra or {})}
    write_json(run/"receipts"/(stage+".json"),result);return result


def done(run,stage,allow_frozen=False):
    p=Path(run)/"receipts"/(stage+".json")
    if not p.exists():return False
    r=read_json(p)
    if r["manifest_id"]!=manifest(run,allow_frozen=allow_frozen)["manifest_id"]:raise ValueError("Task receipt belongs to another run")
    if r["state"]!="completed":return False
    for file,h in r["files"].items():
        if digest(Path(run)/file)!=h:raise ValueError("Completed output changed")
        if file.endswith("/complete.json"):
            checkpoint=read_json(Path(run)/file)
            for name,value in checkpoint["files"].items():
                if digest((Path(run)/file).parent/name)!=value:raise ValueError("Nested year checkpoint changed")
    return True


def coverage(run):
    scheduled();m=manifest(run);run=Path(run);c=m["settings"]
    if done(run,"coverage") and (not m.get("options_source") or done(run,"options")):return
    source,taxonomy,objects=load_source(ROOT/m["source"])
    prices,events,issues=normalize(source,objects);panel,filings,panel_issues=build_panel(prices,events,source)
    folder=run/"outputs";folder.mkdir(exist_ok=True)
    with (folder/"panel.pkl").open("wb") as stream:pickle.dump(panel,stream,protocol=5)
    write_json(folder/"filings.json",filings)
    event_by_category={cat:[f for f in filings if cat in f["categories"]] for cat in c["categories"]};rows=[]
    option_anchors={}
    for definition in taxonomy:
        cat=definition["tertiary_category"];fs=event_by_category[cat];indices=sorted({r for f in fs for r in f["rows"]})
        issuers=len({f["issuer"] for f in fs});row={"category":cat,"primary_category":definition["primary_category"],"secondary_category":definition["secondary_category"],
            "description":definition["description"],"filings":len(fs),"issuers":issuers,"mapped_stock_rows":len(indices),
            "missing_text_filings":sum(not e["text"] for e in events if e["category"]==cat),"option_status":"not_yet_acquired","evidence_status":"coverage_only",
            "source_problems":len(issues)+len(panel_issues)+len(source["failures"]),"source_problem_scope":"Global source issues; details in quality.json",
            "outcome_count_grain":"Distinct issuer/session with a complete share-class outcome; filings remain distinct in source counts"}
        for year in range(2022,2026):row[f"filings_{year}"]=sum(f["filing_date"].startswith(str(year)) for f in fs)
        for h in c["horizons"]:
            eligible=panel.iloc[indices];row[f"complete_stock_outcomes_{h}"]=len(eligible.loc[eligible[f"return_{h}"].notna(),["issuer","date"]].drop_duplicates()) if indices else 0
        row["model_coverage_eligible"]=len(fs)>=c["train_min_activations"] and issuers>=c["train_min_issuers"]
        if row["model_coverage_eligible"]:
            for i in indices:
                for lag in c["lags"]:
                    j=i+lag
                    if j>=len(panel) or panel.iloc[j].ticker!=panel.iloc[i].ticker:continue
                    p=panel.iloc[j]
                    if not p[CONTROLS].notna().all():continue
                    key=(p.ticker,str(p.date.date()));entry=option_anchors.setdefault(key,{"ticker":p.ticker,"issuer":p.issuer,"date":key[1],"session":int(p.session),"stock_close":float(p.close),"categories":[],"role":"event"})
                    entry["categories"]=sorted(set(entry["categories"]+[cat]))
        rows.append(row)
    write_table(folder/"coverage.csv",rows)
    write_json(folder/"option-anchor-requests.json",sorted(option_anchors.values(),key=lambda x:(x["date"],x["ticker"])))
    write_json(folder/"quality.json",{"source_failures":source["failures"],"identity_issues":issues+panel_issues,
       "source_rows":len(events),"distinct_filings":len(filings),"stock_rows":len(panel),"universe":c["universe"],"availability":c["availability"],"prior_exposure":c["prior_exposure"]})
    receipt(run,"coverage",[folder/n for n in ["panel.pkl","filings.json","coverage.csv","option-anchor-requests.json","quality.json"]])
    if m.get("options_source"):
        from .atlas_options import build_option_panel
        inputs,readings,osource=build_option_panel(panel,ROOT/m["options_source"])
        np.save(folder/"option-inputs.npy",inputs,allow_pickle=False);write_table(folder/"option-coverage.csv",readings)
        targets=option_targets(panel,readings,c)
        np.savez_compressed(folder/'option-targets.npz',**targets)
        receipt(run,"options",[folder/"option-inputs.npy",folder/"option-coverage.csv",folder/'option-targets.npz'],extra={"source_id":osource["source_id"],"failures":osource["failures"]})


def option_targets(panel,readings,config):
    """Future same-contract marks are targets only, never input eligibility."""
    values={f'premium_{bucket}_{h}':np.full(len(panel),np.nan) for bucket in config['option_buckets'] for h in config['horizons']}
    lookup={(r.ticker,str(r.date.date())):i for i,r in panel.iterrows()}
    for row in readings:
        i=lookup.get((row['ticker'],row['date']))
        if i is None:continue
        for h in config['horizons']:
            value=row.get('premium_change_'+str(h));name=f'premium_{row["bucket"]}_{h}'
            if value is not None and np.isfinite(value) and pd.notna(panel.iloc[i][f'target_end_{h}']):values[name][i]=value
    return values


def option_requests(run):
    scheduled();run=Path(run);panel,filings,c=prepared(run);anchors=read_json(run/"outputs/option-anchor-requests.json")
    lookup={(a["ticker"],a["date"]):a for a in anchors};days=len(sessions_from_panel(panel))
    active=np.zeros(len(panel),bool)
    for f in filings:active[f["rows"]]=True
    forbidden=active.copy()
    for offset in range(0,len(panel),days):
        for s in np.flatnonzero(active[offset:offset+days]):forbidden[offset+max(0,s-21):offset+min(days,s+22)]=True
    for h,lag in itertools.product(c["horizons"],c["lags"]):
        shifted=np.zeros(len(panel),bool)
        for i in np.flatnonzero(active):
            if i%days+lag<days:shifted[i+lag]=True
        for year in c["fold_years"]:
            train,test=outer_masks(panel,h,year,f"return_{h}")
            matches=matched_values(panel,train,test,shifted,forbidden,h,f"return_{h}",return_matches=True)
            for chosen in matches.values():
                for j in chosen:
                    p=panel.iloc[j];key=(p.ticker,str(p.date.date()))
                    lookup.setdefault(key,{"ticker":p.ticker,"issuer":p.issuer,"date":key[1],"session":int(p.session),"stock_close":float(p.close),"categories":[],"role":"ordinary"})
    p=run/"outputs/option-matched-requests.json";write_json(p,sorted(lookup.values(),key=lambda x:(x["date"],x["ticker"])))
    receipt(run,"option-requests",[p],extra={"anchors":len(lookup),"selection":"coverage and strictly prior state, never favorable outcomes"})


def sessions_from_panel(panel):return panel.loc[panel.ticker==panel.ticker.iloc[0],"date"].to_numpy()


def prepared(run):
    run=Path(run);m=manifest(run)
    if not done(run,"coverage"):raise ValueError("Coverage stage must complete first")
    with (run/"outputs/panel.pkl").open("rb") as stream:panel=pickle.load(stream)
    return panel,read_json(run/"outputs/filings.json"),m["settings"]


def patterns(run):
    scheduled();run=Path(run)
    if done(run,"patterns"):return
    panel,filings,c=prepared(run);start=time.perf_counter()
    cat=pattern_catalog(filings,c,minimum=c["train_min_activations"])
    write_json(run/"outputs/catalog.json",cat)
    model_cat=fitting_catalog(cat,c);write_json(run/"outputs/model-catalog.json",model_cat)
    candidate_names={p["name"] for p in model_cat}
    rows=[{k:v for k,v in row.items() if k!="rows"} for row in cat]
    signatures={}
    for row, entry in zip(rows, cat):
        signature=identity(entry["rows"]);row["same_activation_as"]=signatures.get(signature);signatures.setdefault(signature,row["name"])
        row["inventory_status"]="requires_training_only_floor" if row["name"] in candidate_names else "insufficient_overall_occurrence_support"
    write_table(run/"outputs/patterns.csv",rows)
    relation=[]
    labels=np.array([[cat in f["categories"] for cat in c["categories"]] for f in filings],dtype=float).reshape(len(filings),len(c["categories"]))
    for a,b in itertools.combinations(range(len(c["categories"])),2):
        both=int((labels[:,a]*labels[:,b]).sum());pa=float(labels[:,a].mean()) if len(filings) else 0;pb=float(labels[:,b].mean()) if len(filings) else 0
        denominator=np.sqrt(pa*(1-pa)*pb*(1-pb))
        relation.append({"category_a":c["categories"][a],"category_b":c["categories"][b],"same_filings":both,
            "phi":(both/len(filings)-pa*pb)/denominator if denominator else None,"grain":"one distinct CIK/accession filing"})
    write_table(run/"outputs/relationships.csv",relation)
    receipt(run,"patterns",[run/"outputs/catalog.json",run/"outputs/model-catalog.json",run/"outputs/patterns.csv",run/"outputs/relationships.csv"],extra={"seconds":time.perf_counter()-start,"patterns":len(cat),"fitting_candidates":len(model_cat)})


def save_losses(path,losses):
    values={}
    for series in losses:
        key=series["comparison_id"];values[key+"_rows"]=np.asarray(series["rows"],dtype=np.int32);values[key+"_values"]=np.asarray(series["values"],dtype=float)
    path=Path(path);temp=path.with_suffix(".tmp.npz");np.savez_compressed(temp,**values);os.replace(temp,path)


def search_score(losses,panel):
    scores=[]
    for series in losses:
        ix=series["rows"];v=np.asarray(series["values"]);w=panel.weight.to_numpy()[ix]
        if not len(v):continue
        mean=float(np.average(v,weights=w));variance=float(np.average((v-mean)**2,weights=w))
        independent=len(panel.iloc[ix][["issuer","date"]].drop_duplicates())
        se=np.sqrt(variance/max(1,independent))
        scores.append({"comparison_id":series["comparison_id"],"score":abs(mean/se) if se>0 else None,"mean":mean,"scale":"descriptive issuer-date standardized statistic; placebo diagnostic, not independent SE"})
    return scores


def cells(config):return [{"horizon":h,"lag":lag,"kind":kind} for h,lag,kind in itertools.product(config["horizons"],config["lags"],KINDS)]


def core(run,task,pilot=False,placebo=None,loaded=None):
    scheduled();run=Path(run);panel,filings,c=loaded or prepared(run)
    label=f"core-{task:03d}" if placebo is None else f"placebo-{placebo:03d}-{task:03d}"
    if pilot:label="pilot-"+str(task)
    if done(run,label):return
    if placebo is not None:filings=scramble(filings,panel,c,c["seed"]+100000+placebo)
    if placebo is None and done(run,"patterns"):catalog=read_json(run/"outputs/model-catalog.json")
    else:catalog=fitting_catalog(pattern_catalog(filings,c),c)
    spec=cells(c)[task];start=time.perf_counter();folder=run/"tasks"/label;folder.mkdir(parents=True,exist_ok=True)
    comp,trials,losses=[],[],[]
    for year in c["fold_years"]:
        yf=folder/str(year);yf.mkdir(exist_ok=True)
        if (yf/"complete.json").exists():
            previous=read_json(yf/"complete.json")
            for name,h in previous["files"].items():
                if digest(yf/name)!=h:raise ValueError("Year checkpoint changed")
            comp.extend(read_json(yf/"comparisons.json"));trials.extend(read_json(yf/"trials.json"))
            if placebo is None:losses.extend(read_losses(yf/"losses.npz"))
            continue
        yc={**c,"fold_years":[year]}
        options=np.load(run/"outputs/option-inputs.npy",allow_pickle=False) if done(run,"options") else None
        if options is not None:
            with np.load(run/'outputs/option-targets.npz',allow_pickle=False) as values:
                for name in values.files:panel[name]=values[name]
        a,b,d=forecast_cell(panel,filings,yc,**spec,catalog=catalog,option_values=options)
        matrix,_,_,active=feature_matrix(panel,filings,catalog,yc,spec["lag"])
        responses,response_losses=response_cell(panel,matrix,active,catalog,yc,**spec)
        a+=responses;d+=response_losses
        if options is not None and spec['kind']=='return':
            # Each horizon/delay premium target is evaluated once, within the
            # same joint inferential family as the stock comparisons.
            for bucket in c['option_buckets']:
                option_spec={**spec,'kind':'premium_'+bucket}
                oa,ob,od=forecast_cell(panel,filings,yc,**option_spec,catalog=catalog,option_values=options)
                ra,rd=response_cell(panel,matrix,active,catalog,yc,**option_spec)
                a+=oa+ra;b+=ob;d+=od+rd
        write_json(yf/"comparisons.json",a);write_json(yf/"trials.json",b);write_json(yf/"search-scores.json",search_score(d,panel))
        names=["comparisons.json","trials.json","search-scores.json"]
        if placebo is None:save_losses(yf/"losses.npz",d);names.append("losses.npz")
        write_json(yf/"complete.json",{"files":{n:digest(yf/n) for n in names},"finished_at":now()})
        comp+=a;trials+=b
        if placebo is None:losses+=d
    write_table(folder/"comparisons.csv",comp);write_table(folder/"trials.csv",trials)
    if placebo is None:save_losses(folder/"losses.npz",losses)
    import resource
    bench=time.perf_counter()
    if pilot:
        # Time actual joint weighting on the pilot's real retained loss series.
        selected=sorted(losses,key=lambda x:len(x["rows"]),reverse=True)[:100]
        columns=[];masks=[]
        for series in selected:
            r=np.asarray(series["rows"]);v=np.asarray(series["values"])
            columns.append(sparse.csc_matrix((v,(r,np.zeros(len(r),int))),shape=(len(panel),1)))
            masks.append(sparse.csc_matrix((np.ones(len(r)),(r,np.zeros(len(r),int))),shape=(len(panel),1)))
        matrix=sparse.hstack(columns,format="csr") if columns else sparse.csr_matrix((len(panel),0))
        denominator=sparse.hstack(masks,format="csr") if masks else matrix.copy()
        for b in range(100):
            w=panel.weight.to_numpy()*joint_weights(panel.issuer.to_numpy(),panel.session.to_numpy(),63,np.random.default_rng(c["seed"]+b))
            np.divide(np.asarray(matrix.T@w).ravel(),np.asarray(denominator.T@w).ravel(),
                out=np.full(len(selected),np.nan),where=np.asarray(denominator.T@w).ravel()>0)
    write_json(folder/"timing.json",{"seconds":time.perf_counter()-start,"spec":spec,"comparisons":len(comp),"trials":len(trials),"placebo":placebo,"pilot":pilot,
        "max_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,"joint_weight_100_seconds":time.perf_counter()-bench if pilot else None,
        "resampling_benchmark_columns":len(selected) if pilot else None})
    receipt(run,label,[folder/n for n in ["comparisons.csv","trials.csv","timing.json"]+(["losses.npz"] if placebo is None else [])]+[p for p in folder.glob("*/complete.json")]+[p for p in folder.glob("*/search-scores.json")])


def placebo_batch(run,replica,cell_start=0,cell_end=128):
    scheduled();panel,filings,c=prepared(run)
    for task in range(cell_start,min(cell_end,len(cells(c)))):core(run,task,placebo=replica,loaded=(panel,filings,c))


def read_losses(path):
    with np.load(path,allow_pickle=False) as a:
        return [{"comparison_id":n,"rows":a[n+"_rows"],"values":a[n+"_values"]} for n in sorted(k[:-5] for k in a.files if k.endswith("_rows"))]


def loss_matrix(run):
    run=Path(run);panel,filings,c=prepared(run);files=sorted(run.glob("tasks/core-*/losses.npz"));names=[];blocks=[];indicators=[];seen=set()
    if not all(done(run,f"core-{i:03d}") for i in range(len(cells(c)))):raise ValueError("Joint family requires all declared core tasks terminal and verified")
    for file in files:
        with np.load(file,allow_pickle=False) as a:
            for name in sorted(k[:-5] for k in a.files if k.endswith("_rows")):
                if name in seen:raise ValueError("Duplicate scientific comparison ID")
                seen.add(name)
                column=len(names);names.append(name);r=a[name+"_rows"];v=a[name+"_values"]
                blocks.append(sparse.csc_matrix((v,(r,np.zeros(len(r),dtype=int))),shape=(len(panel),1)))
                indicators.append(sparse.csc_matrix((np.ones(len(r)),(r,np.zeros(len(r),dtype=int))),shape=(len(panel),1)))
    matrix=sparse.hstack(blocks,format="csr") if blocks else sparse.csr_matrix((len(panel),0))
    indicator=sparse.hstack(indicators,format="csr") if indicators else matrix.copy()
    return panel,c,names,matrix,indicator


def placebo_summary(run):
    scheduled();run=Path(run);panel,filings,c=prepared(run);maxima=[];main=[]
    for i in range(len(cells(c))):
        if not done(run,f"core-{i:03d}"):raise ValueError("Main search incomplete")
        for p in (run/"tasks"/f"core-{i:03d}").glob("*/search-scores.json"):main.extend(read_json(p))
    for replica in range(c["placebos"]):
        values=[]
        for i in range(len(cells(c))):
            if not done(run,f"placebo-{replica:03d}-{i:03d}"):raise ValueError("Full placebo search incomplete")
            for p in (run/"tasks"/f"placebo-{replica:03d}-{i:03d}").glob("*/search-scores.json"):values.extend(x["score"] for x in read_json(p) if x["score"] is not None)
        maxima.append({"replica":replica,"maximum":max(values,default=None),"tested_cells":len(values)})
    finite=np.array([x["maximum"] for x in maxima if x["maximum"] is not None])
    results=[{**x,"full_search_placebo_p":(1+int((finite>=x["score"]).sum()))/(1+len(finite)) if x["score"] is not None and len(finite)==c["placebos"] else None,
        "status":"diagnostic_exchangeability_assumed","replicas":len(finite)} for x in main]
    write_table(run/"outputs/placebo-maxima.csv",maxima);write_table(run/"outputs/placebo-comparisons.csv",results)
    receipt(run,"placebo-summary",[run/"outputs/placebo-maxima.csv",run/"outputs/placebo-comparisons.csv"])


def resampling(run,batch,block):
    scheduled();run=Path(run);label=f"resample-{block}-{batch:03d}"
    if done(run,label):return
    panel,c,names,values,indicator=loss_matrix(run);start=batch*c["resample_batch"];end=min(c["resamples"],start+c["resample_batch"])
    result=np.full((end-start,len(names)),np.nan);base=panel.weight.to_numpy()
    for offset,b in enumerate(range(start,end)):
        rng=np.random.default_rng(c["seed"]+block*1000000+b)
        w=base*joint_weights(panel.issuer.to_numpy(),panel.session.to_numpy(),block,rng)
        num=np.asarray(values.T@w).ravel();den=np.asarray(indicator.T@w).ravel();result[offset]=np.divide(num,den,out=np.full(len(names),np.nan),where=den>0)
    folder=run/"uncertainty";folder.mkdir(exist_ok=True);p=folder/(label+".npz");np.savez_compressed(p,draws=result,names=np.array(names))
    receipt(run,label,[p],extra={"start":start,"end":end,"block":block})


def inference(run):
    scheduled();run=Path(run);panel,c,names,values,indicator=loss_matrix(run);weight=panel.weight.to_numpy()
    numerator=np.asarray(values.T@weight).ravel();denominator=np.asarray(indicator.T@weight).ravel()
    point=np.divide(numerator,denominator,out=np.full(len(names),np.nan),where=denominator>0);results=[]
    for block in c["block_lengths"]:
        expected=int(np.ceil(c["resamples"]/c["resample_batch"]));arrays=[]
        for batch in range(expected):
            label=f"resample-{block}-{batch:03d}"
            if not done(run,label):raise ValueError("Joint inference is incomplete; preserve partial results")
            with np.load(run/"uncertainty"/(label+".npz"),allow_pickle=False) as a:
                if list(a["names"])!=names:raise ValueError("Joint family ordering changed")
                arrays.append(a["draws"])
        draws=np.vstack(arrays);sd=np.nanstd(draws,axis=0,ddof=1);valid=np.isfinite(point)&(sd>0)&np.isfinite(draws).all(axis=0)
        p=np.full(len(names),np.nan)
        if valid.any():p[valid]=romano_wolf(point[valid]/sd[valid],(draws[:,valid]-point[valid])/sd[valid])
        for i,name in enumerate(names):
            lo,hi=np.nanquantile(draws[:,i],[.025,.975]) if np.isfinite(draws[:,i]).any() else (np.nan,np.nan)
            results.append({"comparison_id":name,"block_sessions":block,"estimate":point[i],"pointwise_lower":lo,"pointwise_upper":hi,
                "romano_wolf_p":p[i],"resamples":len(draws),"family_size":len(names),"inference_status":"approximate_exploratory" if valid[i] else "unsupported"})
    write_table(run/"outputs/inference.csv",results);receipt(run,"inference",[run/"outputs/inference.csv"])


def render_atlas(run,complete=False):
    scheduled();run=Path(run);m=manifest(run);coverage_rows=pd.read_csv(run/"outputs/coverage.csv").to_dict("records")
    core_states={f"core-{i:03d}":"completed" if done(run,f"core-{i:03d}") else "pending_or_failed" for i in range(len(cells(m["settings"]))) }
    complete=all(v=="completed" for v in core_states.values()) and done(run,"inference") and done(run,"placebo-summary") and done(run,"options")
    if done(run,"options"):
        panel,filings,c=prepared(run);option_values=np.load(run/"outputs/option-inputs.npy",allow_pickle=False);days=len(sessions_from_panel(panel))
        for row in coverage_rows:
            base={i for f in filings if row["category"] in f["categories"] for i in f["rows"]}
            for lag in c["lags"]:
                indices=[i+lag for i in base if i%days+lag<days];covered=[i for i in indices if np.isfinite(option_values[i]).all()]
                row["option_complete_input_"+str(lag)]=len(panel.iloc[covered][["issuer","date"]].drop_duplicates())
            row["option_status"]="available_subset" if any(row["option_complete_input_"+str(lag)] for lag in c["lags"]) else "unavailable_or_incomplete"
    comparisons=[];trial_frames=[];failures=[]
    for p in sorted(run.glob("tasks/core-*/comparisons.csv")):
        try:comparisons.extend(pd.read_csv(p).to_dict("records"))
        except pd.errors.EmptyDataError:pass
    for p in sorted(run.glob("tasks/core-*/trials.csv")):
        try:trial_frames.append(pd.read_csv(p))
        except pd.errors.EmptyDataError:pass
    inference_rows=pd.read_csv(run/"outputs/inference.csv").to_dict("records") if done(run,"inference") else []
    inferred={(r["comparison_id"],r["block_sessions"]):r for r in inference_rows}
    for x in comparisons:
        for block in m["settings"]["block_lengths"]:
            value=inferred.get((x["comparison_id"],block))
            if value:
                for name in ["romano_wolf_p","pointwise_lower","pointwise_upper"]:x[name+"_"+str(block)]=value[name]
    measured=[x for x in comparisons if x.get("status")=="measured"]
    for row in coverage_rows:
        reads=[x for x in measured if x.get("pattern")=="tag:"+row["category"]]
        row["measured_forecast_cells"]=len(reads);row["evidence_status"]="exploratory_measured" if reads else "coverage_only_or_unsupported"
        row["supported_fold_cells"]=len(reads)
        row["unsupported_fold_cells"]=sum(x.get("pattern")=="tag:"+row["category"] and x.get("status")=="unsupported" for x in comparisons)
        row["adjusted_p_min_63"]=min([x["romano_wolf_p_63"] for x in reads if pd.notna(x.get("romano_wolf_p_63"))],default=None)
        row["adjusted_p_min_126"]=min([x["romano_wolf_p_126"] for x in reads if pd.notna(x.get("romano_wolf_p_126"))],default=None)
        row["response_mean_min"]=min([x["response_mean"] for x in reads if pd.notna(x.get("response_mean"))],default=None)
        row["response_mean_max"]=max([x["response_mean"] for x in reads if pd.notna(x.get("response_mean"))],default=None)
        row["forecast_improvement_min"]=min([x["event_improvement"] for x in reads if pd.notna(x.get("event_improvement"))],default=None)
        row["forecast_improvement_max"]=max([x["event_improvement"] for x in reads if pd.notna(x.get("event_improvement"))],default=None)
        row["summary_scope"]="Ranges span different declared units/settings; inspect individual horizon/delay cells before interpretation"
    write_table(run/"outputs/master.csv",coverage_rows);write_table(run/"outputs/comparisons.csv",comparisons)
    if trial_frames:pd.concat(trial_frames,ignore_index=True).to_csv(run/"outputs/trials.csv",index=False)
    columns=["category","primary_category","filings","issuers","filings_2022","filings_2023","filings_2024","filings_2025","complete_stock_outcomes_5","measured_forecast_cells","evidence_status","option_status"]
    rows=''.join('<tr>'+''.join('<td>'+html.escape(str(r.get(k,"")))+'</td>' for k in columns)+'</tr>' for r in coverage_rows)
    page='''<!doctype html><html><head><meta charset="utf-8"><title>Massive Disclosure Research Atlas</title><style>body{font:15px system-ui;margin:32px;color:#172338;background:#f6f8fc}input,select{padding:10px;margin:8px;border:1px solid #ccd3df;border-radius:6px}table{border-collapse:collapse;background:white;width:100%}th,td{padding:9px;border-bottom:1px solid #dfe4ed;text-align:left}th{position:sticky;top:0;background:#172338;color:white}a{color:#126cab}.scroll{overflow:auto}small{color:#526075}</style></head><body><h1>Massive Disclosure Research Atlas</h1><p>All 119 categories · supplied 100 tickers · 2022–2025 · exploratory research</p><p>STATUS_TEXT</p><p>Retrospective labels and static universe. Previously exposed research remains exposed. No trading simulation or alpha claim.</p><input id="search" placeholder="Filter category or domain"><select id="status"><option value="">All evidence statuses</option><option>coverage_only_or_unsupported</option><option>exploratory_measured</option></select><p><a href="master.csv">Master CSV</a> · <a href="comparisons.csv">Horizon/delay and forecast comparisons</a> · <a href="patterns.csv">Combinations and sequences</a> · <a href="inference.csv">Joint uncertainty</a> · <a href="quality.json">Source limitations</a></p><div class="scroll"><table><thead><tr>HEADERS</tr></thead><tbody id="masterrows">ROWS</tbody></table></div><script>function filter(){let q=document.querySelector('#search').value.toLowerCase(),s=document.querySelector('#status').value;for(let r of document.querySelectorAll('#masterrows tr'))r.hidden=!r.textContent.toLowerCase().includes(q)||(s&&!r.textContent.includes(s));}document.querySelector('#search').oninput=filter;document.querySelector('#status').onchange=filter;</script></body></html>'''
    page=page.replace("STATUS_TEXT","Complete planned scientific stages, pending independent confirmation." if complete else "Partial staged atlas: remaining planned stages are pending.")
    page=page.replace("HEADERS",''.join('<th>'+html.escape(k)+'</th>' for k in columns)).replace("ROWS",rows)
    (run/"outputs/atlas.html").write_text(page,encoding="utf-8")
    summary={"manifest_id":m["manifest_id"],"categories":len(coverage_rows),"comparisons":len(comparisons),"measured":len(measured),
             "complete":complete,"alpha_claim":False,"generated_at":now(),"pending":[stage for stage in ["patterns","inference"] if not done(run,stage)]}
    summary["core_task_states"]=core_states
    summary["pending"]+=[s for s in ["placebo-summary","options"] if not done(run,s)]
    # Cell-level filters expose outcome, horizon, delay and support without
    # presenting a discovery ranking as a confirmation verdict.
    safe=pd.DataFrame(comparisons).replace({np.nan:None}).to_dict("records") if comparisons else []
    payload=json.dumps(safe,default=str).replace("</","<\\/")
    detail='''<h2>Declared comparisons</h2><p>Raw outcomes and forecast loss improvements use different units. All relationships remain development discoveries.</p><input id="cellsearch" placeholder="Category or sequence"><select id="kind"><option value="">Every outcome</option><option>return</option><option>absolute</option><option>volatility</option><option>downside</option><option>premium_30</option><option>premium_60</option><option>premium_120</option></select><select id="horizon"><option value="">Every horizon</option>HORIZONS</select><select id="lag"><option value="">Every delay</option>LAGS</select><input id="minimum" type="number" min="0" value="0" aria-label="Minimum validation activations"><select id="cellstatus"><option value="">Every status</option><option>measured</option><option>unsupported</option><option>failed</option></select><p id="count"></p><div class="scroll"><table><thead><tr><th>Pattern</th><th>Outcome</th><th>Horizon/delay</th><th>Year</th><th>Group</th><th>Activations/issuers</th><th>Response</th><th>Loss improvement</th><th>Adjusted p 63/126</th><th>Status</th></tr></thead><tbody id="cells"></tbody></table></div><script>const data=PAYLOAD;function esc(v){let t=document.createElement('span');t.textContent=v??'';return t.innerHTML;}function showCells(){const q=document.querySelector('#cellsearch').value.toLowerCase(),k=document.querySelector('#kind').value,h=document.querySelector('#horizon').value,l=document.querySelector('#lag').value,s=document.querySelector('#cellstatus').value,n=Number(document.querySelector('#minimum').value);let a=data.filter(r=>(!q||String(r.pattern||r.group).toLowerCase().includes(q))&&(!k||r.kind===k)&&(!h||String(r.horizon)===h)&&(!l||String(r.lag)===l)&&(!s||r.status===s)&&Number(r.validation_activations||0)>=n);document.querySelector('#count').textContent=a.length+' cells; displaying up to 500. The CSV retains every cell.';document.querySelector('#cells').innerHTML=a.slice(0,500).map(r=>'<tr>'+[r.pattern||'Global',r.kind,r.horizon+'/'+r.lag,r.year,r.group,(r.validation_activations??'')+'/'+(r.validation_issuers??''),r.response_mean,r.event_improvement??r.mse_improvement,(r.romano_wolf_p_63??'pending')+'/'+(r.romano_wolf_p_126??'pending'),r.status].map(v=>'<td>'+esc(v)+'</td>').join('')+'</tr>').join('');}for(const id of ['cellsearch','kind','horizon','lag','minimum','cellstatus'])document.getElementById(id).oninput=showCells;showCells();</script>'''
    detail=detail.replace("HORIZONS",''.join(f'<option>{h}</option>' for h in m["settings"]["horizons"])).replace("LAGS",''.join(f'<option>{lag}</option>' for lag in m["settings"]["lags"])).replace("PAYLOAD",payload)
    page=page.replace('</body>',detail+'</body>')
    (run/"outputs/atlas.html").write_text(page,encoding="utf-8")
    write_json(run/"outputs/summary.json",summary)
    receipt(run,"report",[run/"outputs"/n for n in ["master.csv","comparisons.csv","atlas.html","summary.json"]])


def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=["manifest","coverage","option-requests","patterns","core","pilot","placebo","placebo-summary","resample","inference","report"])
    p.add_argument("--run",required=True);p.add_argument("--source");p.add_argument("--options");p.add_argument("--task",type=int,default=0);p.add_argument("--replica",type=int);p.add_argument("--block",type=int,default=63)
    a=p.parse_args()
    if a.action=="manifest":create_manifest(a.source,a.run,a.options)
    elif a.action=="coverage":coverage(a.run)
    elif a.action=="option-requests":option_requests(a.run)
    elif a.action=="patterns":patterns(a.run)
    elif a.action in ("core","pilot"):core(a.run,a.task,pilot=a.action=="pilot")
    elif a.action=="placebo":placebo_batch(a.run,a.replica,a.task,a.task+1)
    elif a.action=="placebo-summary":placebo_summary(a.run)
    elif a.action=="resample":resampling(a.run,a.task,a.block)
    elif a.action=="inference":inference(a.run)
    elif a.action=="report":render_atlas(a.run)


if __name__=="__main__":
    try:main()
    except Exception as error:
        # Failed attempts remain separate from completed immutable checkpoints.
        if os.getenv("SLURM_JOB_ID"):
            arguments=list(__import__('sys').argv)
            if '--run' in arguments:
                failed_run=Path(arguments[arguments.index('--run')+1])
                failure={"state":"failed","finished_at":now(),"slurm_job_id":os.getenv('SLURM_JOB_ID'),
                    "slurm_array_task_id":os.getenv('SLURM_ARRAY_TASK_ID'),"arguments":arguments[1:],
                    "exception":type(error).__name__,"reason":str(error)}
                name=identity(failure)
                write_json(failed_run/'attempts'/(name+'.json'),failure)
        raise
