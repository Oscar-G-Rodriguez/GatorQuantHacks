"""Allowlisted connection-study packaging, scheduled jobs and verified return."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
import zipfile
from pathlib import Path

from .connections import STUDIES, read_manifest
from .io import ROOT, digest, safe_child, write_json, remote_base


def jobs(run,remote):
    run=Path(run).resolve();m=read_manifest(run)
    if not re.fullmatch(re.escape(remote_base())+r"/[A-Za-z0-9_-]+",remote):
        raise ValueError("Remote destination is outside the intended personal project storage")
    relative=run.relative_to(ROOT).as_posix();folder=run/"hpg";folder.mkdir()
    head=f"""#!/bin/bash
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8gb
#SBATCH --time=02:00:00
#SBATCH --chdir={remote}
"""
    env=f"""set -euo pipefail
umask 077
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
unset PYTHONHOME PYTHONPATH
cd '{remote}'
"""
    setup=head+f"#SBATCH --job-name=connections-setup\n#SBATCH --output={remote}/hpg-setup-%j.out\n"+env+"""module load python/3.12
unset PYTHONHOME PYTHONPATH
uv sync --frozen --python 3.11
.venv/bin/python -m unittest discover -s tests -v
"""
    studies=" ".join(m["studies"])
    core=head+f"#SBATCH --job-name=connections-core\n#SBATCH --array=0-{len(m['studies'])-1}%4\n#SBATCH --output={remote}/hpg-core-%A-%a.out\n"+env+f"STUDIES=({studies})\n.venv/bin/python -m discovery.connections task --run '{relative}' --study \"${{STUDIES[$SLURM_ARRAY_TASK_ID]}}\"\n"
    report=head+f"#SBATCH --job-name=connections-report\n#SBATCH --output={remote}/hpg-report-%j.out\n"+env+f".venv/bin/python -m discovery.connections aggregate --run '{relative}'\n.venv/bin/python -m discovery.connection_jobs export --run '{relative}' --output returned-results.zip\n"
    submit=f"""#!/bin/bash
set -euo pipefail
cd '{remote}'
SETUP=$(sbatch --parsable '{relative}/hpg/setup.sbatch'); SETUP=${{SETUP%%;*}}
CORE=$(sbatch --parsable --dependency=afterok:$SETUP '{relative}/hpg/core.sbatch'); CORE=${{CORE%%;*}}
REPORT=$(sbatch --parsable --dependency=afterany:$CORE '{relative}/hpg/report.sbatch'); REPORT=${{REPORT%%;*}}
printf 'setup=%s core=%s report=%s\\n' "$SETUP" "$CORE" "$REPORT" | tee submission-ids.txt
"""
    for name,body in [("setup.sbatch",setup),("core.sbatch",core),("report.sbatch",report),("submit.sh",submit)]:
        (folder/name).write_text(body,encoding="utf-8",newline="\n")
    write_json(folder/"job-config.json",{"remote_root":remote,"manifest_id":m["manifest_id"],"studies":m["studies"],
                                        "concurrency":4,"cpus_per_task":1,"memory_gb":8,"hours":2})
    return {"remote":remote,"studies":m["studies"]}


def bundle(run,output):
    run=Path(run).resolve();m=read_manifest(run);output=Path(output)
    if output.exists():raise ValueError("Existing bundle cannot be overwritten")
    names=set(m["code_files"])|set(m["input_files"])
    names|={p.relative_to(ROOT).as_posix() for p in (ROOT/"webull_bt").rglob("*.py")}
    names|={"docs/README.md","docs/discovery/options-buffered-plan.md","config/discovery-pilot.json"}
    names|={p.relative_to(ROOT).as_posix() for p in (run/"hpg").glob("*")}
    names.add((run/"manifest.json").relative_to(ROOT).as_posix())
    # Earlier discovery modules are imported by correctness fixtures; their folder code is needed too.
    names|={p.relative_to(ROOT).as_posix() for p in (ROOT/"Hypotheses").glob("H*/analysis.py")}
    hashes={n:digest(ROOT/n) for n in sorted(names)}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(output,"w:gz") as archive:
        for name in hashes:
            if Path(name).name==".env" or not safe_child(ROOT,name).is_file():raise ValueError("Invalid bundle member")
            archive.add(ROOT/name,arcname=name,recursive=False)
    write_json(output.with_suffix(".receipt.json"),{"manifest_id":m["manifest_id"],"sha256":digest(output),"files":hashes})
    return {"sha256":digest(output),"files":len(hashes),"bytes":output.stat().st_size}


def export(run,output):
    run=Path(run);m=read_manifest(run)
    files=[p for p in run.rglob("*") if p.is_file() and p.suffix in {".csv",".json",".md"} and "hpg" not in p.relative_to(run).parts]
    hashes={p.relative_to(run).as_posix():digest(p) for p in files}
    with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as archive:
        for p in files:archive.write(p,p.relative_to(run).as_posix())
        archive.writestr("RETURN-RECEIPT.json",json.dumps({"manifest_id":m["manifest_id"],"files":hashes},indent=2))
    return {"sha256":digest(output),"files":len(hashes)}


def import_results(archive_path,run):
    run=Path(run);m=read_manifest(run);entries=[]
    with zipfile.ZipFile(archive_path) as archive:
        if len(archive.namelist())!=len(set(archive.namelist())):raise ValueError("Duplicate members")
        r=json.loads(archive.read("RETURN-RECEIPT.json"))
        if r["manifest_id"]!=m["manifest_id"]:raise ValueError("Return belongs to another frozen run")
        if set(archive.namelist())!=set(r["files"])|{"RETURN-RECEIPT.json"}:raise ValueError("Unexpected archive entries")
        for name,expected in r["files"].items():
            p=safe_child(run,name);raw=archive.read(name)
            if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError("Returned file hash differs")
            if p.exists() and digest(p)!=expected:raise ValueError("Existing local output differs")
            entries.append((p,raw))
    for p,raw in entries:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    return {"files_verified":len(entries),"archive_sha256":digest(archive_path)}


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest="command",required=True)
    for command in ["jobs","bundle","export","import"]:
        q=s.add_parser(command);q.add_argument("--run",type=Path,required=True)
        if command=="jobs":q.add_argument("--remote",required=True)
        elif command=="import":q.add_argument("--archive",type=Path,required=True)
        else:q.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.command=="jobs":r=jobs(a.run,a.remote)
    elif a.command=="bundle":r=bundle(a.run,a.output)
    elif a.command=="export":r=export(a.run,a.output)
    else:r=import_results(a.archive,a.run)
    print(json.dumps(r))


if __name__=="__main__":main()
