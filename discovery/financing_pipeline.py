"""Standard-library-only immutable packaging, scheduler scripts and PC return."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile

from discovery.io import ROOT,digest,identity,read_json,write_json,now,remote_base

REGISTRATION="b4159e2917248d588072ef5d9ae55bd88c3f8063"
CONFIG=ROOT/"config/financing-round2.json"


def verify(run):
    m=read_json(Path(run)/"manifest.json")
    if m["registration_commit"]!=REGISTRATION or m["manifest_id"]!=identity({k:v for k,v in m.items() if k!="manifest_id"}):
        raise ValueError("Frozen identity changed")
    for relative,h in m["files"].items():
        p=(ROOT/relative).resolve()
        if not p.is_relative_to(ROOT.resolve()) or digest(p)!=h:raise ValueError("Frozen file changed: "+relative)
    return m


def code_files(phase="backtest"):
    cfg=read_json(CONFIG)
    tracked=set(subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True).splitlines())
    paths=[CONFIG,ROOT/"docs/massive/financing-round2-plan.md",ROOT/"pyproject.toml",ROOT/"uv.lock",ROOT/".python-version"]
    coverage_plan=ROOT/"docs/massive/financing-round2-coverage-plan.md"
    if coverage_plan.exists():paths.append(coverage_plan)
    paths += [ROOT/p for p in ["discovery/__init__.py","discovery/io.py","discovery/mechanism_data.py","discovery/mechanism_engine.py"]]
    paths += ([ROOT/"discovery"/name for name in ["financing_research.py","financing_pipeline.py","financing_acquire.py"]] if phase=="prepare" else [p for p in (ROOT/"discovery").glob("financing_*.py") if p.relative_to(ROOT).as_posix() in tracked])
    paths += ([ROOT/"tests"/name for name in ["test_financing_research.py","test_financing_pipeline.py"]] if phase=="prepare" else [p for p in (ROOT/"tests").glob("test_financing*.py") if p.relative_to(ROOT).as_posix() in tracked])
    for study in cfg["studies"]:
        folder=ROOT/"Hypotheses"/study["folder"]
        paths += [p for p in folder.glob("*") if p.is_file() and p.suffix in {".py",".md",".json"} and p.name not in {"Paper.md"}]
        paths += list((folder/"strategies").glob("*.py"))
    return sorted(set(paths))


def jobs(run,phase):
    run=Path(run).resolve();relative=run.relative_to(ROOT).as_posix();base=remote_base();remote=base+"/"+run.name
    remote_python=base+"/atlas-v3/.venv/bin/python"
    directory=run/"hpg";directory.mkdir(exist_ok=True)
    common=f'''#!/bin/bash
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8gb
#SBATCH --time=02:00:00
#SBATCH --chdir={remote}
'''
    if phase=="prepare":stages={"prepare":("prepare",None),"return":("export",None)}
    else:stages={"pilot":("run",list(range(min(4,len(read_json(run/"tasks.json")))))),
        "run":("run",list(range(len(read_json(run/"tasks.json"))))),"analyze":("analyze",None),"calibration":("calibration",None),"return":("export",None)}
    for name,(stage,array) in stages.items():
        content=common+f"#SBATCH --job-name=fin2-{name}\n#SBATCH --output={remote}/fin2-{name}-%A-%a.out\n"
        if array is not None:content+=f"#SBATCH --array={','.join(map(str,array))}%{4 if name=='pilot' else 16}\n"
        content+='set -euo pipefail\nexport OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1\n'
        content+=f'"{remote_python}" -B -m discovery.financing_pipeline exec --stage {stage} --run "{relative}"'
        if array is not None:content+=' --task "$SLURM_ARRAY_TASK_ID"'
        content+='\n';(directory/(name+".sbatch")).write_text(content,encoding="utf-8",newline="\n")


def freeze(run,phase,scope="full",prepared=None):
    run=Path(run).resolve();run.mkdir(parents=True,exist_ok=True)
    if not run.is_relative_to(ROOT.resolve()):raise ValueError("Run outside repository workspace")
    if (run/"manifest.json").exists():raise ValueError("Immutable run already frozen; choose a new directory")
    cfg=read_json(CONFIG)
    for study in cfg["studies"]:
        subprocess.run(["git","cat-file","-e",REGISTRATION+":Hypotheses/"+study["folder"]+"/Hypothesis.md"],cwd=ROOT,check=True)
    subprocess.run(["git","merge-base","--is-ancestor",REGISTRATION,"HEAD"],cwd=ROOT,check=True)
    if phase=="prepare":
        shutil.copytree(ROOT/"data/cache/disclosure-atlas/source-v1",run/"input/source",ignore=shutil.ignore_patterns("attempts","history"),dirs_exist_ok=False)
    else:
        if prepared is not None:
            src=Path(prepared);shutil.copytree(src/"prepared",run/"prepared",dirs_exist_ok=False)
        if not (run/"prepared/anchors.json").exists() or not (run/"acquisition/source.json").exists():
            raise ValueError("Returned preparation and local acquisition required")
        source=read_json(run/"acquisition/source.json")
        if not source.get("complete") or source["anchors_sha256"]!=digest(run/"prepared/anchors.json") or source["settings_sha256"]!=digest(CONFIG):
            raise ValueError("Incomplete or mismatched acquisition cannot be frozen")
        specs=cfg["pilot_task_spec"] if scope=="pilot" else [[s["id"],v["id"]] for s in cfg["studies"] for v in cfg["variants"]]
        write_json(run/"tasks.json",[{"task":i,"study":s,"variant":v} for i,(s,v) in enumerate(specs)])
    jobs(run,phase)
    paths=code_files(phase)+[p for p in run.rglob("*") if p.is_file() and p.name!="manifest.json" and "history" not in p.relative_to(run).parts and "attempts" not in p.relative_to(run).parts]
    files={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
    m={"schema":1,"study":"financing-round2","phase":phase,"scope":scope,"registration_commit":REGISTRATION,
       "code_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"created_at":now(),
       "files":files,"remote":remote_base()+"/"+run.name,"run":run.relative_to(ROOT).as_posix(),
       "prior_exposure":cfg["exposed_windows"],"fresh_final_oos_available":False}
    m["manifest_id"]=identity(m);write_json(run/"manifest.json",m);print(json.dumps({"manifest_id":m["manifest_id"],"files":len(files)}),flush=True)


def bundle(run,output):
    run=Path(run).resolve();m=verify(run);output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    files={**m["files"],(run/"manifest.json").relative_to(ROOT).as_posix():digest(run/"manifest.json")}
    with tarfile.open(output,"w:gz") as tar:
        for relative in sorted(files):tar.add(ROOT/relative,arcname=relative,recursive=False)
    installer=output.with_name(output.stem+"-install.py")
    script='''from pathlib import Path
import hashlib, os, tarfile
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
bundle=Path(__file__).with_name(BUNDLE)
if sha(bundle)!=ARCHIVE_SHA:raise ValueError('Whole archive hash differs')
dest=Path(DEST);dest.mkdir(parents=True,exist_ok=True);os.chmod(dest,0o700)
with tarfile.open(bundle,'r:gz') as tar:
 members=tar.getmembers()
 if len(members)!=len(FILES) or {m.name for m in members}!=set(FILES):raise ValueError('Member set differs')
 for m in members:
  target=(dest/m.name).resolve()
  if not m.isfile() or not target.is_relative_to(dest.resolve()) or '.env' in Path(m.name).parts:raise ValueError('Unsafe archive member')
  content=tar.extractfile(m).read()
  if hashlib.sha256(content).hexdigest()!=FILES[m.name]:raise ValueError('Member hash differs')
  if target.exists() and sha(target)!=FILES[m.name]:raise ValueError('Immutable destination conflict')
 for m in members:
  target=dest/m.name
  if target.exists():continue
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read());os.chmod(target,0o600)
print('Verified and installed',len(members),'financing members',flush=True)
'''
    installer.write_text(f"BUNDLE={output.name!r}\nARCHIVE_SHA={digest(output)!r}\nDEST={m['remote']!r}\nFILES={files!r}\n"+script,encoding="utf-8",newline="\n")
    metadata={"bundle":str(output),"sha256":digest(output),"installer":str(installer),"installer_sha256":digest(installer),"bytes":output.stat().st_size}
    write_json(run/"transfer.json",metadata);print(json.dumps(metadata),flush=True)


def export(run):
    from discovery.financing_research import scheduled
    scheduled();run=Path(run);m=verify(run)
    expected=["prepare"] if m["phase"]=="prepare" else ["analysis"]+["task-"+str(t["task"]) for t in read_json(run/"tasks.json")]
    for name in expected:
        r=read_json(run/"receipts"/(name+".json"))
        if r.get("status")!="completed" or r.get("manifest_id")!=m["manifest_id"]:raise ValueError("Unfinished or mismatched stage: "+name)
        for relative,h in r["files"].items():
            p=(run/relative).resolve()
            if not p.is_relative_to(run.resolve()) or digest(p)!=h:raise ValueError("Stage output hash differs")
    folders=["prepared","receipts"] if m["phase"]=="prepare" else ["prepared","results","receipts"]
    files={p.relative_to(run).as_posix():digest(p) for folder in folders for p in (run/folder).rglob("*") if p.is_file()}
    r={"manifest_id":m["manifest_id"],"registration_commit":REGISTRATION,"code_commit":m["code_commit"],
       "scope":m["scope"],"stage":m["phase"],"files":files,"export_job_id":os.environ["SLURM_JOB_ID"]}
    write_json(run/"return.json",r)
    archive=ROOT/("returned-"+run.name+".zip")
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for relative in sorted(files):z.write(run/relative,relative)
        z.write(run/"return.json","return.json")
    archive.with_suffix(".sha256").write_text(digest(archive)+"  "+archive.name+"\n")
    print(json.dumps({"archive":archive.name,"sha256":digest(archive),"members":len(files)+1}),flush=True)


def import_return(archive,run,expected):
    archive=Path(archive);run=Path(run)
    if digest(archive)!=expected:raise ValueError("Whole return archive differs")
    m=read_json(run/"manifest.json")
    if m.get("registration_commit")!=REGISTRATION or m.get("manifest_id")!=identity({k:v for k,v in m.items() if k!="manifest_id"}):
        raise ValueError("Local manifest identity differs")
    with zipfile.ZipFile(archive) as z:
        r=json.loads(z.read("return.json"))
        if r["manifest_id"]!=m["manifest_id"]:raise ValueError("Return belongs to another manifest")
        if r.get("registration_commit")!=m["registration_commit"] or r.get("code_commit")!=m["code_commit"] or r.get("scope")!=m["scope"]:
            raise ValueError("Returned research provenance differs")
        if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(r["files"])|{"return.json"}:raise ValueError("Return member set differs")
        for relative,h in r["files"].items():
            p=(run/relative).resolve()
            if not p.is_relative_to(run.resolve()) or hashlib.sha256(z.read(relative)).hexdigest()!=h:raise ValueError("Returned member invalid")
            if p.exists() and digest(p)!=h:raise ValueError("Existing return output conflicts")
        for relative in r["files"]:
            p=run/relative;p.parent.mkdir(parents=True,exist_ok=True)
            if not p.exists():p.write_bytes(z.read(relative))
        (run/"return.json").write_bytes(z.read("return.json"))
    target=run/"returned"/archive.name;target.parent.mkdir(exist_ok=True)
    if not target.exists():shutil.copy2(archive,target)
    write_json(run/"import-receipt.json",{"verified_at":now(),"sha256":expected,"manifest_id":m["manifest_id"],"members":len(r["files"])+1,"files":r["files"]})
    print("Verified",len(r["files"])+1,"returned members",flush=True)


def execute(run,stage,task=0,replica=0,phase="development"):
    if phase=="final-oos":raise ValueError("No attested unseen confirmation/freeze; exposed data cannot be final OOS")
    from discovery.financing_research import scheduled,prepare,prepare_placebo
    scheduled()
    if stage=="prepare":prepare(run)
    elif stage=="placebo-prepare":prepare_placebo(run,replica)
    elif stage=="run":
        from discovery.financing_strategy import run_task
        run_task(run,task)
    elif stage=="calibration":
        from discovery.financing_analysis import calibration
        calibration(run)
    elif stage=="analyze":
        from discovery.financing_analysis import analyze
        analyze(run)
    elif stage=="export":export(run)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("action",choices=["freeze","bundle","import","exec"])
    p.add_argument("--run",required=True);p.add_argument("--phase",default="prepare",choices=["prepare","backtest","development","final-oos"])
    p.add_argument("--scope",choices=["full","pilot","coverage"],default="full");p.add_argument("--prepared")
    p.add_argument("--output");p.add_argument("--archive");p.add_argument("--sha256");p.add_argument("--task",type=int,default=0);p.add_argument("--replica",type=int,default=0)
    p.add_argument("--stage",choices=["prepare","run","analyze","export","placebo-prepare","calibration"]);a=p.parse_args()
    if a.action=="freeze":freeze(a.run,a.phase,a.scope,a.prepared)
    elif a.action=="bundle":bundle(a.run,a.output)
    elif a.action=="import":import_return(a.archive,a.run,a.sha256)
    else:execute(a.run,a.stage,a.task,a.replica,a.phase)


if __name__=="__main__":main()
