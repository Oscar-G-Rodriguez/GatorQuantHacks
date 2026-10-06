"""Copy verified pilot evidence and append four attempts; no market calculations."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_SHA='a923f46a7dfc33d6bda51c183c0b93de0a99596ef2b9b9a78eaaf5ebb76dda90'
FIELDS=['experiment_id','registered_at','hypothesis_id','registration_commit','code_commit',
        'sample_or_fold','parameters','signal_and_fill_timing','cost_model','data_identity',
        'outcome','evidence_path','notes']


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def child(base,relative):
    target=(Path(base)/relative).resolve()
    if not target.is_relative_to(Path(base).resolve()):raise ValueError('Evidence path escapes root')
    return target


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def package(run,registered_at):
    run=Path(run).resolve();imported=read(run/'import-receipt.json');manifest=read(run/'manifest.json')
    returned=read(run/'return.json');scheduler=read(run/'scheduler-observation.json')
    if imported['sha256']!=EXPECTED_SHA or imported['members']!=177:
        raise ValueError('This delivery requires the exact verified 177-member pilot return')
    if imported['manifest_id']!=manifest['manifest_id'] or returned['manifest_id']!=manifest['manifest_id']:
        raise ValueError('Return/manifest identity differs')
    for relative,expected in imported['files'].items():
        if digest(child(run,relative))!=expected:raise ValueError('Imported member changed: '+relative)
    if imported['files']!=returned['files']:raise ValueError('Returned member ledger differs')
    for job in scheduler['jobs']:
        if job['state']!='COMPLETED' or job['exit_code']!='0:0':raise ValueError('Scheduler has incomplete work')
    tasks=read(run/'tasks.json');cfg=read(ROOT/'config/financing-round2.json')
    if digest(ROOT/'config/financing-round2.json')!=manifest['files']['config/financing-round2.json']:
        raise ValueError('Current settings differ from executed settings')
    calibration=read(run/'results/calibration/summary.json');joint=read(run/'results/joint/summary.json')
    rows=[]
    for task in tasks:
        number=task['task'];record=read(run/'receipts'/f'task-{number}.json')
        if record['status']!='completed' or record['manifest_id']!=manifest['manifest_id'] or record['task']!=task:
            raise ValueError('Task receipt is incomplete or misidentified')
        for relative,expected in record['files'].items():
            if digest(child(run,relative))!=expected:raise ValueError('Task evidence changed')
        settings=next(v for v in cfg['variants'] if v['id']==task['variant'])
        study=next(s for s in cfg['studies'] if s['id']==task['study'])
        summary=read(run/'results'/task['study']/'summary.json')
        rows.append(dict(zip(FIELDS,[
            f"financing-pilot-{manifest['manifest_id'][:12]}-task-{number}",registered_at,task['study'],
            manifest['registration_commit'],manifest['code_commit'],'2022–2025 development; deterministic pilot',
            json.dumps({'task':number,'variant':settings,'shapes':cfg['shapes'],'primary_horizon':cfg['primary_horizon'],
                'diagnostic_horizons':cfg['horizons']+['expiry'],'primary_effects':summary['primary_effects']},sort_keys=True),
            'Assumed filing+1 calendar day aligned forward; study delay '+str(study['delay'])+
                '; variant delay '+str(settings['extra_delay'])+'; next session close; planned/actual exits retained',
            f"Stock6bp/side; option5% premium+$0.65/contract/side; all frictions x{settings['cost_multiplier']}; bounded quotes separately",
            record['source_id'],'INCONCLUSIVE: insufficient_support; calibration_fail; no_fresh_OOS',
            f"Hypotheses/{study['folder']}/results/financing-round2-pilot-v1/tasks/{number}",
            f"Array observation 44693324_{number}; child receipt job {record['job_id']}; completed {record['completed_at']}; "+
                'calibration false rejections 45/100(block63),72/100(block126),limit10; 0/199 timing placebos; full cohort pending; no established alpha; no alpha claim'
        ])))
    ledger=ROOT/'Hypotheses/EXPERIMENTS.csv';before=ledger.read_bytes()
    existing=list(csv.DictReader(io.StringIO(before.decode('utf-8'))))
    if list(existing[0])!=FIELDS:raise ValueError('Experiment ledger schema differs')
    known={r['experiment_id']:r for r in existing};new=[];corrections=[]
    for row in rows:
        if row['experiment_id'] in known:
            if known[row['experiment_id']]!=row:
                legacy=dict(row)
                legacy['notes']=legacy['notes'].replace('Array observation ','Array observation').replace('child receipt job ','child receipt job').replace('completed ','completed').replace('false rejections ','false rejections').replace('no established alpha; no alpha claim','no alpha')
                if known[row['experiment_id']]!=legacy:raise ValueError('Conflicting prior trial record')
                corrections.append(row)
        else:new.append(row)
    preserved=before
    if corrections:
        # The only authorized correction is wording in this helper's own four
        # appended one-line records; older experiment bytes stay untouched.
        if new or len(corrections)!=4 or [r['experiment_id'] for r in existing[-4:]]!=[r['experiment_id'] for r in rows]:
            raise ValueError('The four owned rows are not the final ledger records')
        lines=before.splitlines(keepends=True)
        if any(not line.startswith((row['experiment_id']+',').encode('utf-8')) for line,row in zip(lines[-4:],rows)):
            raise ValueError('Owned trial lines are not safely isolated')
        preserved=b''.join(lines[:-4])
        buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=FIELDS,lineterminator='\r\n');writer.writerows(rows)
        if ledger.read_bytes()!=before:raise ValueError('Experiment ledger changed during correction')
        ledger.write_bytes(preserved+buffer.getvalue().encode('utf-8'));before=ledger.read_bytes()
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=FIELDS,lineterminator='\r\n')
    writer.writerows(new)
    if ledger.read_bytes()!=before:raise ValueError('Experiment ledger changed during preparation')
    if new:
        suffix=(b'' if before.endswith(b'\n') else b'\r\n')+buffer.getvalue().encode('utf-8')
        ledger.write_bytes(before+suffix)
    if not ledger.read_bytes().startswith(preserved):raise ValueError('Prior trial ledger bytes were modified')
    copied=[]
    for study in cfg['studies']:
        sid=study['id'];out=ROOT/'Hypotheses'/study['folder']/'results/financing-round2-pilot-v1'
        selected={p.relative_to(run).as_posix():p.relative_to(run/'results'/sid).as_posix()
                  for p in (run/'results'/sid).rglob('*') if p.is_file()}
        for task in tasks:
            if task['study']!=sid:continue
            n=task['task']
            for p in (run/'results/tasks'/str(n)).glob('*'):
                if p.is_file():selected[p.relative_to(run).as_posix()]=f'tasks/{n}/'+p.name
            selected[f'receipts/task-{n}.json']=f'receipts/task-{n}.json'
        for name in ['analysis','calibration']:selected[f'receipts/{name}.json']=f'receipts/{name}.json'
        for name in ['manifest.json','return.json','import-receipt.json','scheduler-observation.json','tasks.json']:
            selected[name]='provenance/'+name
        for name in ['summary.json','calibration_gate.json','primary_family.csv','task_status.csv',
                     'timing_placebo_trials.csv','timing_placebo_comparison.csv','dependencies.json']:
            selected['results/joint/'+name]='joint/'+name
        selected['results/calibration/summary.json']='calibration/summary.json'
        for name in ['coverage.csv','exclusions.csv','summary.json']:selected['prepared/'+name]='prepared/'+name
        total=sum(child(run,p).stat().st_size for p in selected)
        if total>20*1024*1024:raise ValueError('Derived study evidence exceeds the bounded delivery size')
        members={}
        for original,target in selected.items():
            source=child(run,original);dest=child(out,target);expected=digest(source)
            if dest.exists() and digest(dest)!=expected:raise ValueError('Canonical evidence copy conflicts')
            dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():shutil.copy2(source,dest)
            if digest(dest)!=expected:raise ValueError('Evidence copy differs')
            members[target]={'source_relative':original,'sha256':expected}
        out.mkdir(parents=True,exist_ok=True)
        with (out/'Trial Ledger.csv').open('w',encoding='utf-8',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=FIELDS);writer.writeheader();writer.writerows(r for r in rows if r['hypothesis_id']==sid)
        write(out/'evidence_manifest.json',{'study':sid,'scope':'pilot','registration_commit':manifest['registration_commit'],
            'code_commit':manifest['code_commit'],'manifest_id':manifest['manifest_id'],'archive_sha256':EXPECTED_SHA,
            'archive_members':177,'import_verified_at':imported['verified_at'],'copied_members':members,
            'copied_bytes':total,'verdict':'INCONCLUSIVE; UNSUPPORTED_FOR_CONFIRMATORY_CLAIM',
            'policy':'Derived results and receipts only; no raw provider objects, excerpts or credentials copied'})
        (out/'Reproduce.md').write_text(
            '# Verified pilot evidence\n\nThese are unchanged copies of scheduled HiPerGator outputs. '+
            'The source paths and SHA-256 values in evidence_manifest.json identify every copied member. '+
            'This directory contains no raw vendor object or credentials.\n\n'+
            'The result is INCONCLUSIVE. Read summary.md and validation_checks.json before interpreting performance.csv. '+
            'The synthetic calibration failed, paired samples are sparse, and fresh confirmation is unavailable. '+
            'This delivered pilot covers four scoped tasks; it does not finish the 33-task full study.\n\n'+
            'Recreate this evidence copy on the PC from the retained verified run:\n\n'+
            '```powershell\n.venv/Scripts/python.exe -B scripts/package_financing_pilot_evidence.py '+
            '--run data/cache/disclosure-atlas/financing-round2-pilot-acquisition-v1\n```\n\n'+
            'Numerical replay requires the frozen source package and a scheduled HiPerGator allocation. '+
            'Run `python -m discovery.financing_pipeline exec --stage run --run <frozen-run> --task N`; '+
            'then calibration, analyze and export stages. The retained source package is private. '+
            'The existing receipts make completed tasks idempotent; a new scientific attempt needs a new frozen run.\n',encoding='utf-8')
        copied.append({'study':sid,'path':out.relative_to(ROOT).as_posix(),'members':len(members),'bytes':total})
    print(json.dumps({'verified_return_members':177,'appended_trials':len(new),'corrected_owned_trial_notes':len(corrections),'studies':copied,
                      'calibration':calibration['status'],'completed_scoped_tasks':joint['completed_tasks']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',default='data/cache/disclosure-atlas/financing-round2-pilot-acquisition-v1')
    parser.add_argument('--registered-at',default='2026-10-04T09:44:08-04:00')
    args=parser.parse_args();package(args.run,args.registered_at)
