"""Export completed, verified stages while other scientific allocations continue."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from .atlas import manifest,scheduled
from .io import ROOT,digest,now,read_json,safe_child


def export_completed(run,output):
    scheduled();run=Path(run).resolve();m=manifest(run);output=Path(output)
    if output.exists():raise ValueError('Preserve earlier return packages')
    members={'manifest.json':(run/'manifest.json',digest(run/'manifest.json'))};stages=[]
    def add(name,h):
        if any(p in ['.env','.git','.venv'] for p in Path(name).parts):raise ValueError('Forbidden return member')
        p=safe_child(run,name)
        if digest(p)!=h:raise ValueError('Completed stage output changed: '+name)
        if name in members and members[name][1]!=h:raise ValueError('Conflicting completed stage identities')
        members[name]=(p,h)
        if name.endswith('/complete.json'):
            checkpoint=read_json(p)
            for child,value in checkpoint['files'].items():add((Path(name).parent/child).as_posix(),value)
    for p in sorted((run/'receipts').glob('*.json')):
        r=read_json(p)
        if r['manifest_id']!=m['manifest_id']:raise ValueError('Stage belongs to another manifest')
        if r['state']!='completed':continue
        for name,h in r['files'].items():add(name,h)
        members[p.relative_to(run).as_posix()]=(p,digest(p));stages.append(r['stage'])
    for p in run.glob('attempts/*.json'):members[p.relative_to(run).as_posix()]=(p,digest(p))
    for pattern in ['h21-*.out','scheduler-*.txt','submission-*.txt']:
        for p in ROOT.glob(pattern):members['scheduler/'+p.name]=(p,digest(p))
    hashes={}
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,(p,h) in sorted(members.items()):
            raw=p.read_bytes();actual=hashlib.sha256(raw).hexdigest()
            # Scheduler files can grow; their current snapshot receives its own hash.
            if actual!=h and not name.startswith('scheduler/'):raise ValueError('Stage changed during export')
            hashes[name]=actual;archive.writestr(name,raw)
        archive.writestr('RETURN-RECEIPT.json',json.dumps({'manifest_id':m['manifest_id'],'files':hashes,
            'completed_stages':stages,'exported_at':now(),'scope':'Completed receipts and their recursively verified outputs only',
            'transfer_control_sha256':digest(Path(__file__))}))
    return {'sha256':digest(output),'members':len(hashes),'completed_stages':len(stages)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(export_completed(a.run,a.output)))
