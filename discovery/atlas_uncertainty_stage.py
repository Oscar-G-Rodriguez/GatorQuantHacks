"""Separate, hash-linked year-stratified uncertainty for frozen H21 stock fits."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

from .atlas import manifest, scheduled, loss_matrix, receipt, done, write_table
from .atlas_statistics import romano_wolf
from .io import ROOT, digest, identity, now, read_json, write_json

AMENDMENT = 'Hypotheses/H21 - Massive Disclosure Research Atlas/Uncertainty Amendment.md'
AMENDMENT_COMMIT = 'f9de563'
METHOD = 'joint-issuer-and-year-stratified-circular-calendar-blocks-v1'


def year_weights(issuers, sessions, years, block, rng):
    """One issuer draw; common calendar counts within every annual stratum."""
    issuers, sessions, years = map(np.asarray, (issuers, sessions, years))
    if not (len(issuers) == len(sessions) == len(years)) or block < 1:
        raise ValueError('Invalid sampling dimensions or block length')
    if not len(issuers):
        return np.zeros(0)
    unique, inverse = np.unique(issuers, return_inverse=True)
    counts = np.bincount(rng.integers(0, len(unique), len(unique)), minlength=len(unique))
    calendar = np.zeros(len(issuers))
    for year in np.unique(years):
        mask = years == year
        dates = np.unique(sessions[mask])
        if np.any(np.isin(dates, sessions[~mask])):
            raise ValueError('A calendar session belongs to multiple years')
        n = len(dates)
        starts = rng.integers(0, n, size=int(np.ceil(n / block)))
        sampled = ((starts[:, None] + np.arange(block)) % n).ravel()[:n]
        date_counts = np.bincount(sampled, minlength=n)
        calendar[mask] = date_counts[np.searchsorted(dates, sessions[mask])]
    return counts[inverse] * calendar


def adjusted_results(point, draws):
    """Undefined sparse draws remain unsupported, rather than conditionally redrawn."""
    finite = np.isfinite(draws).sum(axis=0)
    sd = np.nanstd(draws, axis=0, ddof=1)
    valid = np.isfinite(point) & (sd > 0) & (finite == len(draws))
    p = np.full(len(point), np.nan)
    if valid.any():
        p[valid] = romano_wolf(point[valid] / sd[valid], (draws[:, valid] - point[valid]) / sd[valid])
    return valid, p, finite


def prepare(parent, stage, remote, workers=64):
    parent, stage = Path(parent).resolve(), Path(stage).resolve()
    pm = manifest(parent, allow_frozen=True)
    if not stage.is_relative_to(ROOT) or not 1 <= workers <= 64:
        raise ValueError('Invalid private stage path or workers')
    stage.mkdir(parents=True, exist_ok=False)
    m = {k: pm[k] for k in ['schema', 'study', 'plan_commit', 'source', 'source_id', 'source_sha256', 'settings', 'sealed_excluded']}
    m.update(created_at=now(), run=stage.relative_to(ROOT).as_posix(), parent_run=parent.relative_to(ROOT).as_posix(),
             parent_manifest_id=pm['manifest_id'], parent_manifest_sha256=digest(parent / 'manifest.json'),
             method=METHOD, amendment_commit=AMENDMENT_COMMIT,
             code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             code={name: digest(ROOT / name) for name in ['discovery/atlas_uncertainty_stage.py', 'discovery/atlas_return.py', AMENDMENT]})
    m['manifest_id'] = identity(m)
    write_json(stage / 'manifest.json', m)
    jobs = stage / 'hpg'; jobs.mkdir()
    batches = int(np.ceil(m['settings']['resamples'] / m['settings']['resample_batch']))
    prefix = f'''#!/bin/bash
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=02:00:00
#SBATCH --chdir={remote}
'''
    setup = f'''set -euo pipefail
umask 077
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
unset PYTHONHOME PYTHONPATH
cd '{remote}'
'''
    command = f".venv/bin/python -B -m discovery.atlas_uncertainty_stage --stage '{m['run']}'"
    (jobs / 'resample.sbatch').write_text(prefix + f'''#SBATCH --mem=16gb
#SBATCH --job-name=h21-ci2-draw
#SBATCH --output={remote}/h21-ci2-draw-%A-%a.out
#SBATCH --array=0-{batches * len(m['settings']['block_lengths']) - 1}%{workers}
''' + setup + f'''BLOCKS=(63 126)
BATCH=$((SLURM_ARRAY_TASK_ID % {batches}))
BLOCK=${{BLOCKS[$((SLURM_ARRAY_TASK_ID / {batches}))]}}
{command} resample --batch "$BATCH" --block "$BLOCK"
''', encoding='utf-8', newline='\n')
    (jobs / 'inference.sbatch').write_text(prefix + f'''#SBATCH --mem=128gb
#SBATCH --job-name=h21-ci2-infer
#SBATCH --output={remote}/h21-ci2-infer-%j.out
''' + setup + command + ' inference\n', encoding='utf-8', newline='\n')
    (jobs / 'return.sbatch').write_text(prefix + f'''#SBATCH --mem=4gb
#SBATCH --job-name=h21-ci2-return
#SBATCH --output={remote}/h21-ci2-return-%j.out
''' + setup + f".venv/bin/python -B -m discovery.atlas_return --run '{m['run']}' --output returned-uncertainty-v2.zip\nsha256sum returned-uncertainty-v2.zip > returned-uncertainty-v2.sha256\n", encoding='utf-8', newline='\n')
    script = f'''#!/bin/bash
set -euo pipefail
cd '{remote}'
DRAWS=$(sbatch --parsable '{m['run']}/hpg/resample.sbatch')
INFER=$(sbatch --parsable --dependency=afterok:$DRAWS '{m['run']}/hpg/inference.sbatch')
RETURN=$(sbatch --parsable --dependency=afterok:$INFER '{m['run']}/hpg/return.sbatch')
echo "draws=$DRAWS inference=$INFER return=$RETURN" | tee submission-uncertainty-v2.txt
'''
    (jobs / 'submit.sh').write_text(script, encoding='utf-8', newline='\n')
    return {'manifest_id': m['manifest_id'], 'workers': workers, 'batches': batches * 2}


def parent_losses(stage):
    m = manifest(stage)
    parent = ROOT / m['parent_run']
    if digest(parent / 'manifest.json') != m['parent_manifest_sha256'] or manifest(parent)['manifest_id'] != m['parent_manifest_id']:
        raise ValueError('Frozen parent identity differs')
    return m, loss_matrix(parent)


def resample(stage, batch, block):
    scheduled(); stage = Path(stage)
    label = f'resample-{block}-{batch:03d}'
    if done(stage, label): return
    m, (panel, c, names, values, indicator) = parent_losses(stage)
    start = batch * c['resample_batch']; end = min(c['resamples'], start + c['resample_batch'])
    if block not in c['block_lengths'] or not 0 <= start < end:
        raise ValueError('Task outside declared mapping')
    result = np.full((end - start, len(names)), np.nan)
    base = panel.weight.to_numpy()
    years = panel.date.dt.year.to_numpy()
    for offset, draw in enumerate(range(start, end)):
        rng = np.random.default_rng(c['seed'] + block * 1000000 + draw)
        w = base * year_weights(panel.issuer.to_numpy(), panel.session.to_numpy(), years, block, rng)
        numerator = np.asarray(values.T @ w).ravel(); denominator = np.asarray(indicator.T @ w).ravel()
        result[offset] = np.divide(numerator, denominator, out=np.full(len(names), np.nan), where=denominator > 0)
    folder = stage / 'uncertainty'; folder.mkdir(exist_ok=True)
    path = folder / (label + '.npz')
    np.savez_compressed(path, draws=result, names=np.array(names))
    receipt(stage, label, [path], extra={'start': start, 'end': end, 'block': block, 'method': m['method']})


def inference(stage):
    scheduled(); stage = Path(stage)
    if done(stage, 'inference'): return
    m, (panel, c, names, values, indicator) = parent_losses(stage)
    w = panel.weight.to_numpy(); num = np.asarray(values.T @ w).ravel(); den = np.asarray(indicator.T @ w).ravel()
    point = np.divide(num, den, out=np.full(len(names), np.nan), where=den > 0)
    rows = []
    for block in c['block_lengths']:
        arrays = []
        for batch in range(int(np.ceil(c['resamples'] / c['resample_batch']))):
            label = f'resample-{block}-{batch:03d}'
            if not done(stage, label): raise ValueError('Incomplete uncertainty stage')
            with np.load(stage / 'uncertainty' / (label + '.npz'), allow_pickle=False) as data:
                if list(data['names']) != names: raise ValueError('Comparison order differs')
                arrays.append(data['draws'])
        draws = np.vstack(arrays); del arrays
        if len(draws) != c['resamples']: raise ValueError('Draw accounting differs')
        valid, p, finite = adjusted_results(point, draws)
        for i, name in enumerate(names):
            lo, hi = np.nanquantile(draws[:, i], [.025, .975]) if finite[i] else (np.nan, np.nan)
            rows.append({'comparison_id': name, 'block_sessions': block, 'estimate': point[i],
                         'pointwise_lower': lo, 'pointwise_upper': hi, 'romano_wolf_p': p[i],
                         'resamples': len(draws), 'finite_resamples': int(finite[i]), 'missing_resamples': int(len(draws)-finite[i]),
                         'family_size': len(names), 'adjusted_family_size': int(valid.sum()),
                         'inference_status': 'approximate_exploratory' if valid[i] else 'unsupported', 'method': m['method']})
        del draws
    write_table(stage / 'outputs/inference.csv', rows)
    write_json(stage / 'outputs/summary.json', {'manifest_id': m['manifest_id'], 'parent_manifest_id': m['parent_manifest_id'],
        'method': m['method'], 'comparisons': len(names), 'rows': len(rows), 'alpha_claim': False,
        'complete_atlas': False, 'remaining': ['499 full-search placebos', 'complete option stage'], 'generated_at': now()})
    receipt(stage, 'inference', [stage / 'outputs/inference.csv', stage / 'outputs/summary.json'])


def main():
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['prepare', 'resample', 'inference'])
    p.add_argument('--stage', required=True); p.add_argument('--parent'); p.add_argument('--remote')
    p.add_argument('--workers', type=int, default=64); p.add_argument('--batch', type=int); p.add_argument('--block', type=int)
    a = p.parse_args()
    if a.action == 'prepare': print(json.dumps(prepare(a.parent, a.stage, a.remote, a.workers)))
    else:
        try:
            if a.action == 'resample': resample(a.stage, a.batch, a.block)
            else: inference(a.stage)
        except Exception as error:
            write_json(Path(a.stage) / 'attempts' / (a.action + '-' + now().replace(':', '') + '.json'),
                       {'action': a.action, 'batch': a.batch, 'block': a.block, 'status': 'failed', 'error': repr(error), 'at': now()})
            raise


if __name__ == '__main__': main()
