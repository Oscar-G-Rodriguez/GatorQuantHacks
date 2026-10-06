"""PC-only bounded/resumable Massive acquisition for frozen H22 anchors.

Contract selection uses decision-time chains and nominal spot. Downloading
later bars is preparation; their returns are evaluated only in scheduled jobs.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
import shutil
import sys
import threading
from urllib.parse import quote

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]));sys.path.insert(0,str(HERE))
from discovery.io import digest, identity, read_json, now
from discovery.mechanism_data import ApiCache, write_json, same_day_bar
from research import ROOT, REGISTRATION, choose_call


class ReusingCache(ApiCache):
    """Only reuse completed exact-query objects with verified hashes."""
    def __init__(self,folder,cfg):
        super().__init__(folder,cfg)
        self.reusable={}
        for directory in [ROOT/"data/cache/disclosure-atlas/options-v3",ROOT/"data/cache/disclosure-atlas/source-v1"]:
            manifest=directory/("options-source.json" if "options" in directory.name else "source.json")
            if not manifest.exists():continue
            s=read_json(manifest)
            for _,o in s.get("objects",{}).items():
                if o.get("complete") and o.get("path") and o.get("params") is not None:
                    spec={"path":o["path"],"params":o["params"],"paginate":True}
                    self.reusable[identity(spec)]=(directory/o["file"],o,spec)

    def pages(self,label,path,params,paginate=True):
        spec={"path":path,"params":params,"paginate":paginate};key=identity(spec)
        with self.lock:
            if key in self.reusable and not (self.folder/(key+".json")).exists():
                p,o,_=self.reusable[key]
                if digest(p)!=o["sha256"]:raise ValueError("Reusable source hash differs")
                shutil.copy2(p,self.folder/(key+".json"))
                write_json(self.folder/(key+".receipt.json"),{"spec":spec,"sha256":o["sha256"],"rows":o["rows"],
                    "retrieved_at":o["retrieved_at"],"reused_from":p.relative_to(ROOT).as_posix()})
        return super().pages(label,path,params,paginate)


def acquire(prepared, output, quotes=True):
    prepared=Path(prepared);output=Path(output);cfg=read_json(HERE/"settings.json")
    anchors=read_json(prepared/"anchors.json");calendar=read_json(prepared/"calendar.json")
    variants={v["id"]:v for v in cfg["variants"]}
    cache=ReusingCache(output/"objects",cfg);lock=threading.Lock();records={};failures=[];known_objects={}
    manifest_path=output/"source.json"
    if manifest_path.exists():
        old=read_json(manifest_path)
        if old["anchors_sha256"]!=digest(prepared/"anchors.json") or old["settings_sha256"]!=digest(HERE/"settings.json"):
            raise ValueError("Resume anchor/config identity differs")
        for key,o in old["objects"].items():
            if digest(cache.folder/(key+".json"))!=o["sha256"]:raise ValueError("Earlier acquired object changed")
        known_objects.update(old["objects"])
        records={r["anchor_id"]:r for r in old["records"]};failures=old["failures"]
        history=output/"history";history.mkdir(exist_ok=True);shutil.copy2(manifest_path,history/(digest(manifest_path)+".json"))
    selected_pairs=set()
    for year in range(2022,2026):
        positive={a["pair_id"] for a in anchors if a["role"]=="event" and a["date"].startswith(str(year))}
        selected_pairs.update(sorted(positive,key=lambda p:identity([cfg["seed"],p]))[:cfg["quote_pairs_per_year"]])

    def save(complete=False):
        with lock:
            # Receipts include reused entries even when this invocation did not
            # request them again; retained source objects remain auditable.
            with cache.lock: objects={**known_objects,**cache.used}
            source={"study":"H22","registration_commit":REGISTRATION,"anchors_sha256":digest(prepared/"anchors.json"),
                "settings_sha256":digest(HERE/"settings.json"),"updated_at":now(),"complete":complete,
                "records":sorted(records.values(),key=lambda r:r["anchor_id"]),"objects":objects,"failures":failures}
            source["source_id"]=identity(source);write_json(manifest_path,source)

    def work(a):
        aid=identity([a["pair_id"],a["variant"],a["role"],a["date"]])[:24]
        if aid in records and records[aid]["status"] not in {"request_failed","pending"}:return
        r={**a,"anchor_id":aid,"status":"pending","quote_objects":{}}
        try:
            t=quote(a["ticker"],safe="");d=a["date"]
            stock,so=cache.pages("nominal stock "+a["ticker"],f"/v2/aggs/ticker/{t}/range/1/day/{cfg['start']}/{cfg['end']}",
                                {"adjusted":"false","sort":"asc","limit":50000})
            r["stock_object"]=so
            spot=same_day_bar(stock,d)
            if spot is None:r["status"]="missing_nominal_decision_bar"
            else:
                r["nominal_decision_close"]=spot["c"]
                chain,co=cache.pages("historical call chain "+a["ticker"]+" "+d,"/v3/reference/options/contracts",
                    {"underlying_ticker":a["ticker"],"contract_type":"call","as_of":d,"expired":"false",
                     "expiration_date.gte":str(date.fromisoformat(d)+timedelta(days=21)),
                     "expiration_date.lte":str(date.fromisoformat(d)+timedelta(days=180)),"limit":1000})
                r["chain_object"]=co
                contract=choose_call(chain,d,spot["c"],variants[a["variant"]])
                if contract is None:r["status"]="no_standard_call_within_rules"
                else:
                    r["contract"]=contract
                    bars,bo=cache.pages("same contract bars "+contract["ticker"],f"/v2/aggs/ticker/{quote(contract['ticker'],safe='')}/range/1/day/{cfg['start']}/{cfg['end']}",
                                       {"adjusted":"false","sort":"asc","limit":50000})
                    r["option_object"]=bo;r["status"]="bars_downloaded"
                    if quotes and a["variant"]=="primary" and a["pair_id"] in selected_pairs and a["role"] in {"event","ordinary"}:
                        for label,i in [("entry",a["entry_session"]),("exit",a["entry_session"]+21)]:
                            if i>=len(calendar["dates"]):continue
                            day=calendar["dates"][i];cut=calendar["clock"][day]["close_ns"]
                            for leg,ticker in [("stock",a["ticker"]),("call",contract["ticker"])]:
                                try:
                                    _,qo=cache.pages("bounded "+leg+" "+label+" quote",f"/v3/quotes/{quote(ticker,safe='')}",
                                        {"timestamp.gte":cut-int(60e9),"timestamp.lte":cut,"sort":"timestamp","order":"desc","limit":1},paginate=False)
                                    r["quote_objects"][label+"_"+leg]={"object":qo,"cutoff_ns":cut}
                                except RuntimeError as error:
                                    r["quote_objects"][label+"_"+leg]={"failure":str(error)}
            with lock:records[aid]=r
        except Exception as error:
            r["status"]="request_failed";r["failure"]=str(error)
            with lock:
                records[aid]=r;failures.append({"anchor_id":aid,"at":now(),"error":str(error)})

    completed=0
    try:
        with ThreadPoolExecutor(max_workers=cfg["acquisition_workers"]) as pool:
            for future in as_completed([pool.submit(work,a) for a in anchors]):
                future.result();completed+=1
                if completed%25==0:
                    save(False)
                    print(f"H22 acquisition {completed}/{len(anchors)} anchors; {len(cache.receipts)} new requests",flush=True)
        save(len(records)==len(anchors) and all(r["status"]!="request_failed" for r in records.values()))
    finally:cache.save_receipts();save(False if completed<len(anchors) else len(records)==len(anchors) and all(r["status"]!="request_failed" for r in records.values()))
    print("H22 source records",len(records),"complete",read_json(manifest_path)["complete"],flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--prepared",required=True);p.add_argument("--output",required=True)
    p.add_argument("--skip-quotes",action="store_true");a=p.parse_args();acquire(a.prepared,a.output,not a.skip_quotes)
