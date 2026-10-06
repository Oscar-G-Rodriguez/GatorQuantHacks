"""Artificial fixtures only; financial estimates stay on HiPerGator."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from discovery.atlas_uncertainty_stage import year_weights, adjusted_results


class StratifiedUncertaintyTests(unittest.TestCase):
    def test_generated_cluster_scripts_use_linux_line_endings(self):
        from discovery import atlas_uncertainty_stage as stage_module
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);parent=root/'parent';parent.mkdir();(parent/'manifest.json').write_text('{}')
            for name in ['discovery/atlas_uncertainty_stage.py','discovery/atlas_return.py',stage_module.AMENDMENT]:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic code or plan')
            pm={'schema':1,'study':'H21','plan_commit':'synthetic','source':'source','source_id':'synthetic','source_sha256':'synthetic',
                'sealed_excluded':True,'manifest_id':'parent','settings':{'resamples':9999,'resample_batch':100,'block_lengths':[63,126]}}
            with patch.object(stage_module,'ROOT',root),patch.object(stage_module,'manifest',return_value=pm),patch.object(stage_module.subprocess,'check_output',return_value='synthetic'):
                stage_module.prepare(parent,root/'stage','/blue/synthetic')
            for file in (root/'stage/hpg').glob('*'):
                self.assertNotIn(b'\r',file.read_bytes());self.assertTrue(file.read_bytes().startswith(b'#!/bin/bash\n'))

    def test_every_year_and_common_calendar(self):
        dates = np.arange(1003); years = np.repeat([2022, 2023, 2024, 2025], [252, 250, 252, 249])
        for block in [63, 126]:
            for seed in range(1000):
                w = year_weights(np.array(['i']*1003), dates, years, block, np.random.default_rng(17+seed))
                for year, n in zip([2022, 2023, 2024, 2025], [252, 250, 252, 249]):
                    self.assertEqual(w[years == year].sum(), n)
        w = year_weights(np.array(['i']*1003+['j']*1003), np.tile(dates, 2), np.tile(years, 2), 63, np.random.default_rng(5))
        if w[:1003].sum() and w[1003:].sum():
            np.testing.assert_allclose(w[:1003]/w[:1003].sum(), w[1003:]/w[1003:].sum())

    def test_determinism_empty_and_year_conflict(self):
        args = (['i', 'i', 'i', 'i'], [0, 1, 2, 3], [2023, 2023, 2024, 2024], 2)
        np.testing.assert_array_equal(year_weights(*args, np.random.default_rng(2)), year_weights(*args, np.random.default_rng(2)))
        self.assertEqual(len(year_weights([], [], [], 1, np.random.default_rng(2))), 0)
        with self.assertRaises(ValueError): year_weights(['i', 'i'], [0, 0], [2023, 2024], 1, np.random.default_rng(2))

    def test_sparse_missing_stays_unsupported_and_nulls_adjusted(self):
        rng = np.random.default_rng(11); draws = rng.normal(size=(999, 4)); point = np.zeros(4)
        draws[0, 3] = np.nan
        valid, p, finite = adjusted_results(point, draws)
        self.assertEqual(valid.tolist(), [True, True, True, False]); self.assertEqual(finite[3], 998)
        self.assertTrue(np.isnan(p[3])); np.testing.assert_array_equal(p[:3], np.ones(3))


if __name__ == '__main__': unittest.main()
