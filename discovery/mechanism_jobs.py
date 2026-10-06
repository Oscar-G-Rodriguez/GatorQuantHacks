"""Private allowlisted transfer, Slurm jobs, returned hashes and final freeze."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import tarfile
import tomllib
import zipfile

from .io import ROOT,digest,identity,now,read_json,safe_child,write_json,remote_base
from .mechanism_data import FOLDERS
from .mechanism_run import verify,create_manifest


def jobs(run,remote):
    run=Path(run).resolve();m=verify(run)
    if not re.fullmatch(re.escape(remote_base())+r"/mechanisms-round1-[A-Za-z0-9_-]+",remote):
        raise ValueError("Destination must be a fresh personal mechanisms directory")
    relative=run.relative_to(ROOT).as_posix();folder=run/"hpg";folder.mkdir(exist_ok=False)
    header=f"""#!/bin/bash
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
    setup=header+f"#SBATCH --job-name=mechanisms-setup\n#SBATCH --output={remote}/hpg-setup-%j.out\n"+env+"""module load python/3.12
unset PYTHONHOME PYTHONPATH
uv sync --frozen --python 3.11
.venv/bin/python -m unittest discover -s tests -p 'test_mechanism*.py' -v
"""
    paths="\n".join(f"  '{(ROOT/'Hypotheses'/folder/'backtest.py').relative_to(ROOT).as_posix()}'" for folder in FOLDERS.values())
    core=header+f"#SBATCH --job-name=mechanisms-core\n#SBATCH --array=0-2%3\n#SBATCH --output={remote}/hpg-core-%A-%a.out\n"+env+f"RUNNERS=(\n{paths}\n)\n.venv/bin/python \"${{RUNNERS[$SLURM_ARRAY_TASK_ID]}}\" --run '{relative}'\n"
    report=header+f"#SBATCH --job-name=mechanisms-report\n#SBATCH --output={remote}/hpg-report-%j.out\n"+env+f".venv/bin/python -m discovery.mechanism_run aggregate --run '{relative}'\n"
    returned=header+f"#SBATCH --job-name=mechanisms-return\n#SBATCH --output={remote}/hpg-return-%j.out\n"+env+f"""
IDS=$(sed -E 's/[a-z]+=//g;s/ /,/g' submission-ids.txt)
sacct -j "$IDS" --parsable2 --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS > scheduler-accounting.txt
.venv/bin/python -m discovery.mechanism_jobs export --run '{relative}' --output returned-results.zip
sha256sum returned-results.zip > returned-results.sha256
"""
    submit=f"""#!/bin/bash
set -euo pipefail
cd '{remote}'
SETUP=$(sbatch --parsable '{relative}/hpg/setup.sbatch'); SETUP=${{SETUP%%;*}}
CORE=$(sbatch --parsable --dependency=afterok:$SETUP '{relative}/hpg/core.sbatch'); CORE=${{CORE%%;*}}
REPORT=$(sbatch --parsable --dependency=afterany:$CORE '{relative}/hpg/report.sbatch'); REPORT=${{REPORT%%;*}}
RETURN=$(sbatch --parsable --dependency=afterany:$REPORT '{relative}/hpg/return.sbatch'); RETURN=${{RETURN%%;*}}
printf 'setup=%s core=%s report=%s return=%s\\n' "$SETUP" "$CORE" "$REPORT" "$RETURN" | tee submission-ids.txt
"""
    for name,body in [("setup.sbatch",setup),("core.sbatch",core),("report.sbatch",report),("return.sbatch",returned),("submit.sh",submit)]:
        (folder/name).write_text(body,encoding="utf-8",newline="\n")
    write_json(folder/"job-config.json",{"remote_root":remote,"manifest_id":m["manifest_id"],"concurrency":3,"cpus":1,"memory_gb":8,"hours":2})
    return {"remote":remote,"manifest_id":m["manifest_id"]}


def bundle(run,output):
    run=Path(run).resolve();m=verify(run);output=Path(output)
    if output.exists():raise ValueError("Do not overwrite earlier bundles")
    names=set(m["code_files"])|set(m["input_files"])
    names|={p.relative_to(ROOT).as_posix() for p in (run/"hpg").glob("*")}
    names.add((run/"manifest.json").relative_to(ROOT).as_posix())
    names|={"docs/massive/mechanism-round1-plan.md"}
    build_spec=tomllib.loads((ROOT/"pyproject.toml").read_text())
    requirements=[build_spec["project"]["readme"]]
    requirements += [name+"/__init__.py" for name in build_spec["tool"]["setuptools"]["packages"]]
    if not set(requirements)<=names:
        raise ValueError("Declared build inputs missing from transfer: "+str(sorted(set(requirements)-names)))
    hashes={name:digest(safe_child(ROOT,name)) for name in sorted(names)}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(output,"w:gz") as archive:
        for name in hashes:
            if ".env" in Path(name).parts or ".git" in Path(name).parts:raise ValueError("Secret/Git path denied")
            archive.add(ROOT/name,arcname=name,recursive=False)
        raw=json.dumps({"manifest_id":m["manifest_id"],"files":hashes}).encode()
        import io
        member=tarfile.TarInfo("BUNDLE-FILES.json");member.size=len(raw);member.mode=0o600
        archive.addfile(member,io.BytesIO(raw))
    write_json(output.with_suffix(".receipt.json"),{"manifest_id":m["manifest_id"],"sha256":digest(output),"bytes":output.stat().st_size,"files":hashes})
    return {"sha256":digest(output),"bytes":output.stat().st_size,"files":len(hashes)}


def export(run,output):
    run=Path(run);m=verify(run);output=Path(output)
    if output.exists():raise ValueError("Return archive exists; preserve attempt")
    files={p.relative_to(run).as_posix():p for p in run.rglob("*") if p.is_file() and "hpg" not in p.relative_to(run).parts}
    for p in list(ROOT.glob("hpg-*.out"))+[ROOT/"scheduler-accounting.txt",ROOT/"submission-ids.txt"]:
        if p.exists():files["scheduler/"+p.name]=p
    hashes={n:digest(p) for n,p in files.items()}
    with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as archive:
        for name,p in files.items():archive.write(p,name)
        archive.writestr("RETURN-RECEIPT.json",json.dumps({"manifest_id":m["manifest_id"],"files":hashes},indent=2))
    return {"sha256":digest(output),"files":len(hashes)}


def import_results(archive_path,run,expected_sha):
    run=Path(run);m=verify(run)
    if digest(archive_path)!=expected_sha:raise ValueError("Whole return archive SHA differs from remote evidence")
    entries=[]
    with zipfile.ZipFile(archive_path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)):raise ValueError("Duplicate ZIP members")
        receipt=json.loads(archive.read("RETURN-RECEIPT.json"))
        if receipt["manifest_id"]!=m["manifest_id"]:raise ValueError("Return is another run")
        if set(names)!=set(receipt["files"])|{"RETURN-RECEIPT.json"}:raise ValueError("Unexpected member")
        for name,expected in receipt["files"].items():
            p=safe_child(run,name);raw=archive.read(name)
            if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError("Member SHA differs")
            if p.exists() and digest(p)!=expected:raise ValueError("Existing local evidence differs")
            entries.append((p,raw))
    for p,raw in entries:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    write_json(run/"return-verification.json",{"at":now(),"archive_sha256":expected_sha,"files_verified":len(entries),"manifest_id":m["manifest_id"]})
    return {"files_verified":len(entries),"sha256":expected_sha}


def freeze(run,output):
    run=Path(run);m=verify(run);output=Path(output)
    if m["phase"]!="development":raise ValueError("Freeze must follow development")
    if output.exists():raise ValueError("Do not replace a scientific freeze")
    result=read_json(run/"aggregate.json")
    if not result["all_tasks_complete"] or not (run/"return-verification.json").exists():
        raise ValueError("Completed verified development return required")
    accounting=(run/"scheduler"/"scheduler-accounting.txt").read_text()
    # Setup, all three array elements and report must actually be terminal.
    ids=(run/"scheduler"/"submission-ids.txt").read_text().strip()
    values=dict(re.findall(r"(setup|core|report)=(\d+)",ids))
    required=[values.get("setup"),values.get("report")]+[values.get("core","")+"_"+str(i) for i in range(3)]
    for jid in required:
        matches=[line.split("|") for line in accounting.splitlines() if line.split("|")[0]==jid]
        if len(matches)!=1 or matches[0][2]!="COMPLETED" or matches[0][3]!="0:0":raise ValueError("Scheduler completion proof absent: "+str(jid))
    write_json(output,{"schema":1,"frozen_at":now(),"registration_commit":m["registration_commit"],"code_files":m["code_files"],
                       "config_sha256":m["config_sha256"],"development_manifest_id":m["manifest_id"],
                       "development_findings_sha256":digest(run/"aggregate.json"),"return_sha256":read_json(run/"return-verification.json")["archive_sha256"],
                       "prediction_files":{study:{"path":(run/"tasks"/study/"prediction-model.json").resolve().relative_to(ROOT).as_posix(),
                                                   "sha256":digest(run/"tasks"/study/"prediction-model.json")} for study in FOLDERS},
                       "final_family":["H18","H19","H20"],"selection":"all three fixed; no winner selected from OOS"})
    return {"freeze_sha256":digest(output)}


def record(run):
    """Append immutable returned trial identities once; no recalculation on PC."""
    run=Path(run);m=verify(run)
    if not (run/"return-verification.json").exists():raise ValueError("Verify the actual returned archive first")
    path=ROOT/"Hypotheses/EXPERIMENTS.csv"
    with path.open(newline="",encoding="utf-8") as h:
        reader=csv.DictReader(h);fields=reader.fieldnames;existing={r["experiment_id"] for r in reader}
    rows=[]
    for study in FOLDERS:
        p=run/"tasks"/study/"trial-cells.csv"
        if not p.exists():
            failure=run/"tasks"/study/"failure.json"
            if not failure.exists():continue
            cells=[{"kind":"operational_failed_task","status":"failed","reason":"See preserved failure.json"}]
        else:
            with p.open(newline="",encoding="utf-8") as h:cells=list(csv.DictReader(h))
        for i,cell in enumerate(cells):
            eid="mechanism-"+identity({"manifest":m["manifest_id"],"study":study,"index":i,"cell":cell})[:24]
            if eid in existing:continue
            rows.append(dict(experiment_id=eid,registered_at=m["created_at"],hypothesis_id=study,registration_commit=m["registration_commit"],
                             code_commit=m["code_commit"],sample_or_fold=m["phase"],parameters=json.dumps(cell,sort_keys=True),
                             signal_and_fill_timing="Conditional filing+1 calendar-day close; next open+2min; exits close-5min; backward <=60sec quotes",
                             cost_model="All legs: bid/ask + $0.65/contract/side +1 premium bp; doubled variants; strike cash at4%",
                             data_identity=m["manifest_id"],outcome=cell.get("status","inconclusive"),
                             evidence_path=(run/"tasks"/study).resolve().relative_to(ROOT).as_posix(),
                             notes="Registered after earlier discovery; static universe; timing/assignment/broad exposure gaps prevent executable support"))
            existing.add(eid)
    with path.open("a",newline="",encoding="utf-8") as h:
        writer=csv.DictWriter(h,fieldnames=fields);writer.writerows(rows)
    return {"new_trial_cells":len(rows)}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    for command in ["jobs","bundle","export","import","freeze","record"]:
        q=sub.add_parser(command);q.add_argument("--run",type=Path,required=True)
        if command=="jobs":q.add_argument("--remote",required=True)
        elif command=="import":q.add_argument("--archive",type=Path,required=True);q.add_argument("--expected-sha",required=True)
        elif command!="record":q.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=jobs(a.run,a.remote) if a.command=="jobs" else import_results(a.archive,a.run,a.expected_sha) if a.command=="import" else record(a.run) if a.command=="record" else freeze(a.run,a.output) if a.command=="freeze" else bundle(a.run,a.output) if a.command=="bundle" else export(a.run,a.output)
    print(json.dumps(r))


if __name__=="__main__":main()
