"""Manifest-verified compute-node runners and honest evidence assembly."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import subprocess
import traceback

import numpy as np
import pandas as pd

from .io import ROOT, digest, identity, now, read_json, safe_child, write_json
from .mechanism_data import CONFIG, FOLDERS, REGISTRATION, settings
from .mechanism_accounting import Sources, Ledger
from .mechanism_engine import replay
from .mechanism_features import build, classification
from .mechanism_statistics import pair, infer, train_prediction, evaluate_prediction


def clean(value):
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [clean(v) for v in value]
    if isinstance(value,np.generic):return clean(value.item())
    if isinstance(value,float) and not math.isfinite(value):return None
    return value


def code_files():
    names={"pyproject.toml","uv.lock",".python-version","discovery/__init__.py","discovery/io.py",
           "config/mechanism-round1.json","config/discovery-development.json"}
    names|={p.relative_to(ROOT).as_posix() for p in (ROOT/"discovery").glob("mechanism_*.py")}
    names|={p.relative_to(ROOT).as_posix() for p in (ROOT/"tests").glob("test_mechanism*.py")}
    # The root editable package declares both libraries and this metadata file.
    # They must be present even though the offline ledger does not call Webull.
    names|={p.relative_to(ROOT).as_posix() for p in (ROOT/"webull_bt").rglob("*.py")}
    names.add("docs/README.md")
    for folder in FOLDERS.values():
        names|={p.relative_to(ROOT).as_posix() for p in (ROOT/"Hypotheses"/folder).rglob("*.py") if "data" not in p.parts}
    return {n:digest(ROOT/n) for n in sorted(names)}


def create_manifest(source_folder,run,reviews=None,freeze=None):
    source_folder=Path(source_folder).resolve();run=Path(run).resolve()
    source=read_json(source_folder/"source.json")
    if not source.get("complete"):raise ValueError("Acquisition incomplete")
    if source["config_sha256"]!=digest(CONFIG):raise ValueError("Source configuration changed")
    if (run/"manifest.json").exists():raise ValueError("Manifest already exists; preserve the prior attempt")
    codes=code_files()
    if source["phase"] in ["final-oos","sealed"]:
        if freeze is None:raise ValueError("Frozen development evidence required")
        locked=read_json(freeze)
        if locked["code_files"]!=codes:raise ValueError("Scientific code differs from frozen development package")
    inputs={(source_folder/"source.json").relative_to(ROOT).as_posix():digest(source_folder/"source.json")}
    for rid,r in source["objects"].items():
        p=source_folder/"raw"/(rid+".json")
        if digest(p)!=r["sha256"]:raise ValueError("Changed source object")
        inputs[p.relative_to(ROOT).as_posix()]=r["sha256"]
    # Failure/exposure receipts are evidence, not invisible operational history.
    receipts=list(source_folder.glob("download-*.json"))+list((source_folder/"checkpoints").glob("*.json"))
    receipts+=list((source_folder/"raw"/"attempts").glob("*/receipt.json"))
    receipts+=list((source_folder/"filings").glob("*.json"))
    if (source_folder/"FINAL-EXPOSURE.json").exists():receipts.append(source_folder/"FINAL-EXPOSURE.json")
    for p in receipts:inputs[p.relative_to(ROOT).as_posix()]=digest(p)
    review_path=Path(reviews).resolve() if reviews else source_folder/"cfo-reviews.json"
    if not review_path.exists():write_json(review_path,{"schema":1,"created_at":now(),"outcome_blind":True,"reviews":{},
                                                              "reason":"No complete reviewed evidence supplied; excerpts cannot establish absence"})
    rv=read_json(review_path)
    if rv.get("outcome_blind") is not True:raise ValueError("Review must precede outcome calculation")
    for anchor in source["anchors"]:classification(anchor,rv["reviews"])
    inputs[review_path.relative_to(ROOT).as_posix()]=digest(review_path)
    if freeze:inputs[Path(freeze).resolve().relative_to(ROOT).as_posix()]=digest(freeze)
    prediction_files={}
    if freeze:
        locked=read_json(freeze)
        for study,record in locked["prediction_files"].items():
            if digest(ROOT/record["path"])!=record["sha256"]:raise ValueError("Frozen prediction model differs")
            inputs[record["path"]]=record["sha256"];prediction_files[study]=record["path"]
    git_result=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True)
    manifest={"schema":1,"created_at":now(),"registration_commit":REGISTRATION,"phase":source["phase"],
              "code_commit":git_result.stdout.strip() if git_result.returncode==0 else None,
              "window":source["window"],"source_folder":source_folder.relative_to(ROOT).as_posix(),
              "reviews_file":review_path.relative_to(ROOT).as_posix(),"hypotheses":list(FOLDERS),
              "config_sha256":digest(CONFIG),"code_files":codes,"input_files":inputs,
              "freeze_sha256":digest(freeze) if freeze else None}
    manifest["prediction_files"]=prediction_files
    manifest["manifest_id"]=identity(manifest)
    write_json(run/"manifest.json",manifest)
    return {"manifest_id":manifest["manifest_id"],"files":len(inputs),"phase":source["phase"]}


def verify(run):
    manifest=read_json(Path(run)/"manifest.json")
    base={k:v for k,v in manifest.items() if k!="manifest_id"}
    if identity(base)!=manifest["manifest_id"]:raise ValueError("Manifest identity differs")
    for name,expected in {**manifest["code_files"],**manifest["input_files"]}.items():
        if digest(safe_child(ROOT,name))!=expected:raise ValueError("Frozen file changed: "+name)
    return manifest


def load(study,module):
    path=ROOT/"Hypotheses"/FOLDERS[study]/(module+".py")
    spec=importlib.util.spec_from_file_location(study+"_"+module,path)
    instance=importlib.util.module_from_spec(spec);sys.modules[spec.name]=instance
    spec.loader.exec_module(instance)
    return instance


def require_compute():
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Real-data analysis/replay must run inside an allocated HiPerGator Slurm job")


def run_study(run,study):
    require_compute();run=Path(run);m=verify(run);cfg=settings()
    out=run/"tasks"/study
    if out.exists():raise ValueError("Existing task evidence cannot be overwritten")
    out.mkdir(parents=True)
    write_json(out/"attempt.json",{"started_at":now(),"slurm_job_id":os.environ["SLURM_JOB_ID"],
                                  "host":os.environ.get("HOSTNAME"),"manifest_id":m["manifest_id"]})
    try:
        sources=Sources(ROOT/m["source_folder"])
        strategy=load(study,"strategy");analysis=load(study,"analysis")
        reviews=read_json(ROOT/m["reviews_file"])["reviews"]
        anchors,features,horizons,capacity=build(sources,strategy.CATEGORY,strategy.SHAPE,reviews)
        features.to_csv(out/"signal_diagnostics.csv",index=False)
        horizons.to_csv(out/"horizon_comparison.csv",index=False)
        capacity.to_csv(out/"capacity.csv",index=False)
        findings=analysis.evaluate(features,horizons,cfg)
        prediction_frame=features.loc[(features.delay==0)&(features.bucket==cfg["primary_bucket"])&(features.otm==cfg["primary_otm"])
                                      &(features.cohort=="event")].copy()
        if study=="H20":
            prediction_frame=prediction_frame.loc[prediction_frame.classification.isin(["verified_incoming_cfo_terms","verified_absence_in_complete_filing"])]
            if not findings.get("primary_group_support",False):prediction_frame=prediction_frame.iloc[:0]
        if study=="H19":prediction_frame["target_end"]=prediction_frame.concentration_target_end
        if m["phase"]=="development":
            model=train_prediction(prediction_frame,analysis.TARGET,cfg)
            write_json(out/"prediction-model.json",clean(model))
        else:
            model=read_json(ROOT/m["prediction_files"][study])
            findings["final_prediction"]=evaluate_prediction(prediction_frame,model)
            write_json(out/"final-prediction.json",clean(findings["final_prediction"]))
        robustness=[]
        for (delay,bucket,otm),f in features.groupby(["delay","bucket","otm"],sort=True):
            target=analysis.TARGET
            if study=="H20":
                chosen=f.loc[(f.cohort=="event") & f.classification.isin(["verified_incoming_cfo_terms","verified_absence_in_complete_filing"])]
                result=infer(chosen,target,cfg,["verified_terms"],parameter=1,primary=False)
            else:result=infer(pair(f,[target]),target,cfg,primary=False)
            robustness.append({"kind":"neighbor_mark_mechanism","delay":delay,"bucket":bucket,"otm":otm,**result})
        for year in [2024,2025,2026]:
            f=features.loc[(features.delay==0)&(features.bucket==cfg["primary_bucket"])&(features.otm==cfg["primary_otm"])
                          & features.filing_date.fillna("").str.startswith(str(year))]
            if study!="H20":result=infer(pair(f,[analysis.TARGET]),analysis.TARGET,cfg,primary=False)
            else:result={"status":"inconclusive","reason":"verified-group primary remains governed by full support"}
            robustness.append({"kind":"year", "year":year,**result})
        # Fixed shock/quiet threshold (.02 past daily RMS), using past marks only.
        for state in ["quiet","shock"]:
            f=features.loc[(features.delay==0)&(features.bucket==cfg["primary_bucket"])&(features.otm==cfg["primary_otm"])
                          & features.past_move_rms.notna()]
            f=f.loc[f.past_move_rms>=.02] if state=="shock" else f.loc[f.past_move_rms<.02]
            robustness.append({"kind":"past_state","state":state,"status":"measured" if len(f) else "inconclusive",
                               "observations":len(f),"mean_target":f[analysis.TARGET].mean()})
        pd.DataFrame(robustness).to_csv(out/"robustness.csv",index=False)
        pd.DataFrame(findings["prediction_folds"]).to_csv(out/"prediction_folds.csv",index=False)
        metrics=[];curves=[];audits=[];closed=[]
        for delay in cfg["decision_delays"]:
            for costs in cfg["cost_multipliers"]:
                for baseline in ["registered_shape","funded_long","ordinary_shape","price_only","cash","all_events_shape"]:
                    if baseline=="all_events_shape" and study!="H20":continue
                    cohort="ordinary" if baseline=="ordinary_shape" else "event"
                    shape="synthetic_long" if baseline=="funded_long" else "cash" if baseline=="cash" else strategy.SHAPE
                    eligible=lambda a:(strategy.eligible(a,reviews) and (study!="H20" or findings.get("primary_group_support",False))) if baseline=="registered_shape" else True
                    def price_shape(a):
                        v=a["variants"].get(str(delay),{});s=v.get("selected",{}).get(cfg["primary_bucket"])
                        if not s:return "cash"
                        di=sources.index[v["decision_date"]]
                        past=sources.spot(s,sources.dates[di-5]) if di>=5 else None
                        last=sources.spot(s,v["decision_date"])
                        if past and last and last>past:return strategy.SHAPE
                        return "synthetic_long" if study in ["H18","H19"] else "cash"
                    ledger=Ledger(sources,anchors,shape,delay=delay,cost_multiplier=costs,cohort=cohort,
                                  predicate=eligible,shape_for=price_shape if baseline=="price_only" else None)
                    result=replay(strategy.Strategy,ledger,sources.dates)
                    tags={"baseline":baseline,"study":study,"delay":delay,"cost_multiplier":costs}
                    metrics.append({**tags,**result["metrics"]})
                    curves.extend({**tags,**r} for r in result["nav"])
                    audits.extend({**tags,**r} for r in result["execution_audit"])
                    closed.extend({**tags,**r} for r in result["closed_trades"])
                    for p in result["unresolved_positions"]:audits.append({**tags,"action":"open_at_cutoff",**p})
        pd.DataFrame(metrics).to_csv(out/"metrics.csv",index=False)
        pd.DataFrame(metrics).to_csv(out/"baseline_comparison.csv",index=False)
        pd.DataFrame(curves).to_csv(out/"equity_curves.csv",index=False)
        write_json(out/"execution_audit.json",clean(audits))
        pd.DataFrame(closed).to_csv(out/"closed_trades.csv",index=False)
        # A measured conditional mechanism never overrides missing historical clock,
        # assignment/dividend evidence or incomplete broad-exposure attribution.
        findings.update(verdict="INCONCLUSIVE",verdict_reason="Historical label availability, American assignment/dividends and broad exposure validity remain unresolved",
                        phase=m["phase"],study=study,manifest_id=m["manifest_id"],category_anchors=len(anchors),
                        scientific_trials=None)
        trials=[]
        for group,cell in horizons.groupby(["shape","horizon","delay","cost_multiplier"],sort=False):
            good=cell.loc[cell.status=="measured"]
            trials.append({"kind":"fixed_horizon_quote_diagnostic","shape":group[0],"horizon":group[1],"delay":group[2],"cost_multiplier":group[3],
                           "status":"measured" if len(good) else "inconclusive","observations":len(good),
                           "missing_observations":len(cell)-len(good),"issuers":int(good.issuer.nunique()),
                           "stock_notional_mean":good.stock_notional_return.mean() if "stock_notional_return" in good else None,
                           "collateral_mean":good.collateral_return.mean() if "collateral_return" in good else None})
        trials+=robustness+[{"kind":"prediction_fold",**r} for r in findings["prediction_folds"]]
        trials+=[{"kind":"funded_portfolio",**r} for r in metrics]
        trials+=[{"kind":"primary_mechanism",**findings["mechanism"]},{"kind":"primary_trade",**findings["trade"]}]
        if "final_prediction" in findings:trials.append({"kind":"frozen_final_prediction",**findings["final_prediction"]})
        findings["scientific_trials"]=len(trials)
        pd.DataFrame(trials).to_csv(out/"trial-cells.csv",index=False)
        if findings["mechanism"].get("status")=="measured" and findings["trade"].get("status")=="measured":
            findings["conditional_result"]="direction criteria met" if findings["mechanism_direction_met"] and findings["trade_direction_met"] else "registered direction criteria not met"
        else:findings["conditional_result"]="insufficient supported primary evidence"
        checks={f"S{i:02}":{"implemented":True,"executed":True,"criterion_status":"pending","evidence":[]} for i in range(1,13)}
        reasons={"S01":"Historical vendor release, dividends and assignment unknown",
                 "S02":"Manifest/phase verified; final OOS not yet run" if m["phase"]=="development" else "Frozen final package verified; exposure history retained",
                 "S03":"Measured counts/units; primary estimator support is reported individually",
                 "S04":"All fixed horizons/settings retained, including missing outcomes",
                 "S05":"Same-unit cash/long/ordinary/price-only baselines executed",
                 "S06":"Chronological prediction fold support reported; sparse folds remain inconclusive",
                 "S07":"Own-instrument controls executed; broad factor and sector explanation incomplete",
                 "S08":"Issuer and date-block intervals/support reported; earlier search remains discovery",
                 "S09":"Ordinary/pre-filing falsification computed where marks exist; CFO absence unknown without full review",
                 "S10":"Neighbor/year/past-state and issuer-removal diagnostics retained",
                 "S11":"All-leg costs/risk ledger executed; size/impact/assignment and missing liquidation evidence may remain unresolved",
                 "S12":"Compute attempt, input/code hashes and artifacts recorded; local return/reproduction audit pending"}
        for key,reason in reasons.items():checks[key]["reason"]=reason
        for key in ["S04","S05","S10"]:checks[key]["criterion_status"]="executed"
        for key in ["S03","S08"]:checks[key]["criterion_status"]=findings["mechanism"].get("status","inconclusive")
        write_json(out/"validation_checks.json",clean(checks));write_json(out/"findings.json",clean(findings))
        write_json(out/"manifest.json",m)
        (out/"summary.md").write_text(f"# {study}: {m['phase']}\n\nVerdict: **{findings['verdict']}**. {findings['verdict_reason']}.\n\nConditional result: {findings['conditional_result']}.\n\nMechanism: `{json.dumps(clean(findings['mechanism']))}`\n\nTrade objective: `{json.dumps(clean(findings['trade']))}`\n\nThis is post-discovery research on a static survivor-selected universe. Read the complete registered protocol and retained exposure/failure history.\n",encoding="utf-8")
        write_json(out/"completion.json",{"finished_at":now(),"status":"complete","manifest_id":m["manifest_id"],
                                          "slurm_job_id":os.environ["SLURM_JOB_ID"],"files":{p.name:digest(p) for p in out.iterdir() if p.is_file()}})
        return {"study":study,"completed":True,"verdict":findings["verdict"]}
    except Exception:
        write_json(out/"failure.json",{"at":now(),"status":"failed","traceback":traceback.format_exc()})
        raise


def aggregate(run):
    require_compute();run=Path(run);m=verify(run);rows=[]
    for study in FOLDERS:
        out=run/"tasks"/study
        if not (out/"completion.json").exists():
            rows.append({"study":study,"phase":m["phase"],"status":"failed_or_missing","verdict":"INCONCLUSIVE"});continue
        f=read_json(out/"findings.json")
        rows.append({"study":study,"phase":m["phase"],"status":"complete","verdict":f["verdict"],"conditional_result":f["conditional_result"],
                     "events":f["mechanism"].get("observations"),"issuers":f["mechanism"].get("issuers"),
                     "mechanism_estimate":f["mechanism"].get("estimate"),"mechanism_ci_low":f["mechanism"].get("ci_low"),
                     "mechanism_ci_high":f["mechanism"].get("ci_high"),"trade_estimate":f["trade"].get("estimate"),
                     "trade_ci_low":f["trade"].get("ci_low"),"trade_ci_high":f["trade"].get("ci_high"),"trials":f["scientific_trials"]})
    pd.DataFrame(rows).to_csv(run/"combined-findings.csv",index=False)
    write_json(run/"aggregate.json",{"at":now(),"manifest_id":m["manifest_id"],"all_tasks_complete":all(r["status"]=="complete" for r in rows),"rows":rows})
    return rows


def main(study=None):
    p=argparse.ArgumentParser(description=__doc__)
    if study:p.add_argument("--run",type=Path,required=True)
    else:
        sub=p.add_subparsers(dest="command",required=True)
        q=sub.add_parser("manifest");q.add_argument("--source",type=Path,required=True);q.add_argument("--run",type=Path,required=True)
        q.add_argument("--reviews",type=Path);q.add_argument("--freeze",type=Path)
        q=sub.add_parser("aggregate");q.add_argument("--run",type=Path,required=True)
    a=p.parse_args()
    result=run_study(a.run,study) if study else aggregate(a.run) if a.command=="aggregate" else create_manifest(a.source,a.run,a.reviews,a.freeze)
    print(json.dumps(clean(result)))


if __name__=="__main__":main()
