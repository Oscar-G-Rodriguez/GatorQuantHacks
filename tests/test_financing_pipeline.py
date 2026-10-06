"""Synthetic transfer and source-completeness tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from discovery.financing_pipeline import import_return,freeze,REGISTRATION
from discovery.io import digest,write_json,identity


class TransferIntegrity(unittest.TestCase):
    def manifest(self,run):
        m={"registration_commit":REGISTRATION,"code_commit":"synthetic-code","scope":"pilot","files":{}}
        m["manifest_id"]=identity(m);write_json(run/"manifest.json",m);return m

    def returned(self,m,files):
        return {"manifest_id":m["manifest_id"],"registration_commit":REGISTRATION,"code_commit":m["code_commit"],"scope":m["scope"],"files":files}

    def test_corrupt_archive_and_unexpected_member_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d)/"run";run.mkdir();m=self.manifest(run)
            archive=Path(d)/"returned.zip"
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("return.json",json.dumps(self.returned(m,{})));z.writestr("unexpected","x")
            with self.assertRaises(ValueError):import_return(archive,run,digest(archive))
            with self.assertRaises(ValueError):import_return(archive,run,"0"*64)

    def test_member_hash_and_path_escape_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d)/"run";run.mkdir();m=self.manifest(run)
            archive=Path(d)/"returned.zip"
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("../outside","x")
                z.writestr("return.json",json.dumps(self.returned(m,{"../outside":hashlib.sha256(b'x').hexdigest()})))
            with self.assertRaises(ValueError):import_return(archive,run,digest(archive))
            self.assertFalse((Path(d)/"outside").exists())


    def test_valid_import_and_changed_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d)/"run";run.mkdir();m=self.manifest(run);archive=Path(d)/"returned.zip"
            content=b"verified synthetic result";r=self.returned(m,{"results/value.txt":hashlib.sha256(content).hexdigest()})
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("return.json",json.dumps(r));z.writestr("results/value.txt",content)
            import_return(archive,run,digest(archive))
            self.assertEqual((run/"results/value.txt").read_bytes(),content)
            m["scope"]="full";write_json(run/"manifest.json",m)
            with self.assertRaisesRegex(ValueError,"manifest identity"):import_return(archive,run,digest(archive))

    def test_wrong_code_and_member_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d)/"run";run.mkdir();m=self.manifest(run);archive=Path(d)/"returned.zip"
            for wrong_code,wrong_bytes in [(True,False),(False,True)]:
                r=self.returned(m,{"result":hashlib.sha256(b"x").hexdigest()})
                if wrong_code:r["code_commit"]="other-code"
                with zipfile.ZipFile(archive,"w") as z:
                    z.writestr("return.json",json.dumps(r));z.writestr("result",b"y" if wrong_bytes else b"x")
                with self.assertRaises(ValueError):import_return(archive,run,digest(archive))
                self.assertFalse((run/"result").exists())


if __name__=="__main__":unittest.main()
