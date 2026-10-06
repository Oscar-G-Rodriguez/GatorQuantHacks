"""Non-secret packaging, scheduling and verified PC return for H22."""
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

from research import ROOT, HERE, REGISTRATION, verify_manifest, receipt, scheduled
from discovery.io import digest, identity, read_json, write_json, now, remote_base



def code_files():
    files = list(HERE.glob("*.py")) + list(HERE.glob("*.md")) + [HERE/"settings.json"]
    files += [ROOT / p for p in ["discovery/__init__.py","discovery/io.py","discovery/mechanism_data.py",
              "discovery/mechanism_engine.py","pyproject.toml","uv.lock",".python-version"]]
    files += list((ROOT/"tests").glob("test_h22*.py"))
    return files


def jobs(run, phase):
    run=Path(run).resolve(); rel=run.relative_to(ROOT).as_posix(); runner=HERE.relative_to(ROOT).as_posix()+"/backtest.py"
    base=remote_base();remote=base+"/h22-"+run.name
    remote_python=base+"/atlas-v3/.venv/bin/python"
    directory=run/"hpg";directory.mkdir(exist_ok=True)
    allocation=f"""#!/bin/bash
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4gb
#SBATCH --time=02:00:00
#SBATCH --chdir={remote}
"""
    tasks=read_json(run/"tasks.json") if (run/"tasks.json").exists() else []
    stages={"prepare":f'"{remote_python}" -B "{runner}" prepare --run "{rel}"',
            "return-prepare":f'"{remote_python}" -B "{runner}" export --run "{rel}"'} if phase=="prepare" else {
            "pilot":f'"{remote_python}" -B "{runner}" run --run "{rel}" --task "$SLURM_ARRAY_TASK_ID"',
            "run":f'"{remote_python}" -B "{runner}" run --run "{rel}" --task "$SLURM_ARRAY_TASK_ID"',
            "analyze":f'"{remote_python}" -B "{runner}" analyze --run "{rel}"',
            "return":f'"{remote_python}" -B "{runner}" export --run "{rel}"'}
    for name, command in stages.items():
        content=allocation+f"#SBATCH --job-name=h22-{name}\n#SBATCH --output={remote}/h22-{phase}-{name}-%A-%a.out\n"
        if name=="pilot": content+="#SBATCH --array=0-3%4\n"
        if name=="run": content+=f"#SBATCH --array=0-{len(tasks)-1}%16\n"
        content+='set -euo pipefail\nexport OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1\n'
        content+=command+"\n"
        (directory/(name+".sbatch")).write_text(content,encoding="utf-8",newline="\n")


def freeze(run, phase):
    run=Path(run).resolve(); run.mkdir(parents=True,exist_ok=True)
    if (run/"manifest.json").exists(): raise ValueError("Immutable run already frozen; use a new directory")
    subprocess.run(["git","cat-file","-e",REGISTRATION+":Hypotheses/H22 - Debt Financing Resolution Covered Calls/Experiment Plan.md"],cwd=ROOT,check=True)
    if phase=="prepare":
        src=ROOT/"data/cache/disclosure-atlas/source-v1"
        shutil.copytree(src,run/"input/source",ignore=shutil.ignore_patterns("attempts","history"))
    else:
        if not (run/"prepared/anchors.json").exists() or not (run/"acquisition/source.json").exists():
            raise ValueError("Preparation and acquisition must precede backtest freeze")
        cfg=read_json(HERE/"settings.json")
        tasks=[]
        for v in cfg["variants"]:
            for costs,assignment in [(1,"time_value"),(2,"time_value"),(1,"any_itm")]:
                tasks.append({"task":len(tasks),"variant":v["id"],"costs":costs,"assignment":assignment})
        write_json(run/"tasks.json",tasks)
    jobs(run,phase)
    paths=code_files()+[p for p in run.rglob("*") if p.is_file() and p.name!="manifest.json"]
    files={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
    m={"schema":1,"study":"H22","phase":phase,"registration_commit":REGISTRATION,
       "code_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
       "created_at":now(),"files":files,"remote":remote_base()+"/h22-"+run.name,"run":run.relative_to(ROOT).as_posix(),
       "prior_exposure":"2022-2025 and January-August2026 exposed; no fresh confirmation"}
    m["manifest_id"]=identity(m);write_json(run/"manifest.json",m)
    print(json.dumps({"manifest_id":m["manifest_id"],"files":len(files)}))


def bundle(run, output):
    run=Path(run).resolve();m=verify_manifest(run);output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    files={**m["files"],(run/"manifest.json").relative_to(ROOT).as_posix():digest(run/"manifest.json")}
    with tarfile.open(output,"w:gz") as tar:
        for relative in sorted(files): tar.add(ROOT/relative,arcname=relative,recursive=False)
    h=digest(output)
    installer=output.with_name(output.stem+"-install.py")
    script='''from pathlib import Path
import hashlib, json, os, tarfile
bundle=Path(__file__).with_name(BUNDLE)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
if sha(bundle)!=ARCHIVE_SHA:raise ValueError('Whole transfer hash differs')
dest=Path(DEST);dest.mkdir(parents=True,exist_ok=True);os.chmod(dest,0o700)
with tarfile.open(bundle,'r:gz') as tar:
 members=tar.getmembers()
 if len(members)!=len(FILES) or {m.name for m in members}!=set(FILES):raise ValueError('Member set differs')
 for m in members:
  target=(dest/m.name).resolve()
  if not m.isfile() or not target.is_relative_to(dest.resolve()) or '.env' in Path(m.name).parts:raise ValueError('Unsafe member')
  content=tar.extractfile(m).read()
  if hashlib.sha256(content).hexdigest()!=FILES[m.name]:raise ValueError('Member hash differs')
  if target.exists() and sha(target)!=FILES[m.name]:raise ValueError('Immutable member conflicts: '+m.name)
 for m in members:
  target=dest/m.name
  if target.exists():continue
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read());os.chmod(target,0o600)
print('Verified and installed',len(members),'H22 members',flush=True)
'''
    prefix=f"BUNDLE={output.name!r}\nARCHIVE_SHA={h!r}\nDEST={m['remote']!r}\nFILES={files!r}\n"
    installer.write_text(prefix+script,encoding="utf-8",newline="\n")
    print(json.dumps({"bundle":str(output),"sha256":h,"installer":str(installer),"installer_sha256":digest(installer),"bytes":output.stat().st_size}))


def terminal_receipts(run, m):
    """A return cannot silently omit unfinished tasks or altered checkpoints."""
    run=Path(run)
    required={"prepare"} if m["phase"]=="prepare" else {
        "analysis", *{f"task-{t['task']}" for t in read_json(run/"tasks.json")}}
    available={p.stem for p in (run/"receipts").glob("*.json")}
    if not required <= available:
        raise ValueError("Unfinished stages: "+", ".join(sorted(required-available)))
    checked={}
    for name in sorted(available):
        p=run/"receipts"/(name+".json");r=read_json(p)
        if r["manifest_id"]!=m["manifest_id"] or r["status"]!="completed":
            raise ValueError("Stage is not completed under this manifest: "+name)
        for relative,h in r["files"].items():
            target=(run/relative).resolve()
            if not target.is_relative_to(run.resolve()) or digest(target)!=h:
                raise ValueError("Returned stage member changed")
        checked[p.relative_to(run).as_posix()]=digest(p)
    return checked


def export(run):
    scheduled();run=Path(run).resolve();m=verify_manifest(run)
    terminal_receipts(run,m)
    stage="prepare" if m["phase"]=="prepare" else "backtest"
    files={}
    for folder in (["prepared","receipts"] if stage=="prepare" else ["prepared","results","receipts"]):
        files.update({p.relative_to(run).as_posix():digest(p) for p in (run/folder).rglob("*") if p.is_file()})
    export_receipt={"manifest_id":m["manifest_id"],"registration_commit":REGISTRATION,"code_commit":m["code_commit"],"files":files,"stage":stage,"export_job_id":os.environ["SLURM_JOB_ID"]}
    write_json(run/"return.json",export_receipt)
    archive=ROOT/("returned-h22-"+stage+".zip")
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for relative in sorted(files):z.write(run/relative,relative)
        z.write(run/"return.json","return.json")
    h=digest(archive);archive.with_suffix(".sha256").write_text(h+"  "+archive.name+"\n")
    print(json.dumps({"archive":archive.name,"sha256":h,"members":len(files)+1}),flush=True)


def import_return(archive, run, expected):
    archive=Path(archive);run=Path(run)
    if digest(archive)!=expected:raise ValueError("Whole return hash differs")
    m=read_json(run/"manifest.json")
    with zipfile.ZipFile(archive) as z:
        r=json.loads(z.read("return.json"))
        if r["manifest_id"]!=m["manifest_id"]:raise ValueError("Return manifest differs")
        if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(r["files"])|{"return.json"}:raise ValueError("Return members differ")
        for relative,h in r["files"].items():
            target=(run/relative).resolve()
            if not target.is_relative_to(run.resolve()) or hashlib.sha256(z.read(relative)).hexdigest()!=h:raise ValueError("Return member invalid")
            if target.exists() and digest(target)!=h:raise ValueError("Existing returned member conflicts")
        for relative in r["files"]:
            target=run/relative;target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():target.write_bytes(z.read(relative))
        (run/"return.json").write_bytes(z.read("return.json"))
    retained=run/"returned"/archive.name;retained.parent.mkdir(exist_ok=True)
    if not retained.exists():shutil.copy2(archive,retained)
    write_json(run/"import-receipt.json",{"verified_at":now(),"sha256":expected,"manifest_id":m["manifest_id"],"members":len(r["files"])+1})
    print("Verified",len(r["files"])+1,"returned members")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("action",choices=["freeze","bundle","import"])
    p.add_argument("--run",required=True);p.add_argument("--phase",choices=["prepare","backtest"],default="prepare")
    p.add_argument("--output");p.add_argument("--archive");p.add_argument("--sha256")
    a=p.parse_args()
    if a.action=="freeze":freeze(a.run,a.phase)
    elif a.action=="bundle":bundle(a.run,a.output)
    else:import_return(a.archive,a.run,a.sha256)
