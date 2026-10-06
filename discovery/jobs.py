"""Build a reviewed local transfer bundle and staged Slurm scripts.

No SSH, remote write or job submission happens here. The scripts become usable
only after the local snapshot and implementation have been completed/verified.
"""
from __future__ import annotations

import re
import tarfile
from pathlib import Path

from .io import ROOT, STUDIES, digest, read_json, safe_child, write_json
from .runner import read_manifest


def write_jobs(run_path, remote_root, account, qos, concurrency=4, memory_gb=4, hours=2):
    run_path = Path(run_path).resolve()
    m = read_manifest(run_path)
    if not re.fullmatch(r"/blue/[A-Za-z0-9_./-]+", remote_root) or ".." in remote_root.split("/"):
        raise ValueError("Remote workspace must be a safe absolute Blue path")
    if not all(re.fullmatch(r"[A-Za-z0-9_-]+", value) for value in [account, qos]):
        raise ValueError("Invalid account/QOS")
    if not 1 <= concurrency <= 64 or not 1 <= memory_gb <= 128 or not 1 <= hours <= 24:
        raise ValueError("Resource request outside bounded builder limits")
    folder = run_path / "hpg"
    folder.mkdir(exist_ok=True)
    relative_run = run_path.relative_to(ROOT).as_posix()
    common = f'''#!/bin/bash
#SBATCH --account={account}
#SBATCH --qos={qos}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem={memory_gb}gb
#SBATCH --time={hours:02d}:00:00
#SBATCH --chdir={remote_root}
'''
    env = f'''set -euo pipefail
umask 077
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
cd '{remote_root}'
# Inherited module paths must not redirect the project's locked interpreter.
unset PYTHONHOME PYTHONPATH
'''
    setup = common + "#SBATCH --job-name=discovery-setup\n" + f"#SBATCH --output={remote_root}/hpg-setup-%j.out\n" + env + '''module load python/3.12
# The maintained module supplies uv; the project itself remains Python 3.11.
# The module sets PYTHONHOME for 3.12; uv/builds use the locked 3.11 runtime.
unset PYTHONHOME PYTHONPATH
uv sync --frozen --python 3.11
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -c "from discovery.methods import handler; from discovery.io import STUDIES; [handler(s) for s in STUDIES]; print('All nine study modules loaded')"
'''
    core = common + f"#SBATCH --job-name=discovery-core\n#SBATCH --array=0-7%{min(concurrency, 8)}\n#SBATCH --output={remote_root}/hpg-core-%A-%a.out\n" + env + f".venv/bin/python -m discovery task --run '{relative_run}' --task-id \"$SLURM_ARRAY_TASK_ID\"\n"
    # Arrays index batches, not each resample; this avoids thousands of tiny jobs.
    batches = sum(t["stage"] == "uncertainty" for t in m["tasks"])
    if batches > 3000:
        raise ValueError("Too many scheduler batches; increase resample_batch")
    uncertainty = common + f"#SBATCH --job-name=discovery-uncertainty\n#SBATCH --array=0-{batches - 1}%{min(concurrency, batches)}\n#SBATCH --output={remote_root}/hpg-uncertainty-%A-%a.out\n" + env + f".venv/bin/python -m discovery task --run '{relative_run}' --task-id \"$((SLURM_ARRAY_TASK_ID + 8))\"\n"
    reduce = common + f"#SBATCH --job-name=discovery-report\n#SBATCH --output={remote_root}/hpg-report-%j.out\n" + env + f".venv/bin/python -m discovery aggregate --run '{relative_run}'\n.venv/bin/python -m discovery export --run '{relative_run}' --output 'returned-results.zip'\n"
    # Reducer runs after ANY uncertainty outcome, so failures have a downloadable
    # report. setup must succeed; uncertainty waits until all core attempts end.
    submit = f'''#!/bin/bash
set -euo pipefail
cd '{remote_root}'
SETUP=$(sbatch --parsable '{relative_run}/hpg/setup.sbatch')
SETUP=${{SETUP%%;*}}
CORE=$(sbatch --parsable --dependency=afterok:$SETUP '{relative_run}/hpg/core.sbatch')
CORE=${{CORE%%;*}}
UNCERTAINTY=$(sbatch --parsable --dependency=afterany:$CORE '{relative_run}/hpg/uncertainty.sbatch')
UNCERTAINTY=${{UNCERTAINTY%%;*}}
REPORT=$(sbatch --parsable --dependency=afterany:$UNCERTAINTY '{relative_run}/hpg/report.sbatch')
REPORT=${{REPORT%%;*}}
printf 'setup=%s core=%s uncertainty=%s report=%s\\n' "$SETUP" "$CORE" "$UNCERTAINTY" "$REPORT" | tee submission-ids.txt
'''
    for name, body in [("setup.sbatch", setup), ("core.sbatch", core), ("uncertainty.sbatch", uncertainty), ("report.sbatch", reduce), ("submit.sh", submit)]:
        (folder / name).write_text(body, encoding="utf-8", newline="\n")
    config = {"remote_root": remote_root, "account": account, "qos": qos, "parallel_task_cap": concurrency, "cpus_per_task": 1, "memory_gb_per_task": memory_gb, "hours_per_task": hours, "manifest_id": m["manifest_id"]}
    write_json(folder / "job-config.json", config)
    return folder


def bundle(run_path, output):
    """Explicit allowlist; never transfer .env, Git metadata or a PC environment."""
    run_path = Path(run_path).resolve()
    m = read_manifest(run_path)
    snapshot_path = (run_path / m["snapshot"]).resolve()
    if not snapshot_path.is_relative_to(ROOT) or not run_path.is_relative_to(ROOT):
        raise ValueError("Keep snapshot/run inside the project for portable bundles")
    files = [ROOT / p for p in m["code_files"]]
    files += list((ROOT / "webull_bt").rglob("*.py"))
    files += list((ROOT / "tests").glob("*.py"))
    files += [ROOT / ".python-version", ROOT / "docs/README.md", ROOT / "docs/discovery/README.md", ROOT / "config/discovery-pilot.json", run_path / "manifest.json"]
    files += list((run_path / "hpg").glob("*"))
    files += [snapshot_path / f for f in ["panel.csv", "snapshot.json", "config.json"]]
    if not (run_path / "hpg/submit.sh").exists():
        raise ValueError("Generate jobs before bundling")
    files = sorted(set(p.resolve() for p in files))
    hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in files}
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Refusing to overwrite an existing transfer bundle")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        for p in files:
            archive.add(p, arcname=p.relative_to(ROOT).as_posix(), recursive=False)
    write_json(output.with_suffix(output.suffix + ".receipt.json"), {"archive_sha256": digest(output), "files": hashes, "manifest_id": m["manifest_id"], "scope": "Local code + normalized historical panel only; no keys, raw API responses, Git history, PC environment, or precomputed study results"})
    return {"bundle": str(output), "sha256": digest(output), "files": len(files)}


def export_results(run_path, output):
    import zipfile
    run_path = Path(run_path).resolve()
    m = read_manifest(run_path)
    files = [p for p in run_path.rglob("*") if p.is_file() and p.suffix in {".json", ".csv", ".md"} and "hpg" not in p.relative_to(run_path).parts]
    hashes = {p.relative_to(run_path).as_posix(): digest(p) for p in files}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"manifest_id": m["manifest_id"], "run_id": m["run_id"], "files": hashes}
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for p in files:
            archive.write(p, p.relative_to(run_path).as_posix())
        archive.writestr("RETURN-RECEIPT.json", __import__("json").dumps(receipt, indent=2))
    return {"archive": str(output), "sha256": digest(output)}


def import_results(archive_path, run_path):
    """Validate paths and bytes before any write; never merge differing attempts."""
    import json
    import zipfile
    run_path = Path(run_path).resolve()
    m = read_manifest(run_path)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive members")
        receipt = json.loads(archive.read("RETURN-RECEIPT.json"))
        if receipt["manifest_id"] != m["manifest_id"]:
            raise ValueError("Returned results belong to another run")
        if set(names) != set(receipt["files"]) | {"RETURN-RECEIPT.json"}:
            raise ValueError("Unexpected return archive entries")
        entries = []
        import hashlib
        for name, expected in receipt["files"].items():
            p = safe_child(run_path, name)
            raw = archive.read(name)
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError("Returned bytes do not match receipt")
            if p.exists() and digest(p) != expected:
                raise ValueError("Existing local attempt differs; import to its own copied-plan directory")
            entries.append((p, raw))
        for p, raw in entries:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
    return len(entries)
