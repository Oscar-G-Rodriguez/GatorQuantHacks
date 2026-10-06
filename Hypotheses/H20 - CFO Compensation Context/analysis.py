"""H20: verified incoming-CFO terms, RMS and fully collateralized put objective."""
import pandas as pd
from discovery.mechanism_statistics import infer, chronological

TARGET="rms"


def evaluate(features,horizons,cfg):
    selected=features.loc[(features.delay==0)&(features.bucket==cfg["primary_bucket"])&(features.otm==cfg["primary_otm"])&(features.cohort=="event")].copy()
    labels=["verified_incoming_cfo_terms","verified_absence_in_complete_filing"]
    verified=selected.loc[selected.classification.isin(labels)].copy() if "classification" in selected else selected.iloc[:0]
    verified=verified.dropna(subset=["rms","uncertainty","momentum","early_downside"])
    groups={label:{"events":int((verified.classification==label).sum()),
                   "issuers":int(verified.loc[verified.classification==label,"issuer"].nunique())} for label in labels}
    support=all(g["events"]>=cfg["minimum_h20_group_events"] and g["issuers"]>=cfg["minimum_h20_group_issuers"] for g in groups.values())
    mechanism={"status":"inconclusive","reason":"verified_group_support","groups":groups}
    trade={"status":"inconclusive","reason":"verified_group_support","groups":groups}
    double_mean=None
    tail_met=False
    if support:
        controls=["verified_terms","uncertainty","momentum","earnings","guidance","debt"]
        # Include issuer effects only when every coefficient has registered support.
        effects=pd.get_dummies(verified.issuer,prefix="issuer",drop_first=True,dtype=float)
        if len(verified)>=2*(len(controls)+len(effects.columns)+1):
            verified=pd.concat([verified,effects],axis=1);controls+=list(effects.columns)
        mechanism=infer(verified,TARGET,cfg,controls,parameter=1)
        primary=horizons.loc[(horizons["shape"]=="cash_secured_put")&(horizons.horizon==5)&(horizons.delay==0)
                             &(horizons.cost_multiplier==1)&(horizons.status=="measured")]
        f=primary.merge(verified[["event_id","verified_terms"]],on="event_id",validate="many_to_one")
        ordinary=f.loc[f.cohort=="ordinary",["event_id","collateral_return"]].rename(columns={"collateral_return":"ordinary_return"})
        event=f.loc[f.cohort=="event"].merge(ordinary,on="event_id",validate="one_to_one")
        event["increment"]=event.collateral_return-event.ordinary_return
        usable=event.dropna(subset=["increment","verified_terms"])
        enough=all(len(usable.loc[usable.verified_terms==g])>=cfg["minimum_h20_group_events"]
                   and usable.loc[usable.verified_terms==g,"issuer"].nunique()>=cfg["minimum_h20_group_issuers"] for g in [0.,1.])
        trade=infer(usable,"increment",cfg,["verified_terms"],parameter=1) if enough else {"status":"inconclusive","reason":"insufficient_complete_group_trade_pairs"}
        tails={}
        for group in [0.,1.]:
            values=event.loc[event.verified_terms==group,"collateral_return"].dropna()
            if len(values)>=8:
                tails[group]=float(values.nsmallest(max(1,int(__import__("math").ceil(.1*len(values))))).mean())
        tail_met=set(tails)=={0.,1.} and tails[1.]>=tails[0.]
        doubled=horizons.loc[(horizons["shape"]=="cash_secured_put")&(horizons.horizon==5)&(horizons.delay==0)
                              &(horizons.cost_multiplier==2)&(horizons.status=="measured")&(horizons.cohort=="event")]
        doubled=doubled.merge(verified[["event_id","verified_terms"]],on="event_id",validate="one_to_one")
        means=doubled.groupby("verified_terms").collateral_return.mean()
        double_mean=float(means[1]-means[0]) if set(means.index)=={0.,1.} else None
    secondary={}
    for proxy in ["compensation_cotag","text_terms_proxy"]:
        secondary[proxy]=infer(selected,TARGET,cfg,[proxy,"uncertainty","momentum"],parameter=1,primary=False)
    folds=chronological(verified,TARGET,["uncertainty","momentum"],["uncertainty","momentum","verified_terms","earnings","guidance","debt"],cfg)
    # Downside group evidence is mandatory, even with a negative RMS coefficient.
    downside=False
    if support and "early_downside" in verified:
        means=verified.groupby("verified_terms").early_downside.mean()
        downside=set(means.index)=={0.,1.} and means[1]<=means[0]
    return dict(mechanism=mechanism,trade=trade,secondary_proxies=secondary,groups=groups,
                doubled_cost_mean=double_mean,primary_group_support=support,
                mechanism_direction_met=mechanism.get("ci_high",float("inf"))<cfg["criteria"]["H20"]["rms_coefficient_upper_bound"] and downside,
                trade_direction_met=trade.get("ci_low",float("-inf"))>cfg["criteria"]["H20"]["net_collateral_increment_lower_bound"]
                                    and double_mean is not None and double_mean>0 and tail_met,
                prediction_folds=folds,objective="verified incoming-person terms; lower RMS and net collateral-return contrast")
