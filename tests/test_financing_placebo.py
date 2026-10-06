"""Synthetic sources only: append integrity, missing-data gates and task clocks."""
import copy
import json
import os
from pathlib import Path
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

from discovery import financing_placebo as p


class FinancingPlaceboTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name); self.run = self.root / 'data/test-run'; self.run.mkdir(parents=True)
        self.config = self.root / 'config.json'; self.config.write_bytes(p.CONFIG.read_bytes())
        self.cfg = json.loads(self.config.read_text())
        self.addCleanup(patch.stopall); patch.object(p, 'ROOT', self.root).start(); patch.object(p, 'CONFIG', self.config).start()
        patch.object(p, 'remote_base', return_value='/blue/test-allocation/test-user/quanthacks/discovery').start()
        prepared = self.run / 'prepared'; prepared.mkdir()
        self.calendar = {'dates': ['2024-01-02', '2024-07-01'], 'clock': {}}
        maps = [{'replica': i, 'shifts': [{'issuer': '001', 'year': 2024, 'offset': 5}]} for i in range(199)]
        p.write_json(prepared / 'calendar.json', self.calendar); p.write_json(prepared / 'placebo-map.json', maps)
        p.write_json(prepared / 'actions.json', {'TEST': {'dividends': [], 'splits': []}})
        files = {self.config.relative_to(self.root).as_posix(): p.digest(self.config)}
        files.update({x.relative_to(self.root).as_posix(): p.digest(x) for x in prepared.glob('*')})
        manifest = {'registration_commit': p.REGISTRATION, 'files': files, 'remote': '/synthetic/remote', 'scope': 'full'}
        manifest['manifest_id'] = p.identity(manifest); p.write_json(self.run / 'manifest.json', manifest)
        self.base_id = manifest['manifest_id']
        self.child = self.run / 'placebos/0'; shifted = self.child / 'prepared'; shifted.mkdir(parents=True)
        self.anchors = []
        for shape in ['covered_call', 'protective_put']:
            for role, day in [('event', '2024-07-01'), ('ordinary', '2024-01-02')]:
                self.anchors.append({'anchor_id': shape + '-' + role, 'shape': shape, 'role': role, 'study': 'H23',
                    'variant': 'primary', 'issuer': '001', 'ticker': 'TEST', 'date': day, 'pair_id': 'shifted-pair',
                    'features': {'momentum': .01}, 'event_decision': '2024-07-01'})
        p.write_json(shifted / 'anchors.json', self.anchors); p.write_json(shifted / 'calendar.json', self.calendar)
        p.write_json(shifted / 'map.json', maps[0]); p.csv_write(shifted / 'exclusions.csv', [])
        self.write_receipt('placebo-prepare-0', list(shifted.glob('*')))

    def write_receipt(self, stage, files, **extra):
        record = {'manifest_id': self.base_id, 'status': 'completed',
                  'files': {x.relative_to(self.run).as_posix(): p.digest(x) for x in files}, **extra}
        p.write_json(self.run / 'receipts' / (stage + '.json'), record)

    def source(self, complete=True, missing=False):
        folder = self.child / 'acquisition'; objects = folder / 'objects'; objects.mkdir(parents=True, exist_ok=True)
        obj = objects / ('a' * 64 + '.json'); p.write_json(obj, [{'t': 1, 'c': 100, 'v': 1000}])
        rows = [{**a, 'status': 'bars_downloaded', 'stock_object': 'a' * 64} for a in self.anchors]
        if missing:
            rows = rows[:-1]
        result = {'registration_commit': p.REGISTRATION, 'settings_sha256': p.digest(self.config),
                  'anchors_sha256': p.digest(self.child / 'prepared/anchors.json'), 'complete': complete,
                  'records': rows, 'objects': {'a' * 64: {'sha256': p.digest(obj)}}, 'failures': [],
                  'required_anchors': len(self.anchors)}
        result['source_id'] = p.identity(result); p.write_json(folder / 'source.json', result)
        return result

    def test_absent_source_is_registered_pending_without_completion_receipt(self):
        extension = p.register_acquisition(self.run, 0)
        assert extension['status'] == 'pending' and extension['ready'] is False
        assert not (self.run / 'receipts/placebo-acquire-0.json').exists()
        with self.assertRaisesRegex(RuntimeError, 'pending'):
            p.verify_extension(self.run, 0)

    def test_partial_phases_preserve_versions_and_cannot_trade(self):
        first = p.register_acquisition(self.run, 0)
        self.source(False, True)
        second = p.register_acquisition(self.run, 0)
        assert first['extension_id'] != second['extension_id']
        assert len(list((self.child / 'extensions').glob('*.json'))) == 2
        with patch.dict(os.environ, {'SLURM_JOB_ID': 'synthetic'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'pending'):
                p.run_study(self.run, 0, 'H23')
        assert not (self.run / 'receipts/placebo-task-0-H23.json').exists()

    def test_complete_source_with_missing_anchor_refuses_registration(self):
        self.source(True, True)
        with self.assertRaisesRegex(ValueError, 'missing/unresolved'):
            p.register_acquisition(self.run, 0)

    def test_record_cannot_relabel_an_unshifted_date(self):
        source = self.source(); source['records'][0]['date'] = '2023-12-01'
        source['source_id'] = p.identity({k: v for k, v in source.items() if k != 'source_id'})
        p.write_json(self.child / 'acquisition/source.json', source)
        with self.assertRaisesRegex(ValueError, 'changed or invented'):
            p.register_acquisition(self.run, 0)

    def test_frozen_map_change_refuses_registration(self):
        path = self.child / 'prepared/map.json'; changed = p.read_json(path); changed['shifts'][0]['offset'] = 63
        p.write_json(path, changed)
        self.write_receipt('placebo-prepare-0', list((self.child / 'prepared').glob('*')))
        with self.assertRaisesRegex(ValueError, 'frozen map'):
            p.register_acquisition(self.run, 0)

    def test_ready_source_is_hash_verified_and_not_mutable(self):
        self.source(); extension = p.register_acquisition(self.run, 0)
        assert extension['ready'] and p.verify_extension(self.run, 0)['source_id'] == extension['source_id']
        source_path = self.child / 'acquisition/source.json'; source_path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'member changed'):
            p.register_acquisition(self.run, 0)

    def test_partial_extension_cannot_be_packaged(self):
        p.register_acquisition(self.run, 0)
        with self.assertRaises(RuntimeError):
            p.bundle(self.run, 0, self.root / 'bundle.tar.gz')

    def test_ready_append_bundle_has_exact_declared_members(self):
        self.source(); extension = p.register_acquisition(self.run, 0)
        output = self.root / 'extension.tar.gz'; result = p.bundle(self.run, 0, output)
        assert result['sha256'] == p.digest(output)
        assert result['extension_id'] == extension['extension_id']
        with tarfile.open(output) as tar:
            names = tar.getnames()
            assert len(names) == result['members'] and len(names) == len(set(names))
            assert all(not name.startswith('/') and '..' not in Path(name).parts for name in names)
            assert 'data/test-run/placebos/0/acquisition/source.json' in names

    def test_jobs_select_only_ready_exact_source_tasks(self):
        pending = p.jobs(self.run, [0])
        assert pending['planned_study_tasks'] == 597 and pending['ready_study_tasks'] == []
        assert not pending['run_script_generated']
        self.source(); p.register_acquisition(self.run, 0)
        ready = p.jobs(self.run, [0])
        assert ready['ready_study_tasks'] == [0, 1, 2]
        script = (self.run / 'hpg/placebo-run.sbatch').read_text()
        assert '--array=0,1,2%16' in script and 'SLURM_ARRAY_TASK_ID / 3' in script
        assert 'OMP_NUM_THREADS=1' in script

    def test_scheduled_refusal_precedes_any_trading_engine_import(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'scheduled'):
                p.run_study(self.run, 0, 'H23')

    def test_invalid_replica_and_traversal_refuse(self):
        for bad in [-1, 199, True]:
            with self.assertRaises(ValueError):
                p.replica_folder(self.run, bad)
        with self.assertRaises(ValueError):
            p.child_path(self.run, '../outside')

    def test_engine_receives_shifted_records_and_writes_expected_root_receipt(self):
        source = self.source(); p.register_acquisition(self.run, 0)
        observed = []
        class SyntheticData:
            def __init__(self, folder):
                self.source = p.read_json(folder / 'acquisition/source.json'); self.records = self.source['records']
                self.dates = ['2024-01-02', '2024-07-01']
        def unit(record, data, horizon, stock_only):
            observed.append((record['date'], data.source['source_id']))
            return {**record, 'horizon': horizon, 'stock_only': stock_only, 'net_return': .02,
                    'status': 'completed', 'evaluation_aligned': True}
        fake = types.SimpleNamespace(Data=SyntheticData, owned_strategy=lambda d, s: object,
            unit_trade=unit, quoted_diagnostics=lambda *a: {}, Ledger=lambda *a: None,
            replay=lambda *a: {'accepted_entries': [], 'daily': []}, performance=lambda *a: {})
        with patch.dict(os.environ, {'SLURM_JOB_ID': 'synthetic'}, clear=True), \
                patch.dict('sys.modules', {'discovery.financing_strategy': fake}):
            result = p.run_study(self.run, 0, 'H23')
            again = p.run_study(self.run, 0, 'H23')
        assert result == again and len(observed) == len(self.anchors) * 18
        assert {s for _, s in observed} == {source['source_id']}
        assert {d for d, _ in observed} == {'2024-01-02', '2024-07-01'}
        assert (self.child / 'results/H23/trades.csv').exists()
        receipt = p.check_receipt(self.run, 'placebo-task-0-H23', self.base_id)
        assert receipt['job_id'] == 'synthetic' and receipt['replica'] == 0


if __name__ == '__main__':
    unittest.main()
