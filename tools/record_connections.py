"""Record verified connection-study outputs once, without model/statistic reruns."""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from discovery.connections import STUDIES, read_manifest
from discovery.io import ROOT, digest, identity, now, read_json


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--run",type=Path,required=True);a=p.parse_args()
    run=a.run.resolve();m=read_manifest(run);report=read_json(run/"report.json")
    if report["manifest_id"]!=m["manifest_id"]:raise ValueError("Wrong report identity")
    path=ROOT/"Hypotheses/EXPERIMENTS.csv"
    with path.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f);columns=reader.fieldnames;seen={r["experiment_id"] for r in reader}
    append=[];counts={};recorded=now()
    for study in m["studies"]:
        folder=run/"studies"/study;receipt=read_json(folder/"receipt.json")
        if receipt["manifest_id"]!=m["manifest_id"]:raise ValueError("Wrong task identity")
        for name,expected in receipt.get("files",{}).items():
            if digest(folder/name)!=expected:raise ValueError("Changed task output")
        if receipt["status"]=="complete":
            with (folder/"measurements.csv").open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
        else:rows=[{"status":"error","reason":receipt.get("error"),"method":"failed_folder_attempt"}]
        counts[study]=len(rows)
        for i,row in enumerate(rows):
            eid="connections-"+identity({"manifest":m["manifest_id"],"study":study,"row":i})[:24]
            if eid in seen:continue
            parameters={k:v for k,v in row.items() if v!=""}
            append.append({"experiment_id":eid,"registered_at":"","hypothesis_id":study,"registration_commit":"","code_commit":"",
                           "sample_or_fold":"2024–2025 statistical discovery; "+row.get("cohort",""),
                           "parameters":json.dumps(parameters,ensure_ascii=False,sort_keys=True),
                           "signal_and_fill_timing":"Assumed filing+1 calendar day; declared session offset; no fills",
                           "cost_model":"No trading or P&L","data_identity":m["manifest_id"],"outcome":row.get("status","error"),
                           "evidence_path":str((folder/"measurements.csv" if receipt["status"]=="complete" else folder/"receipt.json").relative_to(ROOT)).replace("\\","/"),
                           "notes":"Unregistered discovery. Recorded "+recorded+"; plans "+", ".join(m["plan_commits"])+"; immutable code/input hashes in manifest; pointwise/search/support limits in report."})
            seen.add(eid)
        log=ROOT/"Hypotheses"/STUDIES[study]/"Research Log.md"
        marker="<!-- connections:"+m["manifest_id"]+" -->"
        text=log.read_text(encoding="utf-8")
        if marker not in text:
            relative=str(Path("../../")/folder.relative_to(ROOT)).replace("\\","/")
            text=text.rstrip()+f"\n\n{marker}\n\n## {recorded}: {m['run_id']}\n\nActual HiPerGator task status: {receipt['status']}. Attempt records: {len(rows)}; measured: {receipt.get('measured',0)}. Returned bytes were verified against the frozen manifest before recording. [Folder output]({relative}/{'measurements.csv' if receipt['status']=='complete' else 'receipt.json'}), [shared report](../../{run.relative_to(ROOT).as_posix()}/REPORT.md), [identity](../../{run.relative_to(ROOT).as_posix()}/manifest.json). This is selected development discovery, with all sparse/failed cells retained, and does not register or confirm a trading strategy.\n"
            log.write_text(text,encoding="utf-8")
    with path.open("a",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writerows(append)
    print(json.dumps({"new_ledger_rows":len(append),"folder_counts":counts,"manifest_id":m["manifest_id"]}))


if __name__=="__main__":main()
