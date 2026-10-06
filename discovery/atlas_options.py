"""Massive-only bounded historical option acquisition and priced-uncertainty inputs."""
from __future__ import annotations
import argparse
from pathlib import Path
from urllib.parse import quote
import numpy as np
import pandas as pd
import exchange_calendars as xcals
from .atlas_data import Store, settings
from .io import ROOT, digest, identity, now, read_json, write_json
from .mechanism_data import standard_pairs, same_day_bar


def select(rows, anchor, config):
    pairs=standard_pairs(rows,anchor["date"]);result={};spot=anchor["stock_close"]
    for bucket,(lo,hi) in config["option_buckets"].items():
        choices=[k for k in pairs if lo<=(pd.Timestamp(k[0])-pd.Timestamp(anchor["date"])).days<=hi]
        if not choices:continue
        expiry=min({x[0] for x in choices},key=lambda d:(abs((pd.Timestamp(d)-pd.Timestamp(anchor["date"])).days-int(bucket)),d))
        strikes=sorted(k[1] for k in choices if k[0]==expiry);atm=min(strikes,key=lambda k:(abs(k-spot),k))
        legs={"atm_call":pairs[(expiry,atm)]["call"],"atm_put":pairs[(expiry,atm)]["put"]}
        for side,direction in [("call",1),("put",-1)]:
            wanted=spot*(1+direction*config["option_otm_distance"])
            strike=min(strikes,key=lambda k:(abs(k-wanted),k))
            if abs(direction*(strike/spot-1)-config["option_otm_distance"])<=config["option_otm_tolerance"]:
                legs["otm_"+side]=pairs[(expiry,strike)][side]
        result[bucket]={"expiry":expiry,"dte":(pd.Timestamp(expiry)-pd.Timestamp(anchor["date"])).days,"legs":legs}
    return result


def quote_samples(anchors,seed,maximum=64):
    """Coverage-only, deterministic samples by calendar year and anchor role."""
    groups={}
    for a in anchors:groups.setdefault((a['date'][:4],a['role']),[]).append(a)
    return {(a['ticker'],a['date']) for group in groups.values() for a in sorted(group,key=lambda a:identity({'seed':seed,'ticker':a['ticker'],'date':a['date']}))[:maximum]}


def nominal_spot(store,anchor,config):
    """Contract strikes use the actual session price, not today's split-adjusted units."""
    path='/v2/aggs/ticker/'+quote(anchor['ticker'],safe='')+'/range/1/day/'+config['start']+'/'+config['end']
    params={'adjusted':'false','sort':'asc','limit':50000}
    rows=store.pages('nominal underlying '+anchor['ticker'],path,params,optional=True)
    bar=same_day_bar(rows,anchor['date']) if rows is not None else None
    return ({**anchor,'adjusted_stock_close':anchor['stock_close'],'stock_close':bar['c'],
             'nominal_spot_object':identity({'path':path,'params':params})} if bar else None)


def acquire(requests, output, budget=5000):
    config=settings();anchors=read_json(requests);output=Path(output);store=Store(output,budget);records=[]
    sampling={'maximum_per_year_role':64,'strata':'calendar year / event or ordinary anchor','ranking':'SHA-256 of fixed seed/ticker/date; no outcome values'}
    previous=output/'options-source.json';history=[]
    if previous.exists():
        old=read_json(previous)
        if old.get('source_id')!=identity({k:v for k,v in old.items() if k!='source_id'}):raise ValueError('Earlier option source manifest changed')
        if (old['requests_sha256']!=digest(requests) or old['settings']!=config or old.get('quote_sampling')!=sampling
                or old.get('contract_query_policy')!='active_at_historical_as_of'
                or old.get('spot_policy')!='unadjusted_same_session_underlying'):raise ValueError('Resume request/settings/sampling/contract clock/spot units differ')
        for key,entry in old['objects'].items():
            if digest(output/entry['file'])!=entry['sha256']:raise ValueError('Earlier option object changed')
        store.entries.update(old['objects']);store.failures.extend(old['failures']);records=list(old['records'])
        h=digest(previous);saved=output/'history'/('options-source-'+h+'.json');saved.parent.mkdir(exist_ok=True);saved.write_bytes(previous.read_bytes())
        history=old.get('previous_manifest_hashes',[])+[h]
    finished={(a['ticker'],a['date']) for a in records};sampled=quote_samples(anchors,config['seed'])
    calendar=xcals.get_calendar("XNYS",start=config["start"],end=config["end"]);grid=calendar.sessions
    try:
        for a in anchors:
            if (a['ticker'],a['date']) in finished:continue
            date=a["date"]
            if not config["start"]<=date<=config["end"]:raise ValueError("Option anchor crosses approved history")
            nominal=nominal_spot(store,a,config)
            if nominal is None:
                records.append({**a,'status':'nominal_underlying_unavailable','selections':{}});continue
            a=nominal
            rows=store.pages("historical chain "+a["ticker"]+" "+date,"/v3/reference/options/contracts",
                {"underlying_ticker":a["ticker"],"as_of":date,"expired":"false","expiration_date.gte":(pd.Timestamp(date)+pd.Timedelta(days=21)).strftime("%Y-%m-%d"),
                 "expiration_date.lte":(pd.Timestamp(date)+pd.Timedelta(days=180)).strftime("%Y-%m-%d"),"limit":1000},optional=True)
            if rows is None:
                records.append({**a,"status":"chain_access_unavailable","selections":{}});continue
            selection=select(rows,a,config)
            for bucket,s in selection.items():
                for role,contract in s["legs"].items():
                    path="/v2/aggs/ticker/"+quote(contract["ticker"],safe="")+"/range/1/day/"+config["start"]+"/"+config["end"]
                    params={"adjusted":"true","sort":"asc","limit":50000}
                    store.pages("option bars "+contract["ticker"],path,params,optional=True)
                    contract["bars_object"]=identity({"path":path,"params":params})
                    contract["quote_objects"]={}
                    if role.startswith("atm") and (a['ticker'],a['date']) in sampled:
                        session=grid.get_indexer([pd.Timestamp(date)])[0]
                        samples=[("decision",session,"close"),("next_open",session+1,"open")]+[("exit_"+str(h),session+h,"close") for h in config["horizons"]]
                        for name,index,clock in samples:
                            if index>=len(grid):continue
                            day=grid[index]
                            cutoff=(calendar.session_close(day)-pd.Timedelta(minutes=1)) if clock=="close" else (calendar.session_open(day)+pd.Timedelta(minutes=2))
                            qp="/v3/quotes/"+quote(contract["ticker"],safe="");params={"timestamp.gte":int(cutoff.value)-60*10**9,"timestamp.lte":int(cutoff.value),"order":"desc","sort":"timestamp","limit":1}
                            store.pages("bounded quote "+contract["ticker"],qp,params,optional=True,paginate=False)
                            contract["quote_objects"][name]={"object":identity({"path":qp,"params":params,"paginate":False}),"cutoff_ns":int(cutoff.value)}
            records.append({**a,"selections":selection,"status":"served" if selection else "no_standard_contract"})
            print(f"Option anchors {len(records)}/{len(anchors)}; requests {store.calls}",flush=True)
    finally:
        source={"schema":1,"requests_sha256":digest(requests),"settings":config,"records":records,"objects":store.entries,"failures":store.failures,
                "complete":len(records)==len(anchors),"finished_at":now(),"calls":store.calls,'quote_sampling':sampling,
                'quote_sample_anchors':len(sampled),'previous_manifest_hashes':history,'contract_query_policy':'active_at_historical_as_of',
                'spot_policy':'unadjusted_same_session_underlying',
                'acquisition_code':{Path(__file__).name:digest(Path(__file__)),'atlas_data.py':digest(Path(__file__).with_name('atlas_data.py'))}}
        source["source_id"]=identity(source);write_json(output/"options-source.json",source)


def quote_mark(rows,cutoff):
    candidates=[r for r in rows if cutoff-60*10**9<=r.get("sip_timestamp",0)<=cutoff]
    if not candidates:return None
    q=max(candidates,key=lambda r:(r["sip_timestamp"],r.get("sequence_number",0)))
    bid,ask=q.get("bid_price",0),q.get("ask_price",0)
    if not 0<bid<=ask or min(q.get("bid_size",0),q.get("ask_size",0))<1:return None
    return {"mid":(bid+ask)/2,"relative_spread":(ask-bid)/((bid+ask)/2),"age_seconds":(cutoff-q["sip_timestamp"])/1e9,"timestamp":q["sip_timestamp"]}


def build_option_panel(panel, folder):
    folder=Path(folder);s=read_json(folder/"options-source.json")
    if identity({k:v for k,v in s.items() if k!="source_id"})!=s["source_id"]:raise ValueError("Option source changed")
    objects={}
    for key,r in s["objects"].items():
        p=folder/r["file"]
        if digest(p)!=r["sha256"]:raise ValueError("Option object changed")
        objects[key]=read_json(p)
    # Six observed same-session inputs: normalized paired premium and sqrt-T
    # normalization in each maturity bucket. These are trade-mark proxies, not IV.
    values=np.full((len(panel),6),np.nan);readings=[];lookup={(r.ticker,str(r.date.date())):i for i,r in panel.iterrows()}
    for record in s["records"]:
        i=lookup.get((record["ticker"],record["date"]))
        if i is None:continue
        for column,bucket in enumerate(s["settings"]["option_buckets"]):
            selection=record["selections"].get(bucket)
            if not selection:continue
            legs=selection["legs"];marks=[same_day_bar(objects.get(legs[role]["bars_object"],[]),record["date"]) for role in ["atm_call","atm_put"]]
            row={"ticker":record["ticker"],"date":record["date"],"bucket":bucket,"role":record["role"],"status":"missing_same_session_marks"}
            if all(m is not None for m in marks):
                premium=sum(m["c"] for m in marks)/record["stock_close"];values[i,2*column:2*column+2]=[premium,premium/np.sqrt(selection["dte"]/365.25)]
                row.update(status="observed_trade_mark_proxy",normalized_premium=premium)
                for h in s["settings"]["horizons"]:
                    j=i+h
                    if j>=len(panel) or panel.iloc[j].ticker!=record["ticker"]:continue
                    day=str(panel.iloc[j].date.date());exit_marks=[same_day_bar(objects.get(legs[r]["bars_object"],[]),day) for r in ["atm_call","atm_put"]]
                    row["premium_change_"+str(h)]=sum(m["c"] for m in exit_marks)/sum(m["c"] for m in marks)-1 if all(m is not None for m in exit_marks) else None
            for stale in [1,3]:
                for role in ["atm_call","atm_put"]:
                    prior=[same_day_bar(objects.get(legs[role]["bars_object"],[]),str(panel.iloc[i-d].date.date())) for d in range(stale+1) if i-d>=0 and panel.iloc[i-d].ticker==record["ticker"]]
                    row[f"{role}_max_staleness_{stale}_covered"]=any(m is not None for m in prior)
            for sample in ['decision','next_open']+['exit_'+str(h) for h in s['settings']['horizons']]:
                quotes=[]
                for role in ["atm_call","atm_put"]:
                    ref=legs[role]["quote_objects"].get(sample)
                    q=quote_mark(objects.get(ref["object"],[]),ref["cutoff_ns"]) if ref else None;quotes.append(q)
                    for field in ['mid','relative_spread','age_seconds']:
                        row[f'{sample}_{role}_{field}']=q[field] if q else None
                row[sample+'_fresh_paired_quote']=all(q is not None for q in quotes)
                if row[sample+'_fresh_paired_quote']:
                    row[sample+'_leg_synchrony_seconds']=abs(quotes[0]['timestamp']-quotes[1]['timestamp'])/1e9
            row['fresh_paired_quote']=row['decision_fresh_paired_quote']
            row['leg_synchrony_seconds']=row.get('decision_leg_synchrony_seconds')
            readings.append(row)
    return values,readings,s


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--requests",required=True);p.add_argument("--output",required=True);p.add_argument("--budget",type=int,default=5000);a=p.parse_args();acquire(a.requests,a.output,a.budget)
