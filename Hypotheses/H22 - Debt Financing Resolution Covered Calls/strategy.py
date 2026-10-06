"""Funded H22 covered calls and matched controls, driven by Backtrader sessions.

Borrowing: the supplied Webull runner's Cerebro/Strategy pattern and the shared
mechanism_engine clock. The ledger below owns stock, short-call liability,
fees, dividends, assignment and risk; the clock feed's broker P&L is unused.
"""
from __future__ import annotations
from bisect import bisect_left
from collections import defaultdict
import json
import math
from pathlib import Path
import time
try:
    import resource
except ImportError:  # Windows synthetic correctness tests have no getrusage.
    resource = None

import numpy as np
import pandas as pd

from discovery.io import digest, identity, read_json, write_json
from discovery.mechanism_engine import FundedStrategy, replay
from research import HERE, csv_write, scheduled, verify_manifest, receipt, bar_map


class Data:
    def __init__(self,run):
        self.run=Path(run);self.cfg=read_json(HERE/"settings.json")
        self.calendar=read_json(self.run/"prepared/calendar.json");self.dates=self.calendar["dates"]
        self.index={d:i for i,d in enumerate(self.dates)}
        self.actions=read_json(self.run/"prepared/actions.json")
        self.source=read_json(self.run/"acquisition/source.json")
        if self.source["source_id"]!=identity({k:v for k,v in self.source.items() if k!="source_id"}):raise ValueError("Acquisition identity changed")
        self.objects={};self.bars={}
        for key,o in self.source["objects"].items():
            p=self.run/"acquisition/objects"/(key+".json")
            if digest(p)!=o["sha256"]:raise ValueError("Acquired object changed")
            self.objects[key]=read_json(p)
        self.records=self.source["records"]

    def marks(self,record,leg):
        key=record.get(leg+"_object")
        if key is None:return {}
        if key not in self.bars:self.bars[key]=bar_map(self.objects[key])
        return self.bars[key]

    def quote_pair(self,r,label):
        quotes=[]
        for leg in ["stock","call"]:
            ref=r.get("quote_objects",{}).get(label+"_"+leg,{})
            if "object" not in ref:return None,"missing_quote"
            rows=self.objects[ref["object"]];cut=ref["cutoff_ns"]
            candidates=[q for q in rows if 0<=cut-q.get("sip_timestamp",0)<=int(self.cfg["quote_max_age_seconds"]*1e9)]
            if not candidates:return None,"missing_or_stale_quote"
            q=max(candidates,key=lambda q:q["sip_timestamp"])
            bid,ask=q.get("bid_price",0),q.get("ask_price",0)
            if bid<=0 or ask<bid or min(q.get("bid_size",0),q.get("ask_size",0))<1:return None,"invalid_quote_or_size"
            mid=(bid+ask)/2
            if leg=="call" and (ask-bid)/mid>self.cfg["quote_max_relative_spread"]:return None,"wide_option_spread"
            quotes.append({"bid":bid,"ask":ask,"mid":mid,"timestamp":q["sip_timestamp"],"age_seconds":(cut-q["sip_timestamp"])/1e9,"relative_spread":(ask-bid)/mid})
        if abs(quotes[0]["timestamp"]-quotes[1]["timestamp"])/1e9>self.cfg["quote_synchrony_seconds"]:return None,"asynchronous_quotes"
        return quotes,"fresh_quotes"


def fees(stock,call,cfg,multiplier=1,stock_only=False):
    return multiplier*(100*stock*cfg["stock_friction"] + (0 if stock_only else 100*call*cfg["option_friction"]+cfg["option_fee"]))


def eligibility(record,data):
    if record.get("status")!="bars_downloaded":return record.get("status","missing_record")
    stock=data.marks(record,"stock");call=data.marks(record,"option")
    di,ei=record["session"],record["entry_session"]
    if di>=ei or data.dates[di]!=record["date"] or data.dates[ei]!=record["entry_date"]:raise ValueError("Entry clock is not after decision")
    if any(d not in stock or d not in call for d in [record["date"],record["entry_date"]]):return "missing_decision_or_entry_bar"
    prior=data.dates[max(0,ei-5):ei]
    if len(prior)!=5:return "insufficient_volume_warmup"
    volume=sum(call.get(d,{}).get("v",0) for d in prior)
    if volume<data.cfg["minimum_prior_option_volume"]:return "thin_prior_option_volume"
    if stock.get(data.dates[ei-1],{}).get("v",0)<data.cfg["minimum_prior_stock_volume"]:return "thin_prior_stock_volume"
    return "eligible"


def fresh_mark(marks,dates,i,max_age=1):
    for age in range(max_age+1):
        if i-age>=0 and dates[i-age] in marks:return marks[dates[i-age]]["c"],age
    return None,None


def unit_trade(r,data,horizon,costs=1,assignment="time_value",stock_only=False):
    """Fixed trade diagnostic, preserving failures after a real entry.

    Eligibility is decided at entry. Future splits, missing exits and mark gaps
    are outcomes/statuses and never retroactive eligibility filters.
    """
    result={"anchor_id":r["anchor_id"],"pair_id":r["pair_id"],"issuer":r["issuer"],"ticker":r["ticker"],
            "variant":r["variant"],"role":r["role"],"event_status":r["event_status"],"horizon":horizon,
            "decision_date":r["date"],"entry_date":r["entry_date"],"entry_session":r["entry_session"],
            "cost_multiplier":costs,"assignment_policy":assignment,"stock_only":stock_only,
            "fill_model":"assumed_daily_close","status":eligibility(r,data)}
    if result["status"]!="eligible":return result
    stock=data.marks(r,"stock");calls=data.marks(r,"option");ei=r["entry_session"]
    s0=stock[r["entry_date"]]["c"];c0=calls[r["entry_date"]]["c"]
    contract=r["contract"];strike=contract["strike_price"];expiry=contract["expiration_date"]
    opening=fees(s0,c0,data.cfg,costs,stock_only)
    result.update(stock_entry=s0,call_entry=c0,funded_notional=100*s0,
                  opening_cost=opening,call_ticker=contract["ticker"],strike=strike,expiry=expiry,
                  decision_premium_ratio=calls[r["date"]]["c"]/r["nominal_decision_close"],
                  achieved_otm=strike/r["nominal_decision_close"]-1,
                  decision_dte=(pd.Timestamp(expiry)-pd.Timestamp(r["date"])).days,
                  prior_option_volume=sum(calls.get(d,{}).get("v",0) for d in data.dates[ei-5:ei]),
                  features=r["features"])
    if ei+horizon>=len(data.dates):result["status"]="initiated_outcome_outside_history";return result
    target=ei+horizon;last=min(target+data.cfg["exit_retry_sessions"],len(data.dates)-1)
    actions=data.actions.get(r["ticker"],{"splits":[],"dividends":[]})
    dividends={a["ex_dividend_date"]:a for a in actions["dividends"] if a.get("currency")=="USD"}
    split_dates={a["execution_date"] for a in actions["splits"]}
    income=0.;expired=False;mark_gaps=0;exit_i=None;reason="scheduled_exit";exit_call=None;exit_stock=None
    for i in range(ei+1,last+1):
        day=data.dates[i];previous=data.dates[i-1]
        if day in split_dates and not stock_only and not expired:
            result["status"]="initiated_unknown_option_split_deliverable";return result
        # If stock-only, split quantity must also be explicit. We retain the
        # unresolved status rather than applying adjusted prices to 100 shares.
        if day in split_dates:
            result["status"]="initiated_unmodelled_stock_split";return result
        dividend=dividends.get(day)
        if (not stock_only and not expired and dividend and contract["exercise_style"]=="american"
                and dividend.get("declaration_date",day)<=previous and previous in stock and previous in calls):
            prior_s=stock[previous]["c"];prior_c=calls[previous]["c"];itm=prior_s>strike
            value=prior_c-max(prior_s-strike,0)
            if itm and (assignment=="any_itm" or value<dividend["cash_amount"]):
                exit_i=i;exit_stock=strike;exit_call=0.;reason="modelled_early_assignment";break
        if dividend:income+=100*dividend["cash_amount"]
        if not stock_only and not expired and day>=expiry:
            if day not in stock:result["status"]="initiated_missing_expiry_stock";return result
            if stock[day]["c"]>strike:
                exit_i=i;exit_stock=strike;exit_call=0.;reason="modelled_expiry_assignment";break
            expired=True
        if fresh_mark(stock,data.dates,i,1)[0] is None or (not stock_only and not expired and fresh_mark(calls,data.dates,i,1)[0] is None):mark_gaps+=1
        if i>=target and day in stock and (stock_only or expired or day in calls):
            exit_i=i;exit_stock=stock[day]["c"];exit_call=0. if stock_only or expired else calls[day]["c"];break
    if exit_i is None:result["status"]="initiated_unfilled_exit_after_retries";return result
    closing=fees(exit_stock,exit_call,data.cfg,costs,stock_only)
    stock_pnl=100*(exit_stock-s0);call_pnl=0. if stock_only else 100*(c0-exit_call)
    total=stock_pnl+call_pnl+income-opening-closing
    result.update(status="completed",exit_date=data.dates[exit_i],exit_session=exit_i,exit_reason=reason,
                  exit_delay=max(0,exit_i-target),stock_exit=exit_stock,call_exit=exit_call,
                  stock_pnl=stock_pnl,call_pnl=call_pnl,dividend_accrual=income,
                  closing_cost=closing,total_cost=opening+closing,net_pnl=total,net_return=total/(100*s0),
                  mark_gap_sessions=mark_gaps,call_expired=expired,
                  call_proxy_change=None if stock_only else exit_call/c0-1)
    return result


class Ledger:
    """One-contract funded portfolio; constant Backtrader feed is only a clock."""
    def __init__(self,data,records,costs,assignment,stock_only=False):
        self.data=data;self.records=defaultdict(list);self.cash=data.cfg["initial_cash"]
        self.positions={};self.rows=[];self.trades=[];self.costs=costs;self.assignment=assignment
        self.stock_only=stock_only;self.high=self.cash;self.cooldown=-1;self.derisk=False
        self.receivables=[];self.invalid_nav=False;self.last_nav=self.cash;self.turnover=0.
        for r in records:self.records[r["entry_date"]].append(r)

    def _mark(self,p,i):
        s,sa=fresh_mark(self.data.marks(p["r"],"stock"),self.data.dates,i,1)
        if self.stock_only or p["expired"]:c,ca=0.,0
        else:c,ca=fresh_mark(self.data.marks(p["r"],"option"),self.data.dates,i,1)
        if s is None or c is None:return None,None
        return 100*(s-c),max(sa,ca)

    def _close(self,key,day,s,c,reason):
        p=self.positions.pop(key);closing=fees(s,c,self.data.cfg,self.costs,self.stock_only)
        self.cash+=100*(s-(0 if self.stock_only else c))-closing
        self.turnover+=100*(s+(0 if self.stock_only else c))
        r=p["r"];stock_pnl=100*(s-p["s0"]);call_pnl=0 if self.stock_only else 100*(p["c0"]-c)
        net=stock_pnl+call_pnl+p["dividends"]-p["opening"]-closing
        self.trades.append({"anchor_id":r["anchor_id"],"pair_id":r["pair_id"],"issuer":r["issuer"],"ticker":r["ticker"],
            "role":r["role"],"entry_date":r["entry_date"],"exit_date":day,"status":"completed", "reason":reason,
            "stock_pnl":stock_pnl,"call_pnl":call_pnl,"dividend_accrual":p["dividends"],"cost":p["opening"]+closing,
            "net_pnl":net,"funded_notional":100*p["s0"],"net_return":net/(100*p["s0"])})

    def step(self,day):
        i=self.data.index[day];stale=0;bad=False
        # Cash payments and receivables do not duplicate dividend accrual.
        due=[r for r in self.receivables if r["pay"]<=day]
        self.cash+=sum(r["dollars"] for r in due)
        self.receivables=[r for r in self.receivables if r["pay"]>day]
        for key,p in list(self.positions.items()):
            r=p["r"];contract=r["contract"];strike=contract["strike_price"]
            stock=self.data.marks(r,"stock");calls=self.data.marks(r,"option")
            actions=self.data.actions.get(r["ticker"],{"dividends":[],"splits":[]})
            if any(a["execution_date"]==day for a in actions["splits"]):p["unresolved"]="split_deliverable_unknown"
            if p.get("unresolved"):bad=True;continue
            dividend=next((a for a in actions["dividends"] if a["ex_dividend_date"]==day and a.get("currency")=="USD"),None)
            previous=self.data.dates[i-1] if i else None
            if (not self.stock_only and not p["expired"] and dividend and contract["exercise_style"]=="american"
                    and dividend.get("declaration_date",day)<=previous and previous in stock and previous in calls):
                s=stock[previous]["c"];c=calls[previous]["c"]
                if s>strike and (self.assignment=="any_itm" or c-(s-strike)<dividend["cash_amount"]):
                    self._close(key,day,strike,0.,"modelled_early_assignment");continue
            if dividend:
                dollars=100*dividend["cash_amount"];p["dividends"]+=dollars
                self.receivables.append({"dollars":dollars,"pay":dividend.get("pay_date") or self.data.cfg["end"]+"~"})
            if not self.stock_only and not p["expired"] and day>=contract["expiration_date"]:
                if day not in stock:p["unresolved"]="missing_expiry_stock";bad=True;continue
                if stock[day]["c"]>strike:self._close(key,day,strike,0.,"modelled_expiry_assignment");continue
                p["expired"]=True
            target=p["target"]
            if i>=target or self.derisk:
                if day in stock and (self.stock_only or p["expired"] or day in calls):
                    self._close(key,day,stock[day]["c"],0. if self.stock_only or p["expired"] else calls[day]["c"],"drawdown_exit" if self.derisk else "scheduled_exit");continue
                if i>target+self.data.cfg["exit_retry_sessions"]:p["unresolved"]="unfilled_exit_after_retries";bad=True
        nav=self.cash+sum(r["dollars"] for r in self.receivables)
        gross=0.
        for p in self.positions.values():
            value,age=self._mark(p,i)
            if value is None:bad=True
            else:nav+=value;stale=max(stale,age)
            s,_=fresh_mark(self.data.marks(p["r"],"stock"),self.data.dates,i,1)
            gross+=100*s if s is not None else 100*p["s0"]
        if bad:self.invalid_nav=True
        if not bad and not self.positions and self.derisk:
            self.derisk=False
        if not bad and i>=self.cooldown and self.cooldown>=0:
            self.high=nav;self.cooldown=-1
        if not bad:
            self.high=max(self.high,nav)
            if nav/self.high-1<=-self.data.cfg["drawdown_limit"] and not self.derisk:
                self.derisk=True;self.cooldown=i+self.data.cfg["cooldown_sessions"]
        for r in sorted(self.records.get(day,[]),key=lambda r:(r["issuer"],str(r["accessions"]),r["ticker"])):
            reason=eligibility(r,self.data)
            if reason=="eligible":
                if r["issuer"] in self.positions:reason="issuer_position_already_open"
                elif bad or self.derisk or i<self.cooldown:reason="risk_cooldown_or_unknown_nav"
                elif i+21>=len(self.data.dates):reason="planned_exit_outside_history"
                else:
                    s=self.data.marks(r,"stock")[day]["c"];c=self.data.marks(r,"option")[day]["c"]
                    opening=fees(s,c,self.data.cfg,self.costs,self.stock_only)
                    funding=100*s;outlay=funding-(0 if self.stock_only else 100*c)+opening
                    if funding>nav*self.data.cfg["name_limit"] or gross+funding>nav*self.data.cfg["gross_limit"] or outlay>self.cash:reason="funding_or_exposure_limit"
                    else:
                        self.cash-=outlay;self.turnover+=100*(s+(0 if self.stock_only else c));gross+=funding
                        nav-=opening
                        self.positions[r["issuer"]]={"r":r,"s0":s,"c0":c,"opening":opening,"dividends":0.,"target":i+21,"expired":False}
                        continue
            self.trades.append({"anchor_id":r["anchor_id"],"pair_id":r["pair_id"],"issuer":r["issuer"],"ticker":r["ticker"],"entry_date":day,"status":"unfilled","reason":reason})
        self.rows.append({"date":day,"nav":None if bad else nav,"cash":self.cash,"dividend_receivable":sum(r["dollars"] for r in self.receivables),
                          "funded_gross":gross,"positions":len(self.positions),"stale_sessions":stale,"unknown_nav":bad})
        self.last_nav=nav

    def result(self):
        for p in self.positions.values():
            r=p["r"];self.trades.append({"anchor_id":r["anchor_id"],"pair_id":r["pair_id"],"issuer":r["issuer"],"ticker":r["ticker"],
                "entry_date":r["entry_date"],"status":"unresolved","reason":p.get("unresolved","still_open_at_history_end")})
        return {"daily":self.rows,"trades":self.trades,"turnover_dollars":self.turnover,"invalid_nav":self.invalid_nav,"remaining_positions":len(self.positions)}


class FinancingCoveredCall(FundedStrategy):
    """Own hypothesis strategy class; each next() advances the H22 ledger."""
    pass


STRATEGY_CLASS=FinancingCoveredCall


def performance(replayed,cfg):
    rows=replayed["daily"];complete=not replayed["invalid_nav"] and not replayed["remaining_positions"]
    result={"phase":"development","sessions":len(rows),"start":rows[0]["date"] if rows else None,"end":rows[-1]["date"] if rows else None,
            "completed_trades":sum(r["status"]=="completed" for r in replayed["trades"]),
            "unfilled_trades":sum(r["status"]=="unfilled" for r in replayed["trades"]),
            "unresolved_trades":replayed["remaining_positions"],"stale_days":sum(r["stale_sessions"]>0 for r in rows),
            "full_nav_available":complete,"annualization_sessions":252,"cash_return":0,
            "turnover_dollars":replayed["turnover_dollars"]}
    if not complete or not rows or result["completed_trades"]==0:
        result.update(annualized_return=None,volatility=None,sharpe=None,max_drawdown=None,net_pnl=None,turnover=None)
        return result
    nav=np.array([cfg["initial_cash"]]+[r["nav"] for r in rows],dtype=float)
    ret=nav[1:]/nav[:-1]-1;vol=float(ret.std(ddof=1)*np.sqrt(252))
    result.update(annualized_return=float((nav[-1]/nav[0])**(252/len(rows))-1),volatility=vol,
        sharpe=float(ret.mean()*252/vol) if vol>0 else None,max_drawdown=float(np.min(nav/np.maximum.accumulate(nav)-1)),
        net_pnl=float(nav[-1]-nav[0]),turnover=float(replayed["turnover_dollars"]/nav[:-1].mean()))
    return result


def run_task(run,task_index):
    scheduled();run=Path(run);m=verify_manifest(run);task=read_json(run/"tasks.json")[task_index]
    rp=run/"receipts"/f"task-{task_index}.json"
    if rp.exists():
        r=read_json(rp)
        if r["manifest_id"]!=m["manifest_id"] or r["status"]!="completed":raise ValueError("Existing task is not completed under this freeze")
        for p,h in r["files"].items():
            if digest(run/p)!=h:raise ValueError("Checkpoint file changed")
        print("Verified completed task",task_index);return
    start=time.monotonic();data=Data(run);records=[r for r in data.records if r["variant"]==task["variant"]]
    folder=run/"results"/f"task-{task_index}";folder.mkdir(parents=True,exist_ok=True)
    diagnostics=[]
    for r in records:
        for h in data.cfg["horizons"]:
            diagnostics.append(unit_trade(r,data,h,task["costs"],task["assignment"]))
            diagnostics.append(unit_trade(r,data,h,task["costs"],task["assignment"],True))
    write_json(folder/"trades.json",diagnostics)
    kpis=[];all_nav=[];all_trades=[]
    for role in ["event","ordinary","planned","shifted"]:
        cohort=[r for r in records if r["role"]==role]
        for stock_only in [False,True]:
            ledger=Ledger(data,cohort,task["costs"],task["assignment"],stock_only)
            result=replay(STRATEGY_CLASS,ledger,data.dates)
            label=role+("_stock" if stock_only else "_covered_call")
            kpis.append({"portfolio":label,**performance(result,data.cfg)})
            all_nav.extend({"portfolio":label,**r} for r in result["daily"])
            all_trades.extend({"portfolio":label,**r} for r in result["trades"])
    csv_write(folder/"performance.csv",kpis);csv_write(folder/"daily-nav.csv",all_nav);csv_write(folder/"trade-ledger.csv",all_trades)
    elapsed=time.monotonic()-start
    receipt(run,f"task-{task_index}",list(folder.glob("*")),{"task":task,"elapsed_seconds":elapsed,
            "max_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None,"records":len(records)})
    print(json.dumps({"task":task_index,"elapsed_seconds":elapsed,"records":len(records)},indent=2),flush=True)
