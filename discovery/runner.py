"""Frozen task graph shared by Windows multiprocessing and Slurm arrays."""
from __future__ import annotations

import csv
import importlib.metadata
import os
import platform
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .data import load_snapshot
from .io import ROOT, STUDIES, code_identity, digest, identity, now, read_json, safe_child, write_json
from .methods import handler


def task_key(row):
    return tuple((k, str(row.get(k, ""))) for k in ["feature", "other_feature", "target", "lag", "horizon", "model", "fold", "regime", "statistic"])


def plan(snapshot_path, run_path):
    snapshot_path, run_path = Path(snapshot_path).resolve(), Path(run_path).resolve()
    _, meta, c = load_snapshot(snapshot_path)
    run_path.mkdir(parents=True, exist_ok=False)
    tasks = [{"id": i, "study": study, "stage": "core", "seed": c["seed"] + i, "draws": 0} for i, study in enumerate(list(STUDIES)[:-1])]
    for j, start in enumerate(range(0, c["resamples"], c["resample_batch"])):
        tasks.append({"id": len(tasks), "study": "H11", "stage": "uncertainty", "seed": c["seed"] + 100000 + j, "draws": min(c["resample_batch"], c["resamples"] - start), "batch": j})
    manifest = {"schema": 1, "created_at": now(), "run_id": run_path.name, "snapshot": os.path.relpath(snapshot_path, run_path).replace("\\", "/"), "snapshot_id": meta["snapshot_id"], "code_files": code_identity(), "tasks": tasks, "scope": "Exploratory development statistics; no trades, P&L, backtest or final OOS", "synthetic": meta["provenance"].get("synthetic", False), "config": c}
    manifest["manifest_id"] = identity(manifest)
    write_json(run_path / "manifest.json", manifest)
    return manifest


def read_manifest(run_path, check_code=True):
    run_path = Path(run_path).resolve()
    m = read_json(run_path / "manifest.json")
    if identity({k: v for k, v in m.items() if k != "manifest_id"}) != m["manifest_id"]:
        raise ValueError("Run manifest changed")
    if check_code and code_identity() != m["code_files"]:
        raise ValueError("Implementation/runtime lock changed; create a new plan rather than mix results")
    return m


def result_path(run_path, task):
    return Path(run_path) / "studies" / task["study"] / f"task-{task['id']:05d}.json"


def valid_receipt(path, m, task):
    if not Path(path).exists():
        return False
    r = read_json(path)
    if r.get("manifest_id") != m["manifest_id"] or r.get("task") != task:
        raise ValueError("Result belongs to a different task/manifest")
    if identity({k: v for k, v in r.items() if k != "result_id"}) != r.get("result_id"):
        raise ValueError("Result content hash mismatch")
    if r.get("status") not in {"complete", "failed"} or (r.get("status") == "complete" and not isinstance(r.get("rows"), list)):
        raise ValueError("Invalid task receipt schema")
    return r["status"] == "complete"


def run_task(run_path, task_id):
    """Top-level, spawn-safe worker. Offline: it never imports a credential client."""
    run_path = Path(run_path).resolve()
    m = read_manifest(run_path)
    if not 0 <= task_id < len(m["tasks"]):
        raise ValueError("Task index outside manifest")
    task = m["tasks"][task_id]
    path = result_path(run_path, task)
    if valid_receipt(path, m, task):
        return {"task_id": task_id, "status": "cached"}
    if path.exists():
        previous = read_json(path)
        # Preserve the failed attempt's original bytes before a retry receipt.
        write_json(path.with_name(f"attempt-{task_id:05d}-{previous['result_id'][:12]}.json"), previous)
    receipt = {"manifest_id": m["manifest_id"], "task": task, "started_at": now(), "status": "failed", "runtime": {"python": platform.python_version(), "platform": platform.platform(), "packages": {n: importlib.metadata.version(n) for n in ["numpy", "pandas", "scipy", "scikit-learn"]}}}
    try:
        panel, meta, c = load_snapshot(run_path / m["snapshot"])
        if meta["snapshot_id"] != m["snapshot_id"]:
            raise ValueError("Snapshot differs from run manifest")
        method_task = task.copy()
        if task["stage"] == "uncertainty":
            # Complete/failed core receipts must exist before this stage starts.
            for core in m["tasks"][:8]:
                if not result_path(run_path, core).exists():
                    raise ValueError("Uncertainty stage started before core stage finished")
            pred_task = m["tasks"][5]
            if valid_receipt(result_path(run_path, pred_task), m, pred_task):
                method_task["paired_losses"] = read_json(result_path(run_path, pred_task))["extra"].get("paired_losses", [])
        with threadpool_limits(limits=1):
            rows, extra = handler(task["study"])(panel, meta, c, method_task)
        receipt.update(status="complete", rows=rows, extra=extra)
    except Exception as error:
        # Statistics run offline, so an exception contains no API key/response.
        receipt.update(error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
    receipt["finished_at"] = now()
    receipt["result_id"] = identity(receipt)
    write_json(path, receipt)
    return {"task_id": task_id, "status": receipt["status"], "error": receipt.get("error")}


def run_local(run_path, workers):
    m = read_manifest(run_path)
    if not 1 <= workers <= (os.cpu_count() or 1):
        raise ValueError("Workers must be between 1 and the detected CPU count")
    summaries = []
    for stage in ["core", "uncertainty"]:
        tasks = [t for t in m["tasks"] if t["stage"] == stage]
        if workers == 1:
            for t in tasks:
                result = run_task(run_path, t["id"])
                print(result, flush=True)
                summaries.append(result)
        else:
            with ProcessPoolExecutor(max_workers=min(workers, len(tasks))) as pool:
                work = [pool.submit(run_task, str(run_path), t["id"]) for t in tasks]
                for future in as_completed(work):
                    result = future.result()
                    print(result, flush=True)
                    summaries.append(result)
    return summaries


def aggregate(run_path):
    """Reducer refuses to call missing/corrupt/failed tasks a completed study."""
    run_path = Path(run_path).resolve()
    m = read_manifest(run_path)
    failures, raw, extras = [], {s: [] for s in STUDIES}, {}
    for t in m["tasks"]:
        path = result_path(run_path, t)
        try:
            if not valid_receipt(path, m, t):
                failures.append({"task": t["id"], "study": t["study"], "reason": read_json(path).get("error") if path.exists() else "Missing result"})
                continue
            receipt = read_json(path)
            raw[t["study"]].extend(receipt["rows"])
            extras[t["study"]] = receipt.get("extra", {})
        except (ValueError, OSError) as error:
            failures.append({"task": t["id"], "study": t["study"], "reason": str(error)})
    combined = {}
    for r in raw["H11"]:
        key = task_key(r)
        if key not in combined:
            combined[key] = {**r, "bootstrap_values": []}
        combined[key]["bootstrap_values"].extend(r.get("bootstrap_values", []))
    family_size = len(combined)  # Includes unsupported scheduled comparisons.
    for r in combined.values():
        values = r.pop("bootstrap_values")
        r["valid_draws"] = len(values)
        if len(values) >= 40:
            r.update(pointwise_ci_low=float(np.quantile(values, .025)), pointwise_ci_high=float(np.quantile(values, .975)))
            # Require >=20 samples in each extreme tail before printing a
            # multiplicity-adjusted percentile interval. Pilot often cannot.
            alpha = .05 / max(1, family_size)
            if len(values) * alpha / 2 >= 20:
                r.update(bonferroni_ci_low=float(np.quantile(values, alpha / 2)), bonferroni_ci_high=float(np.quantile(values, 1 - alpha / 2)))
            else:
                r["search_adjusted_interval"] = "Unavailable: resampling budget has inadequate tail resolution"
        r["correlation_and_paired_loss_family_size"] = family_size
        r["inference_limits"] = "Approximate bootstrap intervals assume sufficiently stationary blocks, condition on observed issuers and do not correct arbitrary adaptive model/feature selection; no null p-values or independent confirmation"
    raw["H11"] = list(combined.values())
    summary = []
    for study, rows in raw.items():
        out = run_path / "studies" / study
        out.mkdir(parents=True, exist_ok=True)
        if rows:
            pd.DataFrame(rows).to_csv(out / "measurements.csv", index=False)
        counts = {"measured": sum(r["status"] == "measured" for r in rows), "inconclusive": sum(r["status"] == "inconclusive" for r in rows)}
        summary.append({"study": study, "name": STUDIES[study], "status": "failed" if any(f["study"] == study for f in failures) else "complete", "comparisons": len(rows), **counts, "evidence": f"studies/{study}/measurements.csv" if rows else ""})
    pd.DataFrame(summary).to_csv(run_path / "summary.csv", index=False)
    # Preserve every core trial and every combined uncertainty comparison.
    trials = [{"study": s, **r} for s, rows in raw.items() for r in rows]
    pd.DataFrame(trials).to_csv(run_path / "trials.csv", index=False)
    report = {"run_id": m["run_id"], "manifest_id": m["manifest_id"], "scope": m["scope"], "synthetic": m["synthetic"], "complete": not failures, "failures": failures, "total_comparisons": len(trials), "summary": summary, "generated_at": now(), "limits": ["Positive discovery measurements are candidates, not validated signals or profitable strategies", "All attempted variants are retained, including sparse/failed comparisons", "Most README proposals have richer methods still to implement; see implementation coverage in docs/discovery/README.md", "Pointwise intervals do not correct selection; pilot resamples generally cannot resolve search-adjusted tails"]}
    write_json(run_path / "report.json", report)
    lines = ["# Statistical discovery results", "", f"Run `{m['run_id']}`. {'SYNTHETIC ENGINEERING CHECK' if m['synthetic'] else 'REAL-DATA DEVELOPMENT DISCOVERY'}. Status: {'complete' if not failures else 'incomplete'}. No backtest or final holdout.", "", "| Study | Completed measurements | Inconclusive comparisons | Task status |", "| --- | ---: | ---: | --- |"]
    lines.extend(f"| {r['name']} | {r['measured']} | {r['inconclusive']} | {r['status']} |" for r in summary)
    lines += ["", "Detailed results: [summary.csv](summary.csv), [every comparison](trials.csv), [data/config/code identity](manifest.json), and [failure details](report.json).", "", "A completed task can yield only inconclusive comparisons. Bootstrap intervals are approximate, conditional on this issuer panel, and subject to block stationarity. A positive result is discovery evidence only."]
    (run_path / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def record_ledger(run_path):
    """Single coordinator only. Idempotently append per-comparison history.

    Remote jobs do not edit the checkout's human ledger. Run this locally after
    downloading/verifying results. Never fabricate registration/code commits.
    """
    run_path = Path(run_path).resolve()
    m = read_manifest(run_path)
    report = read_json(run_path / "report.json")
    if report["manifest_id"] != m["manifest_id"]:
        raise ValueError("Aggregate belongs to another manifest")
    ledger = ROOT / "Hypotheses/EXPERIMENTS.csv"
    with ledger.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields, prior = reader.fieldnames, list(reader)
    existing = {r["experiment_id"] for r in prior}
    with (run_path / "trials.csv").open(newline="", encoding="utf-8") as f:
        trial_rows = list(csv.DictReader(f))
    trial_rows += [{"study": f["study"], "status": "failed", "reason": f["reason"], "task": f["task"]} for f in report["failures"]]
    for attempt_path in sorted((run_path / "studies").glob("*/attempt-*.json")):
        attempt = read_json(attempt_path)
        trial_rows.append({"study": attempt["task"]["study"], "status": attempt["status"], "reason": attempt.get("error"), "task": attempt["task"]["id"], "attempt_result_id": attempt["result_id"]})
    added = []
    for i, trial in enumerate(trial_rows):
        eid = f"discovery-{m['manifest_id'][:12]}-{identity(trial)[:16]}"
        if eid in existing:
            continue
        row = {k: "" for k in fields}
        row.update(experiment_id=eid, registered_at=m["created_at"], hypothesis_id=trial["study"], sample_or_fold="synthetic engineering" if m["synthetic"] else "2024-2025 development discovery", parameters=__import__("json").dumps(trial, sort_keys=True), signal_and_fill_timing="Assumed next-day event availability; at-close features; later outcomes; no fills", cost_model="Not applicable: statistical discovery", data_identity=m["snapshot_id"], outcome=trial["status"], evidence_path=str(run_path.relative_to(ROOT)).replace("\\", "/"), notes=f"Unregistered discovery; timestamp is run planning, not economic hypothesis registration; code content identity {identity(m['code_files'])}")
        added.append(row)
    with ledger.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writerows(added)
    for study in STUDIES:
        log = ROOT / "Hypotheses" / STUDIES[study] / "Research Log.md"
        marker = f"<!-- discovery:{m['manifest_id']} -->"
        text = log.read_text(encoding="utf-8") if log.exists() else f"# {study}: discovery history\n\nNo economic hypothesis registration or strategy implementation is recorded here.\n"
        if marker not in text:
            relative = os.path.relpath(run_path, log.parent).replace("\\", "/")
            study_summary = next(r for r in report["summary"] if r["study"] == study)
            table_link = f"[This study's table]({relative}/studies/{study}/measurements.csv), " if study_summary["evidence"] else "No measured table was produced. "
            text += f"\n{marker}\n\n## {m['created_at']}: {m['run_id']}\n\n{'Synthetic pipeline verification' if m['synthetic'] else 'Real-data development statistics'}. Study task status: {study_summary['status']}; measured comparisons: {study_summary['measured']}; inconclusive comparisons: {study_summary['inconclusive']}. {table_link}[Run report]({relative}/REPORT.md), [all attempted comparisons]({relative}/trials.csv), [snapshot/code/config identity]({relative}/manifest.json). Evidence remains in ignored local results; remote copies must be returned and verified before logging. No final holdout, orders or P&L. Read [implementation coverage](../../docs/discovery/README.md) for the calculations and unresolved inferential limits.\n"
            log.write_text(text, encoding="utf-8")
    return len(added)
