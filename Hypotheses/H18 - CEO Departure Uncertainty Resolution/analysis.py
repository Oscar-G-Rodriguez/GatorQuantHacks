"""H18: abnormal premium compression and covered-call incremental objective."""
from discovery.mechanism_statistics import infer, pair, chronological
from discovery.mechanism_comparisons import paired_trade, tail

TARGET="premium_log_change"
CONTROLS=["synthetic_return","abs_synthetic_return","elapsed_dte","uncertainty"]


def evaluate(features,horizons,cfg):
    selected=features.loc[(features.delay==0)&(features.bucket==cfg["primary_bucket"])&(features.otm==cfg["primary_otm"])]
    paired=pair(selected,[TARGET]+CONTROLS)
    mechanism=infer(paired,TARGET,cfg,CONTROLS)
    rows,trades=paired_trade(horizons,"covered_call",cfg)
    trade=infer(trades,"increment",cfg)
    _,double=paired_trade(horizons,"covered_call",cfg,cost=2)
    double_mean=float(double.increment.mean()) if "increment" in double and len(double) else None
    tails=tail(rows.loc[rows.cohort=="event"])
    mechanism_direction=(mechanism.get("ci_high",float("inf"))<cfg["criteria"]["H18"]["compression_upper_bound"]
                         and mechanism.get("leave_one_max",float("inf"))<0 and not mechanism.get("unsupported_leave_one",1))
    trade_direction=(trade.get("ci_low",float("-inf"))>cfg["criteria"]["H18"]["net_increment_lower_bound"]
                     and double_mean is not None and double_mean>0
                     and tails.get("q10_shape",float("-inf"))>=tails.get("q10_long",float("inf")))
    folds=chronological(selected.loc[selected.cohort=="event"],TARGET,["uncertainty","momentum"],
                         ["uncertainty","momentum","earnings","guidance","debt"],cfg)
    return dict(mechanism=mechanism,trade=trade,doubled_cost_mean=double_mean,tail=tails,
                mechanism_direction_met=mechanism_direction,trade_direction_met=trade_direction,
                prediction_folds=folds,objective="covered call minus funded long; event minus ordinary")
