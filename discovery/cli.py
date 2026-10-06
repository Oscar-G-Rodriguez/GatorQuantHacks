"""Local downloads, parallel offline studies and portable job preparation."""
from __future__ import annotations

import argparse
from pathlib import Path

from .io import ROOT, STUDIES


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ["download", "demo"]:
        q = sub.add_parser(name)
        q.add_argument("--config", type=Path, default=ROOT / "config/discovery-pilot.json")
        q.add_argument("--snapshot", type=Path, required=True)
        if name == "download":
            q.add_argument("--max-requests", type=int, default=20)
    q = sub.add_parser("plan")
    q.add_argument("--snapshot", type=Path, required=True)
    q.add_argument("--run", type=Path, required=True)
    for name in ["run", "task", "study", "aggregate", "record", "jobs", "bundle", "export", "import"]:
        q = sub.add_parser(name)
        q.add_argument("--run", type=Path, required=True)
        if name == "run":
            q.add_argument("--workers", type=int, default=2)
        elif name == "task":
            q.add_argument("--task-id", type=int, required=True)
        elif name == "study":
            q.add_argument("--id", choices=STUDIES, required=True)
        elif name in ["bundle", "export"]:
            q.add_argument("--output", type=Path, required=True)
        elif name == "import":
            q.add_argument("--archive", type=Path, required=True)
        elif name == "jobs":
            q.add_argument("--remote-root", required=True)
            q.add_argument("--account", default="ai-workshop")
            q.add_argument("--qos", default="ai-workshop")
            q.add_argument("--concurrency", type=int, default=4)
            q.add_argument("--memory-gb", type=int, default=4)
            q.add_argument("--hours", type=int, default=2)
    args = p.parse_args(argv)
    if args.command in ["demo", "download"]:
        from .download import download, synthetic
        result = synthetic(args.config, args.snapshot) if args.command == "demo" else download(args.config, args.snapshot, args.max_requests)
        print({"snapshot": str(args.snapshot), "snapshot_id": result.get("snapshot_id")}, flush=True)
        return 0
    from .runner import aggregate, plan, read_manifest, record_ledger, run_local, run_task
    from .jobs import bundle, export_results, import_results, write_jobs
    if args.command == "plan":
        result = plan(args.snapshot, args.run)
        print({"run": str(args.run), "tasks": len(result["tasks"]), "manifest_id": result["manifest_id"]}, flush=True)
    elif args.command == "run":
        run_local(args.run, args.workers)
        result = aggregate(args.run)
        print({"report": str(args.run / "REPORT.md"), "complete": result["complete"]}, flush=True)
        return 0 if result["complete"] else 1
    elif args.command == "task":
        result = run_task(args.run, args.task_id)
        print(result, flush=True)
        return 0 if result["status"] != "failed" else 1
    elif args.command == "study":
        for task in read_manifest(args.run)["tasks"]:
            if task["study"] == args.id:
                result = run_task(args.run, task["id"])
                print(result, flush=True)
                if result["status"] == "failed":
                    return 1
    elif args.command == "aggregate":
        result = aggregate(args.run)
        print({"complete": result["complete"], "failures": result["failures"]}, flush=True)
        # Exit normally so a failed task still yields a return archive in Slurm.
    elif args.command == "record":
        print({"ledger_rows_added": record_ledger(args.run)}, flush=True)
    elif args.command == "jobs":
        print(write_jobs(args.run, args.remote_root, args.account, args.qos, args.concurrency, args.memory_gb, args.hours), flush=True)
    elif args.command == "bundle":
        print(bundle(args.run, args.output), flush=True)
    elif args.command == "export":
        print(export_results(args.run, args.output), flush=True)
    elif args.command == "import":
        print({"verified_files": import_results(args.archive, args.run)}, flush=True)
    return 0
