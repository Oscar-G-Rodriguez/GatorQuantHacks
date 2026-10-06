"""Event response, component contrasts and strictly prior ordinary comparisons."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from .atlas_features import CONTROLS, eligible_columns
from .atlas_statistics import outer_masks, support
from .io import identity


def matched_values(panel, train, test, event, forbidden, horizon, target, maximum=5, return_matches=False):
    """No later observations, outcome overlap, or future state enter matching."""
    names=["return20","vol20","log_adv20"]
    if not np.any(train):return {} if return_matches else np.full(len(panel),np.nan)
    values=panel[names].to_numpy(); center=np.nanmean(values[train],axis=0)
    scale=np.nanstd(values[train],axis=0);scale[scale==0]=1
    x=(values-center)/scale;y=panel[target].to_numpy();out=np.full(len(panel),np.nan);matches={}
    session=panel.session.to_numpy();end=panel[f"target_end_{horizon}"].to_numpy();dates=panel.date.to_numpy()
    complete=np.isfinite(y)&np.isfinite(x).all(axis=1)
    for issuer, frame in panel.groupby("issuer",sort=False):
        indices=frame.index.to_numpy()
        # One market observation per issuer/date; average later with issuer weights.
        candidate=indices[complete[indices]&~forbidden[indices]]
        for i in indices[test[indices]&event[indices]]:
            allowed=candidate[(session[candidate]<session[i])&(session[candidate]>=session[i]-252)&(end[candidate]<dates[i])]
            if not len(allowed):continue
            distance=np.sum((x[allowed]-x[i])**2,axis=1)
            ordered=allowed[np.lexsort((allowed,distance))]; chosen=[]
            for j in ordered:
                if all(abs(int(session[j])-int(session[k]))>horizon for k in chosen):chosen.append(j)
                if len(chosen)==maximum:break
            if chosen:
                out[i]=y[i]-float(np.average(y[chosen],weights=panel.weight.to_numpy()[chosen]));matches[int(i)]=[int(j) for j in chosen]
    return matches if return_matches else out


def response_cell(panel, patterns, active, catalog, config, horizon, lag, kind):
    target=f"{kind}_{horizon}";y=panel[target].to_numpy();w=panel.weight.to_numpy();results=[];losses=[]
    days=len(panel)//panel.ticker.nunique();forbidden=active.copy()
    for offset in range(0,len(panel),days):
        positions=np.flatnonzero(active[offset:offset+days])
        for s in positions:forbidden[offset+max(0,s-21):offset+min(days,s+22)]=True
    lookup={p["name"]:i for i,p in enumerate(catalog)}
    for year in config["fold_years"]:
        train,test=outer_masks(panel,horizon,year,target)
        ordinary=matched_values(panel,train,test,active,forbidden,horizon,target)
        allowed=set(eligible_columns(patterns,panel,train,config))
        for column,entry in enumerate(catalog):
            flag=patterns[:,column].toarray().ravel()>0
            tr,va=support(panel,flag,train),support(panel,flag,test)
            base={"pattern":entry["name"],"family":entry["family"],"horizon":horizon,"lag":lag,"kind":kind,"year":year,
                  "train_activations":tr["activations"],"train_issuers":tr["issuers"],"validation_activations":va["activations"],"validation_issuers":va["issuers"]}
            valid=column in allowed and va["activations"]>=config["validation_min_activations"] and va["issuers"]>=config["validation_min_issuers"]
            rows=np.flatnonzero(test&flag)
            for mode in ["response","ordinary",*( ["component"] if entry["family"]!="tag" else [])]:
                comparison_id=identity({**base,"mode":mode});values=y.copy()
                if mode=="ordinary":values=ordinary
                if mode=="component" and valid:
                    component=np.zeros(len(panel),bool)
                    for cat in entry["members"]:component|=patterns[:,lookup["tag:"+cat]].toarray().ravel()>0
                    # Past component events matched to prior state, before current outcome.
                    values=matched_values(panel,train,test,flag,~(component&~flag),horizon,target)
                usable=rows[np.isfinite(values[rows])];sv=support(panel,np.isfinite(values)&flag,test)
                ok=valid and sv["activations"]>=config["validation_min_activations"] and sv["issuers"]>=config["validation_min_issuers"]
                results.append({**base,"comparison_id":comparison_id,"group":"response_"+mode,"status":"measured" if ok else "unsupported",
                    "matched_activations":sv["activations"],"matched_issuers":sv["issuers"],"response_mean":float(np.average(values[usable],weights=w[usable])) if ok else None,
                    "reason":None if ok else "Insufficient fold or matched issuer-date support"})
                # Raw response is descriptive, rather than a test against a zero financial mean.
                if ok and mode!="response":losses.append({"comparison_id":comparison_id,"rows":usable,"values":values[usable]})
    return results,losses
