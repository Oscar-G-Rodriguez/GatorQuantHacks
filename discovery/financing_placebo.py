"""Append-only exact-source financing timing-placebo stages.

Metadata registration and transfer preparation use the standard library on the
PC. Shift matching and trading calculations require Slurm. Partial acquisitions
are preserved as pending extensions, never converted into traded observations.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import tarfile
import time

from .io import ROOT, digest, identity, now, read_json, write_json, remote_base
from .financing_pipeline import CONFIG, REGISTRATION


def child_path(base, relative):
    base = Path(base).resolve(); relative = str(relative).replace('\\', '/')
    if Path(relative).is_absolute() or ':' in relative.split('/')[0] or any(part in {'..', '.env'} for part in relative.split('/')):
        raise ValueError('Unsafe placebo member path')
    result = (base / relative).resolve()
    if not result.is_relative_to(base):
        raise ValueError('Placebo member escapes its workspace')
    return result


def base_manifest(run):
    run = Path(run).resolve()
    if not run.is_relative_to(ROOT.resolve()):
        raise ValueError('Placebo run is outside repository workspace')
    manifest = read_json(run / 'manifest.json')
    if (manifest.get('registration_commit') != REGISTRATION or
            manifest.get('manifest_id') != identity({k: v for k, v in manifest.items() if k != 'manifest_id'})):
        raise ValueError('Base immutable manifest differs')
    for relative, expected in manifest['files'].items():
        if digest(child_path(ROOT, relative)) != expected:
            raise ValueError('Base immutable member changed: ' + relative)
    return manifest


def check_receipt(run, stage, base_id):
    path = Path(run) / 'receipts' / (stage + '.json')
    if not path.exists():
        return None
    record = read_json(path)
    if record.get('manifest_id') != base_id or record.get('status') != 'completed' or not record.get('files'):
        raise ValueError('Incomplete or mismatched placebo receipt: ' + stage)
    for relative, expected in record['files'].items():
        if digest(child_path(run, relative)) != expected:
            raise ValueError('Placebo receipt member changed: ' + relative)
    return record


def required_member(run, receipt, path):
    name = Path(path).relative_to(run).as_posix()
    if not receipt or name not in {str(k).replace('\\', '/') for k in receipt['files']}:
        raise ValueError('Required placebo member is not receipted: ' + name)


def replica_folder(run, replica):
    cfg = read_json(CONFIG)
    if not isinstance(replica, int) or isinstance(replica, bool) or not 0 <= replica < cfg['timing_placebos']:
        raise ValueError('Replica is outside the frozen199-map family')
    return child_path(run, 'placebos/' + str(replica))


def prepared_inputs(run, replica, manifest):
    folder = replica_folder(run, replica); prepared = folder / 'prepared'
    checked = check_receipt(run, f'placebo-prepare-{replica}', manifest['manifest_id'])
    if not checked:
        raise RuntimeError('Shifted matching has not returned a verified preparation receipt')
    roots = [Path(run) / 'prepared' / name for name in ['placebo-map.json', 'calendar.json', 'actions.json']]
    if any(path.relative_to(ROOT).as_posix() not in manifest['files'] for path in roots):
        original = check_receipt(run, 'prepare', manifest['manifest_id'])
        for path in roots:
            if path.relative_to(ROOT).as_posix() not in manifest['files']:
                required_member(run, original, path)
    maps = read_json(Path(run) / 'prepared/placebo-map.json')
    if len(maps) != read_json(CONFIG)['timing_placebos'] or maps[replica].get('replica') != replica:
        raise ValueError('Frozen timing map identity/count differs')
    for name in ['anchors.json', 'calendar.json', 'map.json']:
        required_member(run, checked, prepared / name)
    if read_json(prepared / 'map.json') != maps[replica]:
        raise ValueError('Shifted preparation is not the frozen map')
    if read_json(prepared / 'calendar.json') != read_json(Path(run) / 'prepared/calendar.json'):
        raise ValueError('Shifted preparation changed the approved session grid')
    actions = prepared / 'actions.json'; original = Path(run) / 'prepared/actions.json'
    if actions.exists():
        if digest(actions) != digest(original):
            raise ValueError('Shifted corporate actions differ from base source')
    else:
        shutil.copyfile(original, actions)
    anchors = read_json(prepared / 'anchors.json'); seen = set()
    for anchor in anchors:
        key = (anchor['anchor_id'], anchor['shape'])
        if key in seen or anchor['variant'] != 'primary':
            raise ValueError('Duplicate or unregistered shifted anchor')
        seen.add(key)
    if len({a['anchor_id'] for a in anchors}) != len(anchors):
        raise ValueError('Shifted anchor IDs are not unique across shapes')
    return folder, anchors


def acquisition_snapshot(folder, anchors):
    path = folder / 'acquisition/source.json'
    if not path.exists():
        return {'ready': False, 'source_id': None, 'status': 'pending', 'reason': 'exact_source_not_acquired',
                'records': 0, 'required_anchors': len(anchors)}, []
    source = read_json(path)
    if (source.get('registration_commit') != REGISTRATION or
            source.get('settings_sha256') != digest(CONFIG) or
            source.get('anchors_sha256') != digest(folder / 'prepared/anchors.json') or
            source.get('source_id') != identity({k: v for k, v in source.items() if k != 'source_id'})):
        raise ValueError('Shifted source identity/settings/anchors differ')
    frozen = {a['anchor_id']: a for a in anchors}; seen = set()
    for record in source.get('records', []):
        aid = record['anchor_id']
        if aid in seen or aid not in frozen or any(record.get(k) != v for k, v in frozen[aid].items()):
            raise ValueError('Acquisition record changed or invented a shifted anchor')
        seen.add(aid)
        for key in ['stock_object', 'chain_object', 'option_object']:
            if record.get(key) and record[key] not in source.get('objects', {}):
                raise ValueError('Shifted anchor references a missing frozen source object')
        for quote in record.get('quote_objects', {}).values():
            if quote.get('object') and quote['object'] not in source.get('objects', {}):
                raise ValueError('Shifted anchor references a missing quote object')
    files = [path]
    for key, obj in source.get('objects', {}).items():
        target = child_path(folder / 'acquisition/objects', key + '.json')
        if digest(target) != obj['sha256']:
            raise ValueError('Exact shifted source member changed')
        files.append(target)
        evidence = target.with_name(key + '.receipt.json')
        if evidence.exists():
            files.append(evidence)
    unresolved = sum(r.get('status') in {'pending', 'request_failed'} for r in source.get('records', []))
    ready = source.get('complete') is True
    if ready and (len(seen) != len(anchors) or source.get('required_anchors') != len(anchors) or unresolved):
        raise ValueError('Source claims completeness with missing/unresolved anchors')
    return {'ready': ready, 'source_id': source['source_id'], 'status': 'ready' if ready else 'pending',
            'reason': '' if ready else 'exact_acquisition_incomplete', 'records': len(seen),
            'required_anchors': len(anchors), 'unresolved_records': unresolved,
            'failures_recorded': len(source.get('failures', []))}, files


def register_acquisition(run, replica):
    """PC metadata-only snapshot; ready extensions are subsequently immutable."""
    run = Path(run).resolve(); manifest = base_manifest(run)
    folder, anchors = prepared_inputs(run, replica, manifest)
    current = folder / 'extension.json'
    if current.exists() and read_json(current).get('ready'):
        return verify_extension(run, replica)
    coverage, acquired = acquisition_snapshot(folder, anchors)
    files = [p for p in (folder / 'prepared').glob('*') if p.is_file()] + acquired
    if any(p.is_symlink() for p in files):
        raise ValueError('Symlinked inputs cannot become immutable archive members')
    hashes = {p.relative_to(run).as_posix(): digest(p) for p in files}
    payload = {'schema': 1, 'study': 'financing-round2-timing-placebo', 'replica': replica,
               'base_manifest_id': manifest['manifest_id'], 'registration_commit': REGISTRATION,
               'settings_sha256': digest(CONFIG), 'map_id': identity(read_json(folder / 'prepared/map.json')),
               'scope': 'primary variants/all three registered studies; exact shifted historical inputs',
               **coverage, 'files': hashes}
    if current.exists():
        prior = read_json(current)
        if {k: v for k, v in prior.items() if k not in {'extension_id', 'registered_at'}} == payload:
            return prior
    payload['registered_at'] = now(); payload['extension_id'] = identity(payload)
    version = folder / 'extensions' / (payload['extension_id'] + '.json')
    if version.exists() and read_json(version) != payload:
        raise ValueError('Extension version collision')
    write_json(version, payload); write_json(current, payload)
    if payload['ready']:
        write_json(run / 'receipts' / f'placebo-acquire-{replica}.json', {
            'manifest_id': manifest['manifest_id'], 'status': 'completed', 'completed_at': now(), 'job_id': None,
            'scope': 'PC acquisition validation; no scientific calculation', 'replica': replica,
            'extension_id': payload['extension_id'], 'source_id': payload['source_id'],
            'files': {**hashes, current.relative_to(run).as_posix(): digest(current),
                      version.relative_to(run).as_posix(): digest(version)}})
    return payload


def verify_extension(run, replica, allow_partial=False):
    run = Path(run).resolve(); manifest = base_manifest(run); folder = replica_folder(run, replica)
    record = read_json(folder / 'extension.json')
    if (record.get('base_manifest_id') != manifest['manifest_id'] or record.get('replica') != replica or
            record.get('registration_commit') != REGISTRATION or record.get('settings_sha256') != digest(CONFIG) or
            record.get('extension_id') != identity({k: v for k, v in record.items() if k != 'extension_id'})):
        raise ValueError('Placebo extension identity differs')
    for relative, expected in record['files'].items():
        target = child_path(run, relative)
        if not target.is_relative_to(folder) or digest(target) != expected:
            raise ValueError('Placebo extension member changed or escaped its replica')
    if not record['ready'] and not allow_partial:
        raise RuntimeError('Exact shifted acquisition is pending; no outcomes may be substituted')
    if record['ready']:
        checked = check_receipt(run, f'placebo-acquire-{replica}', manifest['manifest_id'])
        required_member(run, checked, folder / 'extension.json')
        if checked.get('extension_id') != record['extension_id']:
            raise ValueError('Acquisition receipt belongs to another extension')
    return record


def acquire_replica(run, replica, quotes=True, request_cap=None):
    """PC acquisition only; the network execution remains an explicit command."""
    run = Path(run).resolve(); manifest = base_manifest(run)
    folder, _ = prepared_inputs(run, replica, manifest)
    if (folder / 'extension.json').exists() and read_json(folder / 'extension.json').get('ready'):
        return verify_extension(run, replica)
    from .financing_acquire import acquire
    try:
        acquire(folder / 'prepared', folder / 'acquisition', quotes=quotes, request_cap=request_cap)
    finally:
        # A failed/rate-limited phase still registers its honest partial state.
        result = register_acquisition(run, replica)
    return result


def scheduled():
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('Placebo matching and trading calculations require a scheduled HiPerGator allocation')


def csv_write(path, rows, fields=None):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or sorted({k for row in rows for k in row}) or ['status']
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def run_study(run, replica, study):
    """Rerun the financing engine on exact shifted observations, not old P&L."""
    scheduled(); run = Path(run).resolve(); manifest = base_manifest(run)
    cfg = read_json(CONFIG)
    if study not in {s['id'] for s in cfg['studies']}:
        raise ValueError('Study is not in the frozen financing family')
    extension = verify_extension(run, replica); folder = replica_folder(run, replica)
    stage = f'placebo-task-{replica}-{study}'
    completed = check_receipt(run, stage, manifest['manifest_id'])
    if completed:
        if completed.get('extension_id') != extension['extension_id']:
            raise ValueError('Completed placebo task belongs to a different exact source')
        return completed
    from .financing_strategy import Data, owned_strategy, unit_trade, quoted_diagnostics, Ledger, replay, performance
    started = time.monotonic(); data = Data(folder)
    if data.source['source_id'] != extension['source_id']:
        raise ValueError('Engine source differs from the frozen extension')
    selected = [r for r in data.records if r['study'] == study and r['variant'] == 'primary']
    strategy_class = owned_strategy(data, study)
    trades, nav, portfolios = [], [], []
    label = {'task': f'placebo-{replica}-{study}', 'study': study, 'variant': 'primary'}
    for record in selected:
        for horizon in [*cfg['horizons'], 'expiry']:
            for stock_only in [False, True]:
                outcome = unit_trade(record, data, horizon, stock_only)
                trades.append({**label, **outcome, **quoted_diagnostics(record, data, outcome, stock_only)})
    for shape in cfg['shapes']:
        for role in ['event', 'ordinary', 'debt_only', 'underwriting_only']:
            anchors = [r for r in selected if r['shape'] == shape and r['role'] == role]
            strategy = Ledger(data, anchors); first = replay(strategy_class, strategy, data.dates)
            baseline = Ledger(data, first['accepted_entries'], True, True); second = replay(strategy_class, baseline, data.dates)
            for stock_only, result in [(False, first), (True, second)]:
                tag = {**label, 'shape': shape, 'role': role, 'stock_only': stock_only}
                nav.extend({**tag, **r} for r in result['daily'])
                portfolios.append({**tag, **performance(result, cfg)})
    output = folder / 'results' / study; output.mkdir(parents=True, exist_ok=True)
    csv_write(output / 'trades.csv', trades); csv_write(output / 'nav.csv', nav)
    details = {'status': 'completed', 'manifest_id': manifest['manifest_id'], 'replica': replica, 'study': study,
               'extension_id': extension['extension_id'], 'source_id': extension['source_id'],
               'map_id': extension['map_id'], 'records': len(selected), 'outcomes': len(trades),
               'elapsed_seconds': time.monotonic() - started, 'portfolios': portfolios,
               'interpretation': 'exact-source development timing placebo; no fresh OOS claim'}
    write_json(output / 'task.json', details)
    files = [output / 'trades.csv', output / 'nav.csv', output / 'task.json']
    result = {**details, 'job_id': os.environ['SLURM_JOB_ID'], 'completed_at': now(),
              'files': {p.relative_to(run).as_posix(): digest(p) for p in files}}
    write_json(run / 'receipts' / (stage + '.json'), result)
    return result


def bundle(run, replica, output):
    """An immutable ready extension can only append verified remote members."""
    run = Path(run).resolve(); manifest = base_manifest(run); record = verify_extension(run, replica)
    folder = replica_folder(run, replica); output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    files = dict(record['files'])
    for path in [folder / 'extension.json', folder / 'extensions' / (record['extension_id'] + '.json'),
                 run / 'receipts' / f'placebo-prepare-{replica}.json', run / 'receipts' / f'placebo-acquire-{replica}.json']:
        files[path.relative_to(run).as_posix()] = digest(path)
    members = {(run / relative).relative_to(ROOT).as_posix(): value for relative, value in files.items()}
    # Old pilot snapshots deliberately exclude unfinished additions. Include
    # the now-finished standalone stage and tests; incompatible remote files
    # are refused by the installer rather than changing the frozen base code.
    for relative in ['discovery/financing_placebo.py', 'tests/test_financing_placebo.py']:
        path = ROOT / relative
        if path.exists():
            if path.is_symlink():
                raise ValueError('Symlinked append code is unsupported')
            if relative in manifest['files'] and digest(path) != manifest['files'][relative]:
                raise ValueError('Declared base placebo code changed')
            members[relative] = digest(path)
    with tarfile.open(output, 'w:gz') as archive:
        for name in sorted(members):
            archive.add(ROOT / name, arcname=name, recursive=False)
    installer = output.with_name(output.name + '-install.py')
    script = '''from pathlib import Path
import hashlib,json,tarfile,os
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
dest=Path(DEST).resolve()
base=json.loads((dest/BASE_MANIFEST).read_text())
if base['manifest_id']!=BASE_ID:raise ValueError('Append target is another immutable run')
for name,h in base['files'].items():
 p=(dest/name).resolve()
 if not p.is_relative_to(dest) or sha(p)!=h:raise ValueError('Base member changed')
archive=Path(__file__).with_name(ARCHIVE)
if sha(archive)!=ARCHIVE_HASH:raise ValueError('Append archive hash differs')
with tarfile.open(archive,'r:gz') as tar:
 members=tar.getmembers()
 if len(members)!=len(FILES) or {m.name for m in members}!=set(FILES):raise ValueError('Append member set differs')
 for m in members:
  path=(dest/m.name).resolve()
  if not m.isfile() or not path.is_relative_to(dest) or '.env' in Path(m.name).parts:raise ValueError('Unsafe append member')
  payload=tar.extractfile(m).read()
  if hashlib.sha256(payload).hexdigest()!=FILES[m.name]:raise ValueError('Append member hash differs')
  if path.exists() and sha(path)!=FILES[m.name]:raise ValueError('Immutable append conflict')
 for m in members:
  path=dest/m.name
  if path.exists():continue
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(m).read());os.chmod(path,0o600)
print('Verified exact-source append',len(members),flush=True)
'''
    preface = f'ARCHIVE={output.name!r}\nARCHIVE_HASH={digest(output)!r}\nDEST={manifest["remote"]!r}\nBASE_MANIFEST={(run / "manifest.json").relative_to(ROOT).as_posix()!r}\nBASE_ID={manifest["manifest_id"]!r}\nFILES={members!r}\n'
    installer.write_text(preface + script, encoding='utf-8', newline='\n')
    result = {'replica': replica, 'base_manifest_id': manifest['manifest_id'], 'extension_id': record['extension_id'],
              'archive': str(output), 'sha256': digest(output), 'installer': str(installer),
              'installer_sha256': digest(installer), 'members': len(members), 'ready': True}
    write_json(folder / 'transfer.json', result)
    return result


def jobs(run, replicas=None):
    """Generate scheduler batches; unacquired replicas have no run submission."""
    run = Path(run).resolve(); manifest = base_manifest(run); cfg = read_json(CONFIG)
    selected = list(range(cfg['timing_placebos'])) if replicas is None else sorted(set(replicas))
    for replica in selected:
        replica_folder(run, replica)
    directory = run / 'hpg'; directory.mkdir(parents=True, exist_ok=True)
    relative = run.relative_to(ROOT).as_posix(); remote = manifest['remote']
    remote_python = remote_base() + '/atlas-v3/.venv/bin/python'
    common = f'''#!/bin/bash
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem={cfg['worker_memory_gb']}gb
#SBATCH --time={cfg['worker_hours']:02d}:00:00
#SBATCH --chdir={remote}
'''
    tail = 'set -euo pipefail\nexport OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1\n'
    if selected:
        preparation = common + f"#SBATCH --job-name=fin2-placebo-prepare\n#SBATCH --output={remote}/fin2-placebo-prepare-%A-%a.out\n#SBATCH --array={','.join(map(str, selected))}%{cfg['pilot_workers']}\n" + tail
        preparation += f'"{remote_python}" -B -m discovery.financing_pipeline exec --stage placebo-prepare --run "{relative}" --replica "$SLURM_ARRAY_TASK_ID"\n'
        (directory / 'placebo-prepare.sbatch').write_text(preparation, encoding='utf-8', newline='\n')
    studies = [s['id'] for s in cfg['studies']]; ready = []
    for replica in selected:
        folder = replica_folder(run, replica)
        if not (folder / 'extension.json').exists():
            continue
        extension = verify_extension(run, replica, allow_partial=True)
        if extension['ready']:
            ready.extend(replica * len(studies) + i for i in range(len(studies)))
    if ready:
        content = common + f"#SBATCH --job-name=fin2-placebo-run\n#SBATCH --output={remote}/fin2-placebo-run-%A-%a.out\n#SBATCH --array={','.join(map(str, ready))}%{min(cfg['initial_workers'], cfg['absolute_worker_cap'])}\n" + tail
        content += f"studies=({' '.join(studies)})\nreplica=$((SLURM_ARRAY_TASK_ID / {len(studies)}))\nstudy_index=$((SLURM_ARRAY_TASK_ID % {len(studies)}))\n"
        content += f'"{remote_python}" -B -m discovery.financing_placebo run --run "{relative}" --replica "$replica" --study "${{studies[$study_index]}}"\n'
        (directory / 'placebo-run.sbatch').write_text(content, encoding='utf-8', newline='\n')
    plan = {'base_manifest_id': manifest['manifest_id'], 'registered_replicas': cfg['timing_placebos'],
            'planned_study_tasks': cfg['timing_placebos'] * len(studies), 'selected_replicas': selected,
            'ready_study_tasks': ready, 'run_script_generated': bool(ready),
            'status': 'ready_subset' if ready else 'pending_exact_acquisition'}
    write_json(directory / 'placebo-job-plan.json', plan)
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['register', 'acquire', 'run', 'bundle', 'jobs', 'verify'])
    parser.add_argument('--run', type=Path, required=True); parser.add_argument('--replica', type=int)
    parser.add_argument('--study'); parser.add_argument('--output', type=Path)
    parser.add_argument('--request-cap', type=int); parser.add_argument('--skip-quotes', action='store_true')
    args = parser.parse_args(argv)
    if args.stage != 'jobs' and args.replica is None:
        parser.error('--replica is required for this stage')
    if args.stage == 'bundle' and args.output is None:
        parser.error('--output is required for bundle')
    if args.stage == 'run' and args.study is None:
        parser.error('--study is required for run')
    if args.stage == 'register': result = register_acquisition(args.run, args.replica)
    elif args.stage == 'verify': result = verify_extension(args.run, args.replica, allow_partial=True)
    elif args.stage == 'acquire': result = acquire_replica(args.run, args.replica, not args.skip_quotes, args.request_cap)
    elif args.stage == 'run': result = run_study(args.run, args.replica, args.study)
    elif args.stage == 'bundle': result = bundle(args.run, args.replica, args.output)
    else: result = jobs(args.run, [args.replica] if args.replica is not None else None)
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
