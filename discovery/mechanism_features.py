"""Explicitly separated filing-clock, holding-clock and quote-backed outcomes."""
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

from .mechanism_accounting import construction, quote_set, reserve, transaction
from .io import identity


def classification(anchor, reviews):
    review = reviews.get(anchor["event_id"], {})
    label = review.get("classification", "incomplete_text_unknown")
    valid = {"verified_incoming_cfo_terms", "verified_absence_in_complete_filing",
             "other_person_or_ambiguous", "incomplete_text_unknown"}
    if label not in valid:
        raise ValueError("Unknown CFO review classification")
    if label.startswith("verified_"):
        if not review.get("incoming_person") or not review.get("evidence_sha256") or not review.get("evidence_passage"):
            raise ValueError("Verified CFO classification lacks outcome-blind evidence")
        if identity(review["evidence_passage"]) != review["evidence_sha256"]:
            raise ValueError("CFO evidence passage hash changed")
        if label == "verified_absence_in_complete_filing" and not review.get("complete_filing_reviewed"):
            raise ValueError("A partial excerpt cannot establish absence")
    return label


def features(sources, anchor, variant, selection, bucket, otm, delay, reviews):
    cfg = sources.cfg
    day = variant["entry_date"]
    ei = sources.index[day]
    result = {"event_id": anchor["event_id"], "anchor_id": anchor["anchor_id"], "issuer": anchor["issuer"],
              "ticker": anchor["ticker"], "filing_date": anchor["filing_date"], "filing_session": anchor["filing_session"],
              "cohort": anchor["cohort"], "delay": delay, "bucket": bucket, "otm": otm,
              "entry_date": day, "target_end": sources.dates[ei+5] if ei+5 < len(sources.dates) else None,
              "concentration_target_end": sources.dates[ei+10] if ei+10 < len(sources.dates) else None,
              "classification": classification(anchor, reviews), "categories": "|".join(anchor["categories"])}
    context = anchor.get("context", [])
    cats = {r.get("tertiary_category", "") for r in context}
    text = " ".join(r.get("supporting_text", "") for r in context)
    result.update(compensation_cotag=float(any("compensation" in c for c in cats)),
                  text_terms_proxy=float(bool(re.search(r"salary|compensation|equity award|incentive", text, re.I))),
                  earnings=float(any("earnings" in c for c in cats)),
                  guidance=float(any("guidance" in c for c in cats)),
                  debt=float(any("debt" in c or "credit" in c for c in cats)),
                  verified_terms=float(result["classification"] == "verified_incoming_cfo_terms"))
    s = sources.spot(selection, day)
    c = sources.mark(selection, "atm_call", day)
    p = sources.mark(selection, "atm_put", day)
    dte = (pd.Timestamp(selection["expiry"])-pd.Timestamp(day)).days
    result.update(dte=dte, achieved_moneyness=(selection["atm_strike"]/s-1) if s else None)
    di = sources.index[variant["decision_date"]]
    past = sources.spot(selection, sources.dates[di-5]) if di >= 5 else None
    current = sources.spot(selection, variant["decision_date"])
    result["momentum"] = current/past-1 if current and past else None
    past_moves = [sources.spot(selection, sources.dates[j]) for j in range(max(0, di-5), di+1)]
    result["past_move_rms"] = float(np.sqrt(np.mean(np.diff(np.log(past_moves))**2))) if len(past_moves) == 6 and all(past_moves) else None
    if not s or not c or not p or dte <= 0:
        result["feature_status"] = "missing_same_session_entry_pair"
        return result
    premium = c["price"]+p["price"]
    uncertainty = premium/s/math.sqrt(dte/365.25)
    result.update(entry_spot=s, uncertainty=uncertainty)
    path = [sources.spot(selection, sources.dates[j]) for j in range(ei, min(ei+11, len(sources.dates)))]
    if len(path) < 6 or any(v is None for v in path[:6]) or sources.dates[ei+5] > selection["expiry"]:
        result["feature_status"] = "incomplete_five_session_same_contract_path"
        return result
    finish = sources.dates[ei+5]
    cc, pp = sources.mark(selection, "atm_call", finish), sources.mark(selection, "atm_put", finish)
    changes = np.diff(np.log(path[:6]))
    result.update(feature_status="measured", premium_log_change=math.log((cc["price"]+pp["price"])/premium),
                  synthetic_return=path[5]/path[0]-1, abs_synthetic_return=abs(path[5]/path[0]-1),
                  elapsed_dte=(pd.Timestamp(finish)-pd.Timestamp(day)).days/dte,
                  rms=float(np.sqrt(np.mean(changes[:5]**2))),
                  early_downside=max(0, 1-min(path[:6])/path[0]))
    normalization = uncertainty*math.sqrt(5/252)
    if len(path) == 11 and all(v is not None for v in path) and sources.dates[ei+10] <= selection["expiry"]:
        result["late_downside"] = max(0, 1-min(path[5:11])/path[5])
        result["downside_concentration"] = (result["early_downside"]-result["late_downside"])/normalization if normalization else None
    # Pre-filing outcome is only a retrospective falsification, never an input.
    fi = anchor["filing_session"]
    pre = [sources.spot(selection, sources.dates[j]) for j in range(max(0, fi-3), fi+1)]
    result["prefiling_return"] = pre[-1]/pre[0]-1 if len(pre) == 4 and all(pre) else None
    return result


def mark_scenario(sources, anchor, variant, selection, shape, otm, haircut):
    """Separate research mark scenario: never establishes an executable fill."""
    quantities = construction(shape, otm)
    ei = anchor["filing_session"]+sources.cfg["primary_filing_horizon"]
    if ei >= len(sources.dates) or sources.dates[ei] < variant["entry_date"] or sources.dates[ei] > selection["expiry"]:
        return {"mark_scenario_status": "inconclusive", "mark_scenario_reason": "unresolved_event_clock"}
    cash = 0
    for role, quantity in quantities.items():
        first = sources.mark(selection, role, variant["entry_date"])
        last = sources.mark(selection, role, sources.dates[ei])
        if first is None or last is None:
            return {"mark_scenario_status": "inconclusive", "mark_scenario_reason": "missing_daily_leg"}
        cash += 100*quantity*(last["price"]-first["price"])-100*abs(quantity)*haircut*(first["price"]+last["price"])-2*abs(quantity)*sources.cfg["commission_per_contract_side"]
    return {"mark_scenario_status": "measured", "mark_scenario_reason": None,
            "mark_scenario_stock_return": cash/(100*selection["selection_spot"]),
            "mark_scenario_haircut": haircut, "execution_evidence": False}


def horizon_trade(sources, anchor, variant, selection, shape, horizon, delay, costs=1):
    cfg = sources.cfg
    base = {"anchor_id": anchor["anchor_id"], "event_id": anchor["event_id"], "issuer": anchor["issuer"],
            "cohort": anchor["cohort"], "filing_date": anchor["filing_date"], "filing_session": anchor["filing_session"],
            "shape": shape, "horizon": horizon, "delay": delay, "cost_multiplier": costs,
            "bucket": cfg["primary_bucket"], "otm": cfg["primary_otm"], "status": "inconclusive"}
    if selection is None:
        return {**base, "reason": "primary_chain_unavailable"}
    quantities = construction(shape, cfg["primary_otm"])
    entry, reason = quote_set(selection, "entry", quantities, cfg)
    if entry is None:
        return {**base, "reason": reason}
    exit_quotes, reason = quote_set(selection, str(horizon), quantities, cfg)
    if exit_quotes is None:
        return {**base, "reason": reason}
    end = selection["quotes"][str(horizon)]["date"]
    entry_day = variant["entry_date"]
    if end < entry_day or end > selection["expiry"]:
        return {**base, "reason": "exit_before_entry_or_after_expiry"}
    if any((sources.prior_volume(selection, r, variant["decision_date"]) or 0) < cfg["minimum_prior_five_session_leg_volume"] for r in quantities):
        return {**base, "reason": "insufficient_prior_leg_volume"}
    cash_in, cost_in, _ = transaction(quantities, entry, cfg, True, costs)
    cash_out, cost_out, _ = transaction(quantities, exit_quotes, cfg, False, costs)
    held = (pd.Timestamp(end)-pd.Timestamp(entry_day)).days
    funding = reserve(selection, shape, quantities)
    # Funded cash P&L includes interest on strike reserve plus opening cashflow.
    interest = (funding+cash_in)*math.expm1(cfg["rate"]*held/365.25)
    spot_entry = selection["atm_strike"]*math.exp(-cfg["rate"]*max(0,(pd.Timestamp(selection["expiry"])-pd.Timestamp(entry_day)).days)/365.25)
    if "atm_call" in entry and "atm_put" in entry:
        spot_entry += (entry["atm_call"]["ask_price"]+entry["atm_call"]["bid_price"])/2-(entry["atm_put"]["ask_price"]+entry["atm_put"]["bid_price"])/2
    else:
        # CSP still needs its stock-notional denominator from a contemporaneous
        # parity quote; incomplete pair cannot be substituted by a future close.
        pair_quotes, _ = quote_set(selection, "entry", ["atm_call", "atm_put"], cfg)
        if pair_quotes:
            spot_entry += sum((1 if r == "atm_call" else -1)*(q["ask_price"]+q["bid_price"])/2 for r,q in pair_quotes.items())
        else:
            spot_entry = None
    pnl = cash_in+cash_out+interest
    return {**base, "status": "measured", "reason": None, "entry_date": entry_day, "exit_date": end,
            "net_pnl": pnl, "cash_interest": interest, "cost_dollars": cost_in+cost_out,
            "stock_notional_return": pnl/(100*spot_entry) if spot_entry and spot_entry > 0 else None,
            "collateral_return": pnl/funding if funding else None, "reserve": funding,
            "elapsed_days": held, "historical_clock_verified": False}


def build(sources, category, shape, reviews):
    diagnostics, horizons, capacity = [], [], []
    anchors = [a for a in sources.source["anchors"] if category in a["categories"]]
    cfg = sources.cfg
    for anchor in anchors:
        for delay in cfg["decision_delays"]:
            variant = anchor["variants"].get(str(delay), {})
            for bucket in cfg["buckets"]:
                selection = variant.get("selected", {}).get(bucket)
                if anchor["cohort"] == "ordinary" and not anchor.get("ordinary_history_complete", True):selection = None
                for otm in cfg["otm_grid"]:
                    if selection:
                        row = features(sources, anchor, variant, selection, bucket, otm, delay, reviews)
                        for haircut in cfg["premium_haircuts_side"]:
                            scenario = mark_scenario(sources, anchor, variant, selection, shape, otm, haircut)
                            row["haircut_"+str(haircut)+"_return"] = scenario.get("mark_scenario_stock_return")
                    else:
                        row = {"event_id": anchor["event_id"], "issuer": anchor["issuer"], "cohort": anchor["cohort"],
                               "filing_session": anchor["filing_session"], "filing_date": anchor["filing_date"],
                               "classification": classification(anchor, reviews),
                               "delay": delay, "bucket": bucket, "otm": otm,
                               "feature_status": variant.get("missing_buckets", {}).get(bucket, variant.get("reason", "unavailable"))}
                    diagnostics.append(row)
            selection = variant.get("selected", {}).get(cfg["primary_bucket"])
            if anchor["cohort"] == "ordinary" and not anchor.get("ordinary_history_complete", True):selection = None
            for horizon in cfg["filing_horizons"]+["expiry"]:
                for costs in cfg["cost_multipliers"]:
                    for comparison in [shape, "synthetic_long"]:
                        record = horizon_trade(sources, anchor, variant, selection, comparison, horizon, delay, costs)
                        if anchor["cohort"] == "ordinary" and not anchor.get("ordinary_history_complete", True):record["reason"] = "ordinary_category_window_incomplete"
                        horizons.append(record)
            if selection:
                for role in construction(shape):
                    adv = sources.prior_volume(selection, role, variant["decision_date"])
                    q = selection.get("quotes", {}).get("entry", {}).get("legs", {}).get(role, {}).get("quote")
                    for participation in cfg["participation_grid"]:
                        capacity.append({"anchor_id": anchor["anchor_id"], "delay": delay, "role": role,
                                         "prior_five_session_adv_contracts": adv, "participation": participation,
                                         "volume_units": math.floor(adv*participation) if adv is not None else None,
                                         "displayed_contracts": min(q["bid_size"], q["ask_size"]) if q else None,
                                         "unit_reserve_dollars": reserve(selection, shape, construction(shape)) if all(r in selection["legs"] for r in construction(shape)) else None,
                                         "sqrt_participation_impact_proxy": math.sqrt(participation),
                                         "impact_calibration": "unknown; proxy is not dollar-cost evidence"})
    frame = pd.DataFrame(diagnostics)
    for column in ["event_id","issuer","cohort","delay","bucket","otm","filing_date","filing_session","classification",
                   "premium_log_change","synthetic_return","abs_synthetic_return","elapsed_dte","uncertainty",
                   "downside_concentration","rms","early_downside","momentum","achieved_moneyness","dte",
                   "target_end","concentration_target_end","earnings","guidance","debt","verified_terms",
                   "compensation_cotag","text_terms_proxy","prefiling_return","past_move_rms"]:
        if column not in frame: frame[column] = None
    horizon_frame = pd.DataFrame(horizons)
    if horizon_frame.empty:
        horizon_frame = pd.DataFrame(columns=["anchor_id","event_id","issuer","cohort","filing_date","filing_session",
                                              "shape","horizon","delay","cost_multiplier","bucket","otm","status",
                                              "stock_notional_return","collateral_return"])
    return anchors, frame, horizon_frame, pd.DataFrame(capacity)
