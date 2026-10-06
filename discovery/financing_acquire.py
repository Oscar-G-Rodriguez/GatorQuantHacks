"""PC-only resumable exact-request acquisition, without outcome calculations."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date,timedelta
from pathlib import Path
import shutil
import threading
from urllib.parse import quote

from discovery.io import ROOT,digest,identity,read_json,now
from discovery.mechanism_data import ApiCache,write_json,same_day_bar
from discovery.financing_research import CONFIG,REGISTRATION,choose_contract


class ReusingCache(ApiCache):
    """Reuse complete exact request identities only, never guessed compatibility."""
    def __init__(self,folder,cfg):
        super().__init__(folder,cfg);self.reusable={}
        base=ROOT/"data/cache/disclosure-atlas"
        manifests=[base/"source-v1/source.json",base/"options-v3/options-source.json"]
        manifests += list((ROOT/"data/cache/h22").glob("acquisition*/source.json"))
        manifests += list(base.glob("h22*/acquisition/source.json"))
        manifests += list(base.glob("financing*/acquisition/source.json"))
        for manifest in manifests:
            if not manifest.exists():continue
            source=read_json(manifest)
            for key,obj in source.get("objects",{}).items():
                if obj.get("spec"):
                    spec=obj["spec"];target=manifest.parent/"objects"/(key+".json")
                    complete=True
                else:
                    if not obj.get("path") or obj.get("params") is None:continue
                    spec={"path":obj["path"],"params":obj["params"],"paginate":obj.get("paginate",True)}
                    target=manifest.parent/obj.get("file","");complete=obj.get("complete",False)
                if complete and target.is_file() and obj.get("sha256"):
                    self.reusable[identity(spec)]=(target,obj,spec)

    def pages(self,label,path,params,paginate=True):
        spec={"path":path,"params":params,"paginate":paginate};key=identity(spec)
        with self.lock:
            if key in self.reusable and not (self.folder/(key+".json")).exists():
                p,obj,_=self.reusable[key]
                if digest(p)!=obj["sha256"]:raise ValueError("Reusable object hash differs")
                shutil.copy2(p,self.folder/(key+".json"))
                write_json(self.folder/(key+".receipt.json"),{"spec":spec,"sha256":obj["sha256"],
                    "rows":obj.get("rows"),"retrieved_at":obj.get("retrieved_at"),"reused_from":p.relative_to(ROOT).as_posix()})
        return super().pages(label,path,params,paginate)


def acquire(prepared,output,quotes=True,request_cap=None):
    prepared=Path(prepared);output=Path(output);cfg=read_json(CONFIG)
    if request_cap is not None:
        if not 0<request_cap<=cfg["acquisition_new_request_cap_phase"]:raise ValueError("Budget exceeds registration")
        cfg={**cfg,"acquisition_new_request_cap_phase":request_cap}
    anchors=read_json(prepared/"anchors.json");calendar=read_json(prepared/"calendar.json")
    variants={v["id"]:v for v in cfg["variants"]}
    cache=ReusingCache(output/"objects",cfg);lock=threading.RLock();records={};failures=[];known={}
    manifest=output/"source.json"
    if manifest.exists():
        old=read_json(manifest)
        if old["anchors_sha256"]!=digest(prepared/"anchors.json") or old["settings_sha256"]!=digest(CONFIG):
            raise ValueError("Resume prepared/settings identity differs")
        for key,obj in old["objects"].items():
            if digest(cache.folder/(key+".json"))!=obj["sha256"]:raise ValueError("Prior acquisition object changed")
        known.update(old["objects"]);records={r["anchor_id"]:r for r in old["records"]};failures=old["failures"]
        history=output/"history";history.mkdir(exist_ok=True);shutil.copy2(manifest,history/(digest(manifest)+".json"))
    quote_pairs=set()
    for year in range(2022,2026):
        possible={a["pair_id"] for a in anchors if a["role"]=="event" and a["date"].startswith(str(year))}
        quote_pairs.update(sorted(possible,key=lambda p:identity([cfg["seed"],p]))[:cfg["quote_pairs_per_year"]])

    def save(complete=False):
        with lock:
            with cache.lock:objects={**known,**cache.used}
            source={"study":"financing-round2","registration_commit":REGISTRATION,
                "anchors_sha256":digest(prepared/"anchors.json"),"settings_sha256":digest(CONFIG),
                "updated_at":now(),"complete":complete,"records":sorted(records.values(),key=lambda r:r["anchor_id"]),
                "objects":objects,"failures":failures,"required_anchors":len(anchors),"quotes_requested":quotes}
            source["source_id"]=identity(source);write_json(manifest,source)

    def work(a):
        aid=a["anchor_id"]
        if aid in records and records[aid]["status"] not in {"pending","request_failed"}:return
        result={**a,"status":"pending","quote_objects":{}}
        try:
            ticker=quote(a["ticker"],safe="");day=a["date"]
            stock,so=cache.pages("nominal shares "+a["ticker"],f"/v2/aggs/ticker/{ticker}/range/1/day/{cfg['start']}/{cfg['end']}",
                {"adjusted":"false","sort":"asc","limit":50000})
            result["stock_object"]=so;spot=same_day_bar(stock,day)
            if spot is None:result["status"]="missing_nominal_decision_bar"
            else:
                result["nominal_decision_close"]=spot["c"]
                kind="call" if a["shape"]=="covered_call" else "put"
                chain,co=cache.pages("as-of "+kind+" chain "+a["ticker"]+" "+day,"/v3/reference/options/contracts",
                    {"underlying_ticker":a["ticker"],"contract_type":kind,"as_of":day,"expired":"false",
                     "expiration_date.gte":str(date.fromisoformat(day)+timedelta(days=21)),
                     "expiration_date.lte":str(date.fromisoformat(day)+timedelta(days=180)),"limit":1000})
                result["chain_object"]=co
                contract=choose_contract(chain,day,spot["c"],variants[a["variant"]],a["shape"])
                if contract is None:result["status"]="no_standard_contract_within_rules"
                else:
                    result["contract"]=contract
                    _,bo=cache.pages("same contract nominal bars "+contract["ticker"],
                        f"/v2/aggs/ticker/{quote(contract['ticker'],safe='')}/range/1/day/{cfg['start']}/{cfg['end']}",
                        {"adjusted":"false","sort":"asc","limit":50000})
                    result["option_object"]=bo;result["status"]="bars_downloaded"
                    if quotes and a["variant"]=="primary" and a["pair_id"] in quote_pairs and a["role"] in {"event","ordinary"}:
                        for label,i in [("decision",a["session"]),("entry",a["entry_session"]),("exit",a["entry_session"]+cfg["primary_horizon"])]:
                            if i>=len(calendar["dates"]):continue
                            cutoff=calendar["clock"][calendar["dates"][i]]["close_ns"]
                            for leg,symbol in [("stock",a["ticker"]),("option",contract["ticker"])]:
                                try:
                                    _,qo=cache.pages("bounded "+leg+" "+label+" quote",f"/v3/quotes/{quote(symbol,safe='')}",
                                        {"timestamp.gte":cutoff-int(60e9),"timestamp.lte":cutoff,"sort":"timestamp","order":"desc","limit":1},paginate=False)
                                    result["quote_objects"][label+"_"+leg]={"object":qo,"cutoff_ns":cutoff}
                                except RuntimeError as error:
                                    result["quote_objects"][label+"_"+leg]={"failure":str(error)}
            with lock:records[aid]=result
        except Exception as error:
            result["status"]="request_failed";result["failure"]=str(error)
            with lock:
                records[aid]=result;failures.append({"anchor_id":aid,"at":now(),"error":str(error)})
    completed=0
    try:
        with ThreadPoolExecutor(max_workers=cfg["acquisition_workers"]) as pool:
            for future in as_completed([pool.submit(work,a) for a in anchors]):
                future.result();completed+=1
                if completed%25==0:
                    save();print(f"Financing acquisition {completed}/{len(anchors)} anchors; {len(cache.receipts)} new HTTP attempts",flush=True)
    finally:
        cache.save_receipts()
        save(len(records)==len(anchors) and all(r["status"] not in {"request_failed","pending"} for r in records.values()))
    print("Acquisition terminal records",len(records),"complete",read_json(manifest)["complete"],flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--prepared",required=True);p.add_argument("--output",required=True)
    p.add_argument("--skip-quotes",action="store_true");p.add_argument("--request-cap",type=int)
    args=p.parse_args();acquire(args.prepared,args.output,not args.skip_quotes,args.request_cap)


if __name__=="__main__":main()
