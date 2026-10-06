"""Small verified inference return; large draw archives remain a separate stage."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from .atlas import manifest,scheduled,done
from .io import ROOT,digest,now,read_json,safe_child


def export_summary(run,output,scheduler=None):
    scheduled();run=Path(run).resolve();m=manifest(run);output=Path(output)
    if output.exists():raise ValueError('Preserve earlier return packages')
    if not done(run,'inference'):raise ValueError('Inference must be complete and verified')
    receipt=read_json(run/'receipts/inference.json')
    files={name:safe_child(run,name) for name in receipt['files']}
    files.update({'manifest.json':run/'manifest.json','receipts/inference.json':run/'receipts/inference.json'})
    if scheduler:
        source=Path(scheduler).resolve()
        if not source.is_relative_to(ROOT):raise ValueError('Scheduler evidence must be in this private checkout')
        files['scheduler/'+source.name]=source
    hashes={}
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,path in sorted(files.items()):
            raw=path.read_bytes();h=hashlib.sha256(raw).hexdigest()
            if name in receipt['files'] and h!=receipt['files'][name]:raise ValueError('Completed output changed during export')
            hashes[name]=h;archive.writestr(name,raw)
        archive.writestr('RETURN-RECEIPT.json',json.dumps({'manifest_id':m['manifest_id'],'files':hashes,'exported_at':now(),
            'scope':'Complete verified inference outputs only; large resampling draws remain in the separate whole-stage return',
            'transfer_control_sha256':digest(Path(__file__))}))
    return {'sha256':digest(output),'members':len(hashes)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--output',required=True);p.add_argument('--scheduler');a=p.parse_args()
    print(json.dumps(export_summary(a.run,a.output,a.scheduler)))
