"""Return a versioned readout with superseded category-level inference removed."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
import pandas as pd
from .atlas import manifest, done, scheduled, receipt
from .io import ROOT, digest, read_json, write_json, now


def clean_master(frame):
    if len(frame) != 119 or frame.category.nunique() != 119:
        raise ValueError('All 119 categories required')
    # The original parent report inherited these extrema from the superseded
    # sampler. Amended inference lives in the exact-ID detailed comparisons.
    return frame.drop(columns=['adjusted_p_min_63', 'adjusted_p_min_126'], errors='ignore')


def run(stage, archive):
    scheduled()
    stage = Path(stage).resolve()
    m = manifest(stage)
    parent = ROOT / m['parent_run']
    if manifest(parent)['manifest_id'] != m['parent_manifest_id']:
        raise ValueError('Parent differs')
    if not all([done(stage, 'readout'), done(stage, 'inference'), done(parent, 'report')]):
        raise ValueError('Verified completed inputs required')
    source = stage / 'outputs/readout'
    folder = stage / 'outputs/readout-v2'
    if folder.exists() or Path(archive).exists():
        raise ValueError('Preserve earlier readouts and archives')
    folder.mkdir()
    clean_master(pd.read_csv(source / 'master.csv')).to_csv(folder / 'master.csv', index=False)
    for name in ['comparisons.csv', 'broad-panel.csv', 'cross-year-forecasts.csv']:
        shutil.copyfile(source / name, folder / name)
        if digest(source / name) != digest(folder / name):
            raise ValueError('Copied readout differs')
    summary = read_json(source / 'summary.json')
    summary.update({
        'readout_version': 2,
        'correction': 'Removed inherited adjusted_p_min_63/126 from superseded parent inference; detailed amended inference and all readout counts unchanged',
        'correction_at': now(),
        'correction_code_sha256': digest(Path(__file__)),
        'input_sha256': {
            'first_readout_receipt': digest(stage / 'receipts/readout.json'),
            'amended_inference': digest(stage / 'outputs/inference.csv'),
            'parent_report_receipt': digest(parent / 'receipts/report.json'),
            'parent_comparisons': digest(parent / 'outputs/comparisons.csv'),
            'parent_master': digest(parent / 'outputs/master.csv'),
        },
    })
    write_json(folder / 'summary.json', summary)
    note = (source / 'Findings.md').read_text(encoding='utf-8')
    note += '\n## Readout version 2\n\nThe category master omits two inherited confidence extrema from the superseded sampler. The detailed comparison confidence columns, cross-year results and all counts above are unchanged. Version 1 and its receipt remain retained. The summary records the original readout, amended inference and actual parent report input hashes.\n'
    (folder / 'Findings.md').write_text(note, encoding='utf-8', newline='\n')
    files = sorted(folder.iterdir())
    receipt(stage, 'readout-v2', files, extra={'correction_code_sha256': digest(Path(__file__)), 'scientific_results_changed': False})
    paths = files + [stage / 'manifest.json', stage / 'receipts/readout-v2.json']
    hashes = {p.relative_to(stage).as_posix(): digest(p) for p in paths}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for name, h in hashes.items():
            raw = (stage / name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != h:
                raise ValueError('Readout output changed')
            zipped.writestr(name, raw)
        zipped.writestr('RETURN-RECEIPT.json', json.dumps({'manifest_id': m['manifest_id'], 'files': hashes, 'scope': 'Complete corrected staged stock readout; options/full-search placebos pending'}))
    print(json.dumps({'sha256': digest(archive), 'members': len(hashes), 'summary': summary}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--stage', required=True)
    p.add_argument('--archive', required=True)
    a = p.parse_args()
    run(a.stage, a.archive)
