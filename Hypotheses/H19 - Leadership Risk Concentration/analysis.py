"""H19: downside timing, maturity curve and paid protection objective."""
from discovery.mechanism_statistics import infer, pair, chronological
from discovery.mechanism_comparisons import paired_trade, tail

TARGET="downside_concentration"


def evaluate(features,horizons,cfg):
    selected=features.loc[(features.delay==0)&(features.bucket==cfg["primary_bucket"])&(features.otm==cfg["primary_otm"])]
    paired=pair(selected,[TARGET])
    mechanism=infer(paired,TARGET,cfg)
    rows,trades=paired_trade(horizons,"protective_put",cfg)
    trade=infer(trades,"increment",cfg)
    tails=tail(rows.loc[rows.cohort=="event"])
    delay_estimates=[]
    for delay in [1,3]:
        f=features.loc[(features.delay==delay)&(features.bucket==cfg["primary_bucket"])&(features.otm==cfg["primary_otm"])]
        delay_estimates.append(infer(pair(f,[TARGET]),TARGET,cfg,primary=False))
    keys=["event_id","cohort","delay","otm"]
    curve=features.loc[(features.bucket=="30")&(features.delay==0)&(features.otm==cfg["primary_otm"])]
    combined=selected.merge(curve[keys+["uncertainty"]],on=keys,suffixes=("","_30"),validate="one_to_one") if "uncertainty" in curve else selected.iloc[:0]
    curve_fit={"status":"inconclusive","reason":"missing_common_maturity_curve"}
    if len(combined):
        combined["curve_delta"]=combined.uncertainty_30-combined.uncertainty
        curve_fit=infer(combined.loc[combined.cohort=="event"],TARGET,cfg,
                        ["curve_delta","uncertainty","momentum","achieved_moneyness","dte"],parameter=1,primary=False)
    mechanism_direction=(mechanism.get("ci_low",float("-inf"))>cfg["criteria"]["H19"]["concentration_lower_bound"]
                         and mechanism.get("leave_one_min",float("-inf"))>0
                         and not mechanism.get("unsupported_leave_one",1)
                         and all(r.get("estimate",float("-inf"))>0 for r in delay_estimates))
    trade_direction=(trade.get("ci_low",float("-inf"))>0
                     and tails.get("tail_loss_reduction",float("-inf")) is not None
                     and tails.get("tail_loss_reduction",float("-inf"))>=cfg["criteria"]["H19"]["tail_loss_reduction_fraction"]
                     and tails.get("mean_return_drag",float("inf"))<=cfg["criteria"]["H19"]["maximum_mean_return_drag"])
    f=selected.loc[selected.cohort=="event"].copy()
    if "concentration_target_end" in f:f["target_end"]=f.concentration_target_end
    folds=chronological(f,TARGET,["uncertainty","momentum"],["uncertainty","momentum","earnings","guidance","debt"],cfg)
    return dict(mechanism=mechanism,trade=trade,tail=tails,delay_mechanisms=delay_estimates,curve_increment=curve_fit,
                mechanism_direction_met=mechanism_direction,trade_direction_met=trade_direction,
                prediction_folds=folds,objective="paid protection reduces worst-decile loss without excessive drag")
