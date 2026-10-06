"""Allowlisted H21 transfer, checkpointed scheduled work, and verified returns."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import re
import tarfile
import zipfile
import os
import shutil
from pathlib import Path
from .io import ROOT,digest,identity,now,read_json,write_json,safe_child,remote_base
from .atlas import manifest,cells,done
from .atlas_evidence import Evidence


def missing_tasks(run,stage):
    run=Path(run);c=manifest(run,allow_frozen=True)["settings"];count=len(cells(c))
    if stage=="search":mapping=[(i,f"core-{i:03d}") for i in range(count)]
    elif stage=="uncertainty":
        batches=math.ceil(c["resamples"]/c["resample_batch"])
        mapping=[(bi*batches+b,f"resample-{block}-{b:03d}") for bi,block in enumerate(c["block_lengths"]) for b in range(batches)]
    elif stage.startswith('placebo-'):
        start=int(stage.split('-')[1])*16;end=min(c['placebos'],start+16)
        mapping=[((replica-start)*count+i,f'placebo-{replica:03d}-{i:03d}') for replica in range(start,end) for i in range(count)]
    else:raise ValueError('Retry supports search, uncertainty, or a declared placebo wave')
    evidence=Evidence(run);m=manifest(run,allow_frozen=True)
    return [i for i,label in mapping if not evidence.completed(label,m['manifest_id'])]


def audit(run):
    """Receipt/hash reconciliation on PC; this performs no scientific fitting."""
    run=Path(run);m=manifest(run,allow_frozen=True);c=m['settings'];count=len(cells(c))
    expected=['coverage','patterns','options','option-requests','inference','placebo-summary','report']
    expected += [f'core-{i:03d}' for i in range(count)]
    expected += [f'placebo-{r:03d}-{i:03d}' for r in range(c['placebos']) for i in range(count)]
    expected += [f'resample-{block}-{b:03d}' for block in c['block_lengths'] for b in range(math.ceil(c['resamples']/c['resample_batch']))]
    failed=set()
    for p in run.glob('attempts/*.json'):
        a=read_json(p);args=a.get('arguments',[])
        action=next((x for x in args if x in ['core','pilot','placebo','resample']),None)
        def number(name,default=0):return int(args[args.index(name)+1]) if name in args else default
        task=number('--task')
        if action=='core':failed.add(f'core-{task:03d}')
        elif action=='placebo':failed.add(f'placebo-{number("--replica"):03d}-{task:03d}')
        elif action=='resample':failed.add(f'resample-{number("--block",63)}-{task:03d}')
    rows=[];evidence=Evidence(run)
    for label in expected:
        state='failed_attempt_preserved' if label in failed else 'pending'
        if evidence.completed(label,m['manifest_id']):state='completed'
        rows.append({'task':label,'state':state})
    counts={s:sum(r['state']==s for r in rows) for s in sorted({r['state'] for r in rows})}
    result={'manifest_id':m['manifest_id'],'checked_at':now(),'tasks':rows,'states':counts,
        'accepted':all(r['state']=='completed' for r in rows),'scientific_calculation_on_pc':False}
    write_json(run/'audit/task-states.json',result)
    return {k:v for k,v in result.items() if k!='tasks'}


def jobs(run,remote,stage="pilot",workers=4,memory=16,retry=False,inference_memory=128):
    run=Path(run).resolve();m=manifest(run,allow_frozen=True);c=m["settings"]
    if not re.fullmatch(re.escape(remote_base())+r"/atlas-[A-Za-z0-9_-]+",remote):raise ValueError("Use a new personal Blue atlas directory")
    if not 1<=workers<=64 or memory<4 or workers*memory>1800:raise ValueError("Resource request exceeds verified account envelope")
    if not memory<=inference_memory<=1800:raise ValueError('Aggregation memory must fit the verified account envelope')
    relative=run.relative_to(ROOT).as_posix();stage_id=stage if not retry else stage+'-retry-'+now().replace(':','')
    missing=missing_tasks(run,stage) if retry else None
    if retry and not missing:return {'stage':stage,'missing_tasks':0,'scripts':None}
    folder=run/"hpg"/stage_id;folder.mkdir(parents=True,exist_ok=False)
    header=f"""#!/bin/bash
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem={memory}gb
#SBATCH --time=02:00:00
#SBATCH --chdir={remote}
"""
    env=f"""set -euo pipefail
umask 077
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
unset PYTHONHOME PYTHONPATH
cd '{remote}'
"""
    def script(name,body,array=None):
        allocation=header.replace(f'--mem={memory}gb',f'--mem={inference_memory}gb') if name=='inference' else header
        content=allocation+f"#SBATCH --job-name=h21-{name}\n#SBATCH --output={remote}/h21-{name}-%A-%a.out\n"
        if array:content+=f"#SBATCH --array={','.join(map(str,missing))+'%'+str(workers) if retry else array}\n"
        (folder/(name+".sbatch")).write_text(content+env+body,encoding="utf-8",newline="\n")
    python=f".venv/bin/python -B -m discovery.atlas --run '{relative}' "
    # CLI action is positional; options preceding it are supported by argparse.
    if stage=="pilot":
        script("setup","module load python/3.12\nunset PYTHONHOME PYTHONPATH\nuv sync --frozen --python 3.11\n.venv/bin/python -B -m unittest discover -s tests -p 'test_atlas*.py' -v\n")
        script("coverage",python+"coverage\n"+python+"report\n")
        script("patterns",python+"patterns\n")
        # Fixed representative horizon/delay/outcome cells, selected before data outcomes.
        script("pilot","TASKS=(0 35 76 127)\n"+python+'pilot --task "${TASKS[$SLURM_ARRAY_TASK_ID]}"\n',"0-3%4")
        order=[("setup",None),("coverage","afterok:setup"),("patterns","afterok:coverage"),("pilot","afterok:patterns")]
    elif stage=="search":
        script("core",python+'core --task "$SLURM_ARRAY_TASK_ID"\n',f"0-{len(cells(c))-1}%{workers}")
        script("report",python+"report\n")
        order=[("core",None),("report","afterany:core")]
    elif stage=="uncertainty":
        count=math.ceil(c["resamples"]/c["resample_batch"])
        script("resample",f'BLOCKS=(63 126)\nBATCH=$((SLURM_ARRAY_TASK_ID % {count}))\nBLOCK=${{BLOCKS[$((SLURM_ARRAY_TASK_ID / {count}))]}}\n'+python+'resample --task "$BATCH" --block "$BLOCK"\n',f"0-{count*2-1}%{workers}")
        script("inference",python+"inference\n"+python+"report\n");order=[("resample",None),("inference","afterok:resample")]
    elif stage.startswith("placebo"):
        # One cell/year checkpoint per two-hour job, waves stay below 3000 queued.
        wave=int(stage.split("-")[1]);start=wave*16;end=min(c["placebos"],start+16)
        if start>=end:raise ValueError("Placebo wave outside declared replicas")
        count=len(cells(c));logical=(end-start)*count
        script("placebo",f'REPLICA=$(({start} + SLURM_ARRAY_TASK_ID / {count}))\nCELL=$((SLURM_ARRAY_TASK_ID % {count}))\n'+python+'placebo --replica "$REPLICA" --task "$CELL"\n',f"0-{logical-1}%{workers}")
        order=[("placebo",None)]
    else:raise ValueError("Unknown stage")
    script("return",f"IDS=$(sed -E 's/[a-z]+=//g;s/ /,/g' submission-{stage_id}.txt)\nsacct -j \"$IDS\" --parsable2 --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS > scheduler-{stage_id}.txt\n.venv/bin/python -B -m discovery.atlas_jobs export --run '{relative}' --output returned-{stage_id}.zip\nsha256sum returned-{stage_id}.zip > returned-{stage_id}.sha256\n")
    submit=["#!/bin/bash","set -euo pipefail",f"cd '{remote}'"]
    for name,dependency in order:
        deps="" if not dependency else "--dependency="+dependency.split(":")[0]+":$"+dependency.split(":")[1].upper()+" "
        submit.append(f"{name.upper()}=$(sbatch --parsable {deps}'{relative}/{folder.relative_to(run).as_posix()}/{name}.sbatch'); {name.upper()}=${{{name.upper()}%%;*}}")
    last=order[-1][0].upper();submit.append(f"RETURN=$(sbatch --parsable --dependency=afterany:${last} '{relative}/hpg/{stage_id}/return.sbatch'); RETURN=${{RETURN%%;*}}")
    names=[x[0] for x in order]+["return"];submit.append("printf '"+" ".join(n+"=%s" for n in names)+"\\n' "+" ".join('"$'+n.upper()+'"' for n in names)+f" | tee submission-{stage_id}.txt")
    (folder/"submit.sh").write_text("\n".join(submit)+"\n",encoding="utf-8",newline="\n")
    write_json(folder/"job-config.json",{"manifest_id":m["manifest_id"],"stage":stage,"workers":workers,"memory_gb":memory,"inference_memory_gb":inference_memory,"remote":remote,"seconds_limit":7200,"retry_tasks":missing,
        "verified_account_limits":{"cpus":250,"memory_mib":2000000,"observed_at":"2026-10-03","source":"authenticated slurmInfo/showQos"}})
    return {"scripts":str(folder),"stage":stage}


def bundle(run,output):
    run=Path(run).resolve();m=manifest(run,allow_frozen=True);s=read_json(ROOT/m["source"]/"source.json");source=ROOT/m["source"]
    names=set(m["code"])|{"docs/README.md","webull_bt/__init__.py"}
    names|={p.relative_to(ROOT).as_posix() for p in (run/"hpg").rglob("*") if p.is_file()}
    names.add((run/"manifest.json").relative_to(ROOT).as_posix())
    names|={(source/n).relative_to(ROOT).as_posix() for n in ["source.json",s["taxonomy_file"]]+[r["file"] for r in s["objects"].values()]}
    if m.get("options_source"):
        opt=ROOT/m["options_source"];osource=read_json(opt/"options-source.json")
        names|={(opt/n).relative_to(ROOT).as_posix() for n in ["options-source.json"]+[r["file"] for r in osource["objects"].values()]}
    output=Path(output)
    if output.exists():raise ValueError("Preserve immutable earlier package")
    selected={}
    for n in names:
        p=safe_child(ROOT,n)
        if n in m["code"] and digest(p)!=m["code"][n]:p=safe_child(run/"frozen-code",n)
        if n in m["code"] and digest(p)!=m["code"][n]:raise ValueError("Frozen bundle code differs")
        selected[n]=p
    hashes={n:digest(selected[n]) for n in sorted(names)};output.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(output,"w:gz") as a:
        for n in hashes:
            if any(x in Path(n).parts for x in [".env",".git",".venv"]):raise ValueError("Credential/runtime path denied")
            a.add(selected[n],arcname=n,recursive=False)
        raw=json.dumps({"manifest_id":m["manifest_id"],"files":hashes}).encode();info=tarfile.TarInfo("BUNDLE-FILES.json");info.size=len(raw);info.mode=0o600;a.addfile(info,io.BytesIO(raw))
    write_json(output.with_suffix(".receipt.json"),{"sha256":digest(output),"files":hashes,"manifest_id":m["manifest_id"],"bytes":output.stat().st_size})
    return {"sha256":digest(output),"bytes":output.stat().st_size,"files":len(hashes)}


def export(run,output):
    run=Path(run);m=manifest(run);output=Path(output)
    if output.exists():raise ValueError("Preserve old return")
    files={p.relative_to(run).as_posix():p for p in run.rglob("*") if p.is_file() and "hpg" not in p.relative_to(run).parts}
    for glob in ["h21-*.out","scheduler-*.txt","submission-*.txt"]:
        files.update({"scheduler/"+p.name:p for p in ROOT.glob(glob)})
    hashes={}
    with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as a:
        for n,p in files.items():
            if ".tmp" in p.name:continue
            raw=p.read_bytes();hashes[n]=hashlib.sha256(raw).hexdigest();a.writestr(n,raw)
        a.writestr("RETURN-RECEIPT.json",json.dumps({"manifest_id":m["manifest_id"],"files":hashes}))
    return {"sha256":digest(output),"files":len(hashes)}


def import_results(archive_path,run,expected,compressed_tasks=False):
    run=Path(run);m=manifest(run,allow_frozen=True)
    if digest(archive_path)!=expected:raise ValueError("Whole archive differs")
    pending=[];history=[];retained={}
    with zipfile.ZipFile(archive_path) as a:
        names=a.namelist()
        if len(names)!=len(set(names)):raise ValueError("Duplicate members")
        r=json.loads(a.read("RETURN-RECEIPT.json"))
        if r["manifest_id"]!=m["manifest_id"] or set(names)!=set(r["files"])|{"RETURN-RECEIPT.json"}:raise ValueError("Return identity/membership differs")
        for n,h in r["files"].items():
            path=safe_child(run,n);raw=a.read(n)
            if hashlib.sha256(raw).hexdigest()!=h:raise ValueError("Member hash differs")
            if path.exists() and digest(path)!=h:
                # Staged reports remain as dated source versions before replacement.
                staged_report=n in ["outputs/master.csv","outputs/comparisons.csv","outputs/trials.csv","outputs/atlas.html","outputs/summary.json","receipts/report.json"]
                scheduler_snapshot=n.startswith("scheduler/") and (n.endswith(".out") or Path(n).name.startswith("scheduler-"))
                if not staged_report and not scheduler_snapshot:raise ValueError("Immutable existing evidence differs: "+n)
                old=run/"return-history"/digest(path)/n;history.append((old,path.read_bytes()))
            keep=compressed_tasks and (n.startswith('tasks/') or n.startswith('uncertainty/')
                or any(n.startswith('receipts/'+prefix) for prefix in ['core-','pilot-','placebo-','resample-']))
            if keep:retained[n]=h
            else:pending.append((path,n))
    if retained:
        saved=run.resolve()/'archives'/(expected+'.zip');saved.parent.mkdir(parents=True,exist_ok=True)
        if not saved.exists():
            # Incoming Downloads can be read-only under the workspace sandbox.
            # Preserve the original and atomically install a verified local copy.
            temporary=saved.with_suffix('.incoming-'+now().replace(':','')+'.tmp')
            shutil.copyfile(Path(archive_path).resolve(),temporary)
            if digest(temporary)!=expected:raise ValueError('Copied archive differs')
            os.replace(temporary,saved)
        elif digest(saved)!=expected:raise ValueError('Existing retained archive changed')
        archive_path=saved
        index=read_json(run/'compressed-evidence.json') if (run/'compressed-evidence.json').exists() else {}
        for n,h in retained.items():
            if n in index and index[n]['member_sha256']!=h:raise ValueError('Immutable archived evidence differs')
            index[n]={'archive':'archives/'+saved.name,'archive_sha256':expected,'member_sha256':h}
        write_json(run/'compressed-evidence.json',index)
    for path,raw in history:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    with zipfile.ZipFile(archive_path) as a:
        for path,n in pending:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(a.read(n))
    write_json(run/"return-verifications"/(expected+".json"),{"archive_sha256":expected,"manifest_id":m["manifest_id"],"member_count":len(pending)+len(retained),"compressed_task_members":len(retained),"at":now()})
    return {"verified_members":len(pending)+len(retained),"compressed_task_members":len(retained)}


def record(run,table_index=False):
    run=Path(run).resolve();m=manifest(run,allow_frozen=True)
    if not list((run/"return-verifications").glob("*.json")):raise ValueError("Verify actual HiPerGator returned evidence first")
    path=ROOT/"Hypotheses/EXPERIMENTS.csv"
    with path.open(newline="",encoding="utf-8") as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;existing={r["experiment_id"] for r in reader}
    rows=[]
    observation=run/'transfer-observation.json'
    owned={str(v) for v in read_json(observation).get('submitted_jobs',{}).values()} if observation.exists() else set()
    for p in run.glob('scheduler/submission-*.txt'):
        owned.update(re.findall(r'=(\d+)',p.read_text()))
    for p in run.glob('scheduler/scheduler-*.txt'):
        with p.open(newline='',encoding='utf-8') as stream:
            for cell in csv.DictReader(stream,delimiter='|'):
                job=cell.get('JobID','');base=job.split('_')[0].split('.')[0]
                if base not in owned:continue
                eid='atlas-operation-'+identity({'manifest':m['manifest_id'],'path':p.relative_to(run).as_posix(),'cell':cell})[:24]
                if eid in existing:continue
                rows.append({'experiment_id':eid,'registered_at':m['created_at'],'hypothesis_id':'H21','registration_commit':'',
                    'code_commit':m['code_commit'],'sample_or_fold':'Operational scheduler accounting','parameters':json.dumps(cell,sort_keys=True),
                    'signal_and_fill_timing':'No signal or fill: scheduled attempt evidence','cost_model':'Not applicable',
                    'data_identity':m['manifest_id'],'outcome':cell.get('State','unknown'),'evidence_path':p.relative_to(ROOT).as_posix(),
                    'notes':'Verified private return; includes failed, interrupted and superseded attempts. Operational records are not scientific findings.'})
                existing.add(eid)
    evidence=Evidence(run);indexed=[]
    for name in evidence.tables():
        p=run/name
        if table_index:
            h=evidence.hash(name);counts={};total=0
            for cell in evidence.rows(name):
                total+=1;s=cell.get('status','recorded');counts[s]=counts.get(s,0)+1
            item={'table':name,'sha256':h,'complete_variant_rows':total,'states':counts,'compressed_member':evidence.index.get(name)}
            indexed.append(item)
            eid='atlas-table-'+identity({'manifest':m['manifest_id'],'table':name,'sha256':h})[:24]
            if eid not in existing:
                rows.append({'experiment_id':eid,'registered_at':m['created_at'],'hypothesis_id':'H21','registration_commit':'',
                    'code_commit':m['code_commit'],'sample_or_fold':'All chronological folds and attempted settings in linked complete table',
                    'parameters':json.dumps(item,sort_keys=True),'signal_and_fill_timing':'Declared assumed availability/delay; no fills',
                    'cost_model':'Not applicable: no trading simulation','data_identity':m['manifest_id'],'outcome':'complete_variant_table_index',
                    'evidence_path':(run/'audit/ledger-variant-index.json').relative_to(ROOT).as_posix(),
                    'notes':'Every measured, null, unsupported and failed row retained in the hash-verified table; index prevents duplicating large private trial archives into Git. Development exposure remains disclosed.'})
                existing.add(eid)
        else:
            for cell in evidence.rows(name):
                eid="atlas-"+identity({"manifest":m["manifest_id"],"path":p.relative_to(run).as_posix(),"cell":cell})[:24]
                if eid in existing:continue
                rows.append({"experiment_id":eid,"registered_at":m["created_at"],"hypothesis_id":"H21","registration_commit":"",
                    "code_commit":m["code_commit"],"sample_or_fold":cell.get("year","2022-2025 discovery"),"parameters":json.dumps(cell,sort_keys=True),
                    "signal_and_fill_timing":"Assumed filing+1 aligned close, declared extra delay; prediction research without fills",
                    "cost_model":"Not applicable: no trading simulation","data_identity":m["manifest_id"],"outcome":cell.get("status","recorded"),
                    "evidence_path":p.relative_to(ROOT).as_posix(),"notes":"Exploratory plan "+m["plan_commit"]+"; static universe, retrospective availability, prior adaptive exposure; not economic registration or alpha"})
                existing.add(eid)
    if table_index:write_json(run/'audit/ledger-variant-index.json',{'manifest_id':m['manifest_id'],'recorded_at':now(),'table_index':True,'tables':indexed})
    with path.open("a",newline="",encoding="utf-8") as stream:csv.DictWriter(stream,fieldnames=fields).writerows(rows)
    return {"new_records":len(rows)}


def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=["jobs","bundle","export","import","record","audit"]);p.add_argument("--run",required=True);p.add_argument("--output");p.add_argument("--remote");p.add_argument("--stage",default="pilot");p.add_argument("--workers",type=int,default=4);p.add_argument("--memory",type=int,default=16);p.add_argument('--inference-memory',type=int,default=128);p.add_argument("--archive");p.add_argument("--expected-sha");p.add_argument("--retry",action='store_true');p.add_argument('--retain-compressed-tasks',action='store_true');p.add_argument('--table-index',action='store_true');a=p.parse_args()
    if a.action=="jobs":r=jobs(a.run,a.remote,a.stage,a.workers,a.memory,a.retry,a.inference_memory)
    elif a.action=="bundle":r=bundle(a.run,a.output)
    elif a.action=="export":r=export(a.run,a.output)
    elif a.action=="import":r=import_results(a.archive,a.run,a.expected_sha,a.retain_compressed_tasks)
    elif a.action=='audit':r=audit(a.run)
    else:r=record(a.run,a.table_index)
    print(json.dumps(r))


if __name__=="__main__":main()
