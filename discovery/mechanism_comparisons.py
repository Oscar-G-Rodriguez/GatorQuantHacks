"""Common paired comparison accounting; objectives live in the owned studies."""
import numpy as np
import pandas as pd

from .mechanism_statistics import pair


def paired_trade(horizons, shape, cfg, delay=0, cost=1):
    f=horizons.loc[(horizons["horizon"]==cfg["primary_filing_horizon"]) & (horizons.status=="measured")
                   & (horizons.delay==delay) & (horizons.cost_multiplier==cost)].copy()
    keys=["anchor_id","event_id","issuer","cohort","filing_date","filing_session","delay","bucket","otm"]
    s=f.loc[f["shape"]==shape];l=f.loc[f["shape"]=="synthetic_long"]
    common=s.merge(l,on=keys,suffixes=("_shape","_long"),validate="one_to_one")
    result=common[keys].copy()
    if common.empty:
        # An all-unmeasured window may have no payoff columns at all. Preserve
        # an empty comparison, never synthesize a zero return or relax a fill.
        for column in ["increment","shape_return","long_return","collateral_return"]:
            result[column]=pd.Series(index=result.index,dtype=float)
        return result,pair(result,["increment","shape_return","long_return","collateral_return"])
    result["increment"]=common.stock_notional_return_shape-common.stock_notional_return_long
    result["shape_return"]=common.stock_notional_return_shape
    result["long_return"]=common.stock_notional_return_long
    result["collateral_return"]=common.collateral_return_shape
    return result,pair(result,["increment","shape_return","long_return","collateral_return"])


def tail(frame):
    if frame.empty:return {"status":"inconclusive","reason":"no_common_quote_trades"}
    f=frame.dropna(subset=["shape_return","long_return"])
    if len(f)<10:return {"status":"inconclusive","reason":"fewer_than_ten_common_returns","observations":len(f)}
    n=max(1,int(np.ceil(.1*len(f))))
    a=float(f.shape_return.nsmallest(n).mean()); b=float(f.long_return.nsmallest(n).mean())
    return {"status":"measured","observations":len(f),"worst_decile_count":n,
            "shape_worst_decile_mean":a,"long_worst_decile_mean":b,
            "tail_loss_reduction":(a-b)/abs(b) if b<0 else None,
            "mean_return_drag":float((f.long_return-f.shape_return).mean()),
            "q10_shape":float(f.shape_return.quantile(.1)),"q10_long":float(f.long_return.quantile(.1))}
