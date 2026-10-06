"""Verified compressed research evidence for resource-bounded PC returns."""
import json
import zipfile
import csv
import io
from pathlib import Path
from .io import digest,read_json,safe_child


class Evidence:
    def __init__(self,run):
        self.run=Path(run).resolve();self.index=read_json(self.run/'compressed-evidence.json') if (self.run/'compressed-evidence.json').exists() else {}
        self.checked=set()

    def exists(self,name):return (self.run/name).exists() or name in self.index

    def tables(self):
        return sorted({p.relative_to(self.run).as_posix() for p in self.run.glob('tasks/*/*.csv')}
                      | {n for n in self.index if n.startswith('tasks/') and n.endswith('.csv')})

    def rows(self,name):
        p=safe_child(self.run,name)
        if p.exists():
            with p.open(newline='',encoding='utf-8') as stream:yield from csv.DictReader(stream)
        else:
            archive,_=self._archive(name)
            with zipfile.ZipFile(archive) as stream,stream.open(name) as member,io.TextIOWrapper(member,encoding='utf-8',newline='') as text:
                yield from csv.DictReader(text)

    def _archive(self,name):
        entry=self.index[name];archive=safe_child(self.run,entry['archive'])
        if entry['archive'] not in self.checked:
            if digest(archive)!=entry['archive_sha256']:raise ValueError('Compressed evidence archive changed')
            self.checked.add(entry['archive'])
        return archive,entry

    def hash(self,name):
        p=safe_child(self.run,name)
        if p.exists():return digest(p)
        _,entry=self._archive(name);return entry['member_sha256']

    def json(self,name):
        p=safe_child(self.run,name)
        if p.exists():return read_json(p)
        archive,_=self._archive(name)
        with zipfile.ZipFile(archive) as stream:return json.loads(stream.read(name))

    def completed(self,label,manifest_id):
        name='receipts/'+label+'.json'
        if not self.exists(name):return False
        r=self.json(name)
        if r['manifest_id']!=manifest_id:raise ValueError('Receipt belongs to another manifest')
        for name,h in r['files'].items():
            if self.hash(name)!=h:raise ValueError('Evidence output changed')
            if name.endswith('/complete.json'):
                for child,value in self.json(name)['files'].items():
                    if self.hash((Path(name).parent/child).as_posix())!=value:raise ValueError('Checkpoint changed')
        return r['state']=='completed'
