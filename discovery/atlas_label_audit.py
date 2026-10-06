"""Source-only H21 label cohorts and evidence-backed, optional annotations.

The registered protocol owns the meanings; this module never infers them from
keywords. Preparation/transfer run locally, while source aggregation requires
a scheduler allocation. All licensed excerpts stay in private run directories.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .io import ROOT, digest, identity, now, read_json, write_json, safe_child

FOLDER = Path('Hypotheses/H21 - Massive Disclosure Research Atlas')
PLAN_COMMIT = '88db95aee74ea54f2fe8da0ea022673c8aa55717'
SEED = 'H21-standard-label-audit-v1'
FIELDS = {
    'debt_issuance': {
        'transaction_stage': ['completed', 'planned', 'mixed', 'unknown'],
        'cash_receipt': ['explicit_receipt', 'unknown'],
    },
    'executive_officer_departure': {
        'transition_context': ['planned_transition', 'abrupt_departure', 'mixed', 'unknown'],
    },
    'guidance_issuance_or_update': {
        'guidance_direction': ['raised', 'lowered', 'mixed', 'reaffirmed', 'initial', 'unknown'],
    },
}
COUNT_FIELDS = ['filings', 'issuers', *[f'filings_{y}' for y in range(2022, 2026)]]


def table(path, rows, fields):
    with Path(path).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def primary_records(taxonomy, collections):
    """Deduplicate appearances, preserving unknown text and all label bundles."""
    definitions = {d['tertiary_category']: d for d in taxonomy}
    if len(definitions) != len(taxonomy):
        raise ValueError('Duplicate taxonomy entries')
    records, filing_dates = {}, {}
    for oid, collection_cik, rows in collections:
        for index, row in enumerate(rows):
            category = row['tertiary_category']
            if category not in definitions:
                raise ValueError('Unknown category: ' + category)
            cik, accession, date = row['cik'], row['accession_number'], row['filing_date']
            if not cik or not accession or cik != collection_cik:
                raise ValueError('Missing or conflicting issuer/accession identity')
            datetime.strptime(date, '%Y-%m-%d')
            if not '2022-01-01' <= date <= '2025-12-31':
                raise ValueError('Date outside H21 development window')
            filing_key = (cik, accession)
            if filing_key in filing_dates and filing_dates[filing_key] != date:
                raise ValueError('Conflicting filing dates')
            filing_dates[filing_key] = date
            definition = definitions[category]
            for level in ['primary_category', 'secondary_category']:
                if row[level] != definition[level]:
                    raise ValueError('Conflicting category hierarchy')
            key = (cik, accession, category)
            if key not in records:
                records[key] = {
                    'record_id': identity({'cik': cik, 'accession': accession, 'category': category}),
                    'cik': cik, 'accession': accession, 'filing_date': date,
                    'category': category, 'excerpts': [], 'provenance': [],
                }
            record = records[key]
            text = row.get('supporting_text')
            if text is not None and not isinstance(text, str):
                raise ValueError('Unexpected excerpt type')
            if text and text.strip() and text not in record['excerpts']:
                record['excerpts'].append(text)
            record['provenance'].append({'object_id': oid, 'row_index': index})
    return sorted(records.values(), key=lambda r: r['record_id'])


def coverage(taxonomy, records):
    by_category = defaultdict(list)
    for row in records:
        by_category[row['category']].append(row)
    result = []
    for definition in taxonomy:
        category = definition['tertiary_category']
        rows = by_category[category]
        result.append({
            'category': category, 'description': definition['description'],
            'filings': len(rows), 'issuers': len({r['cik'] for r in rows}),
            **{f'filings_{y}': sum(r['filing_date'].startswith(str(y)) for r in rows) for y in range(2022, 2026)},
            'missing_text_filings': sum(not r['excerpts'] for r in rows),
        })
    return result


def review_cards(taxonomy, records):
    definitions = {d['tertiary_category']: d['description'] for d in taxonomy}
    cards, key, strata = [], [], defaultdict(list)
    for record in records:
        if record['category'] not in FIELDS:
            continue
        card_id = identity({'seed': SEED, 'record_id': record['record_id']})
        card = {'card_id': card_id, 'category': record['category'],
                'definition': definitions[record['category']], 'excerpts': record['excerpts']}
        cards.append(card)
        key.append({'card_id': card_id, **record})
        strata[(record['category'], record['filing_date'][:4])].append(card)
    sample = sorted([card for rows in strata.values() for card in sorted(rows, key=lambda c: c['card_id'])[:5]], key=lambda c: c['card_id'])
    return sorted(cards, key=lambda c: c['card_id']), key, sample


def template(card):
    return {'card_id': card['card_id'], 'category': card['category'],
            'review_status': 'missing_text' if not card['excerpts'] else 'unreviewed',
            'reviewer': '', 'reviewed_at': '', 'rationale': '',
            'fields': {name: {'value': 'unknown', 'evidence': []} for name in FIELDS[card['category']]}}


def validate_annotations(cards, annotations):
    """Validate interpretations without removing any card or primary label."""
    catalog = {card['card_id']: card for card in cards}
    checked = {}
    for annotation in annotations:
        if set(annotation) != {'card_id', 'category', 'review_status', 'reviewer', 'reviewed_at', 'rationale', 'fields'}:
            raise ValueError('Unexpected review fields; market outcomes are forbidden')
        card_id = annotation['card_id']
        if card_id not in catalog or card_id in checked:
            raise ValueError('Unknown or duplicate annotation ID')
        card = catalog[card_id]
        if annotation['category'] != card['category']:
            raise ValueError('Annotation category differs')
        status = annotation['review_status']
        if status not in ['unreviewed', 'reviewed', 'ambiguous', 'missing_text']:
            raise ValueError('Illegal review status')
        if status == 'missing_text' and card['excerpts']:
            raise ValueError('False missing-text annotation')
        if set(annotation['fields']) != set(FIELDS[card['category']]):
            raise ValueError('Unexpected annotation fields')
        if status in ['reviewed', 'ambiguous']:
            if not all(annotation.get(k, '').strip() for k in ['reviewer', 'reviewed_at', 'rationale']):
                raise ValueError('Incomplete review provenance')
            stamp = datetime.fromisoformat(annotation['reviewed_at'].replace('Z', '+00:00'))
            if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
                raise ValueError('Review timestamp must be UTC')
        for name, choices in FIELDS[card['category']].items():
            field = annotation['fields'][name]
            if set(field) != {'value', 'evidence'}:
                raise ValueError('Unexpected field metadata')
            value, evidence = field['value'], field['evidence']
            if value not in choices or not isinstance(evidence, list):
                raise ValueError('Illegal secondary value or evidence')
            if value != 'unknown' and (status not in ['reviewed', 'ambiguous'] or not evidence):
                raise ValueError('Unreviewed or unevidenced assertion')
            if any(not isinstance(span, str) or not span.strip() or not any(span in excerpt for excerpt in card['excerpts']) for span in evidence):
                raise ValueError('Evidence absent from source excerpt')
        checked[card_id] = annotation
    # Return the full source card set, including every missing/unknown case.
    return [checked.get(card['card_id'], template(card)) for card in cards]


def prepare(stage, source, master, remote):
    stage, source, master = Path(stage).resolve(), Path(source).resolve(), Path(master).resolve()
    if not stage.is_relative_to(ROOT / 'data/cache'):
        raise ValueError('Use a private cache stage')
    stage.mkdir(parents=True, exist_ok=False)
    source_manifest = read_json(source / 'source.json')
    if not source_manifest['complete'] or len(source_manifest['settings']['categories']) != 119:
        raise ValueError('Complete pinned H21 source required')
    inputs = stage / 'inputs'; inputs.mkdir()
    paths = [source / 'source.json', source / source_manifest['taxonomy_file']]
    for collection in source_manifest['disclosure_collections']:
        obj = source_manifest['objects'][collection['object_id']]
        if not obj['complete'] or obj['path'] != '/stocks/filings/8-K/vX/disclosures':
            raise ValueError('Incomplete or unexpected disclosure source')
        path = safe_child(source, obj['file'])
        if digest(path) != obj['sha256']:
            raise ValueError('Disclosure bytes differ')
        paths.append(path)
    for path in paths:
        target = inputs / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    # Display/transport projection of already returned counts; no new statistics.
    with master.open(encoding='utf-8', newline='') as handle:
        rows = [{key: row[key] for key in ['category', *COUNT_FIELDS]} for row in csv.DictReader(handle)]
    table(inputs / 'reference-counts.csv', rows, ['category', *COUNT_FIELDS])
    code_paths = ['discovery/atlas_label_audit.py', 'discovery/io.py',
                  str(FOLDER / 'label_audit.py'), str(FOLDER / 'Label Audit Protocol.md'),
                  'tests/test_atlas_label_audit.py']
    m = {'schema': 1, 'study': 'H21', 'scope': 'standard-label-audit',
         'plan_commit': PLAN_COMMIT, 'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'created_at': now(), 'source_sha256': digest(source / 'source.json'),
         'source_id': source_manifest['source_id'], 'reference_master_sha256': digest(master),
         'code': {Path(p).as_posix(): digest(ROOT / p) for p in code_paths},
         'inputs': {p.relative_to(stage).as_posix(): digest(p) for p in inputs.rglob('*') if p.is_file()},
         'seed': SEED, 'review_per_category_year': 5, 'no_trading': True}
    m['manifest_id'] = identity(m); write_json(stage / 'manifest.json', m)
    local = stage.relative_to(ROOT).as_posix()
    script = f'''#!/bin/bash
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --job-name=h21-label-audit
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output={remote}/audit-%j.log
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd {remote}
/blue/<allocation>/<username>/quanthacks/discovery/atlas-v3/.venv/bin/python -B -m discovery.atlas_label_audit run --stage {local}
'''
    (stage / 'run.sh').write_text(script, encoding='utf-8', newline='\n')
    package = stage / 'input.tar.gz'
    members = {name: digest(ROOT / name) for name in m['code']}
    members.update({f'{local}/{name}': value for name, value in m['inputs'].items()})
    members.update({f'{local}/manifest.json': digest(stage / 'manifest.json'), f'{local}/run.sh': digest(stage / 'run.sh')})
    with tarfile.open(package, 'w:gz') as archive:
        for name in members: archive.add(ROOT / name, arcname=name)
    write_json(stage / 'transfer.json', {'sha256': digest(package), 'members': members, 'manifest_id': m['manifest_id']})
    verifier = f'''import hashlib,json,tarfile,sys
from pathlib import Path
p=Path(sys.argv[1]);target=Path(sys.argv[2]).resolve()
expected={digest(package)!r}
if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise ValueError("Archive changed")
members={members!r}
target.mkdir(parents=True,exist_ok=False)
with tarfile.open(p) as archive:
 if set(x.name for x in archive.getmembers())!=set(members):raise ValueError("Unexpected members")
 for x in archive.getmembers():
  dest=(target/x.name).resolve()
  if not x.isfile() or not dest.is_relative_to(target):raise ValueError("Unsafe member")
  raw=archive.extractfile(x).read()
  if hashlib.sha256(raw).hexdigest()!=members[x.name]:raise ValueError("Member changed")
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
print(json.dumps({{"verified_members":len(members),"archive_sha256":expected}}))
'''
    (stage / 'verify_install.py').write_text(verifier, encoding='utf-8', newline='\n')
    print(json.dumps({'manifest_id': m['manifest_id'], 'archive_sha256': digest(package), 'verifier_sha256': digest(stage / 'verify_install.py'), 'members': len(members)}))


def run(stage, annotation_file=None):
    if not os.getenv('SLURM_JOB_ID'):
        raise RuntimeError('Real data aggregation requires a HiPerGator allocation')
    stage = Path(stage).resolve(); m = read_json(stage / 'manifest.json')
    if identity({k: v for k, v in m.items() if k != 'manifest_id'}) != m['manifest_id']:
        raise ValueError('Manifest changed')
    for name, value in m['code'].items():
        if digest(safe_child(ROOT, name)) != value: raise ValueError('Code changed: ' + name)
    for name, value in m['inputs'].items():
        if digest(safe_child(stage, name)) != value: raise ValueError('Input changed: ' + name)
    source = read_json(stage / 'inputs/source.json')
    if identity({k: v for k, v in source.items() if k != 'source_id'}) != m['source_id']:
        raise ValueError('Source identity differs')
    taxonomy = read_json(stage / 'inputs' / source['taxonomy_file'])
    if len(taxonomy) != 119 or digest(stage / 'inputs' / source['taxonomy_file']) != source['taxonomy_sha256']:
        raise ValueError('Pinned taxonomy differs')
    if set(source['settings']['categories']) != {d['tertiary_category'] for d in taxonomy}:
        raise ValueError('Taxonomy setting differs')
    collections = [(c['object_id'], c['cik'], read_json(stage / 'inputs' / source['objects'][c['object_id']]['file'])) for c in source['disclosure_collections']]
    records = primary_records(taxonomy, collections); counts = coverage(taxonomy, records)
    with (stage / 'inputs/reference-counts.csv').open(encoding='utf-8') as handle:
        reference = {r['category']: r for r in csv.DictReader(handle)}
    if set(reference) != {r['category'] for r in counts}:
        raise ValueError('Reference categories differ')
    for row in counts:
        if any(row[field] != int(reference[row['category']][field]) for field in COUNT_FIELDS):
            raise ValueError('Source count reconciliation failed: ' + row['category'])
        row['reconciled'] = True
    cards, key, sample = review_cards(taxonomy, records)
    annotations = validate_annotations(cards, read_json(annotation_file)) if annotation_file else [template(c) for c in cards]
    destination = stage / ('reviewed' if annotation_file else 'outputs')
    destination.mkdir(exist_ok=False)
    table(destination / 'coverage.csv', counts, list(counts[0]))
    for name, value in [('primary-records.json', records), ('blind-cards.json', cards),
                        ('lookup-key.json', key), ('review-batch.json', sample),
                        ('annotations.json', annotations), ('review-template.json', [template(c) for c in sample])]:
        write_json(destination / name, value)
    lookup = {item['record_id']: item['card_id'] for item in key}
    annotation_lookup = {a['card_id']: a for a in annotations}
    augmented = [{**r, 'secondary_annotation': annotation_lookup.get(lookup.get(r['record_id']))} for r in records]
    if len(augmented) != len(records): raise ValueError('Primary rows lost')
    write_json(destination / 'annotated-primary.json', augmented)
    summary = {'categories': len(counts), 'primary_filing_categories': len(records),
               'distinct_filings': len({(r['cik'], r['accession']) for r in records}),
               'cards': len(cards), 'review_batch': len(sample), 'reconciled': True,
               'review_status_counts': {status: sum(a['review_status'] == status for a in annotations) for status in ['unreviewed', 'reviewed', 'ambiguous', 'missing_text']},
               'primary_labels_filtered_by_text': 0, 'independent_review': 'pending',
               'statistical_or_alpha_claim': False}
    write_json(destination / 'summary.json', summary)
    files = {p.relative_to(destination).as_posix(): digest(p) for p in destination.iterdir()}
    receipt = {'manifest_id': m['manifest_id'], 'slurm_job_id': os.environ['SLURM_JOB_ID'],
               'finished_at': now(), 'state': 'completed', 'files': files,
               'annotations_sha256': digest(annotation_file) if annotation_file else None}
    write_json(destination / 'receipt.json', receipt)
    files['receipt.json'] = digest(destination / 'receipt.json')
    archive = stage / ('reviewed.zip' if annotation_file else 'audit.zip')
    if archive.exists(): raise ValueError('Preserve earlier return')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for name in files: zipped.write(destination / name, name)
        zipped.writestr('RETURN.json', json.dumps({'manifest_id': m['manifest_id'], 'files': files}))
    print(json.dumps({'archive': str(archive), 'sha256': digest(archive), 'members': len(files), 'summary': summary}))


def import_result(stage, archive, expected):
    stage, archive = Path(stage).resolve(), Path(archive).resolve()
    if digest(archive) != expected: raise ValueError('Whole archive differs')
    destination = stage / ('returned-review' if archive.name.startswith('reviewed') else 'returned')
    if destination.exists(): raise ValueError('Preserve earlier import')
    with zipfile.ZipFile(archive) as zipped:
        receipt = json.loads(zipped.read('RETURN.json'))
        if receipt['manifest_id'] != read_json(stage / 'manifest.json')['manifest_id']:
            raise ValueError('Wrong stage return')
        names = zipped.namelist()
        if len(names) != len(set(names)) or set(names) != set(receipt['files']) | {'RETURN.json'}:
            raise ValueError('Unexpected archive members')
        for name, value in receipt['files'].items():
            safe_child(destination, name)
            if hashlib.sha256(zipped.read(name)).hexdigest() != value:
                raise ValueError('Return member changed')
        destination.mkdir()
        for name in receipt['files']:
            target = safe_child(destination, name); target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zipped.read(name))
        write_json(destination / 'import-receipt.json', {'sha256': expected, 'verified_members': len(receipt['files']), 'verified_at': now()})
    print(json.dumps({'verified_members': len(receipt['files']), 'destination': str(destination)}))


def main():
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--stage', required=True); p.add_argument('--source', required=True); p.add_argument('--master', required=True); p.add_argument('--remote', required=True)
    p = sub.add_parser('run'); p.add_argument('--stage', required=True); p.add_argument('--annotations')
    p = sub.add_parser('import'); p.add_argument('--stage', required=True); p.add_argument('--archive', required=True); p.add_argument('--expected-sha', required=True)
    args = parser.parse_args()
    if args.command == 'prepare': prepare(args.stage, args.source, args.master, args.remote)
    elif args.command == 'run': run(args.stage, args.annotations)
    else: import_result(args.stage, args.archive, args.expected_sha)


if __name__ == '__main__': main()
