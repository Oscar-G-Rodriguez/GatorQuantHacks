"""Small correctness checks, not market-data discovery or a local suite run."""
from __future__ import annotations

import ast
import copy
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from discovery.data import build_panel, load_snapshot, snapshot, validate_config
from discovery.io import ROOT, STUDIES, identity, read_json, write_json
from discovery.methods import block_indices, correlation, correlation_moments, distance_correlation, folds, moments, pairs, residuals
from discovery.runner import aggregate, plan, read_manifest, valid_receipt
from discovery.jobs import import_results, write_jobs


def fixture():
    c = read_json(ROOT / "config/discovery-pilot.json")
    c.update(horizons=[1, 5], lags=[0, 1], block_sessions=5, resamples=40, resample_batch=20)
    dates = pd.bdate_range("2024-01-01", periods=120)
    rows = []
    for ticker in ["AAPL", "MSFT", "AMZN", "SPY"]:
        for i, d in enumerate(dates):
            rows.append({"date": d.strftime("%Y-%m-%d"), "ticker": ticker, "close": 100 + i + np.sin(i), "volume": 10000 + i})
    return c, pd.DataFrame(rows), dates


def event(dates, i, category, accession, filing=None):
    return {"ticker": "AAPL", "issuer": "issuer-a", "filing_date": (filing or dates[i]).strftime("%Y-%m-%d"), "available_date": (dates[i] + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), "category": category, "accession": accession}


class DiscoveryIntegrityTests(unittest.TestCase):
    def test_targets_use_later_prices_and_stop_at_boundary(self):
        c, bars, dates = fixture()
        p, _, _ = build_panel(bars, pd.DataFrame(), c)
        g = p[p.ticker == "AAPL"].set_index("date")
        i = 40
        current = 100 + i + np.sin(i)
        later = 100 + i + 5 + np.sin(i + 5)
        self.assertAlmostEqual(g.loc[str(dates[i].date()), "return_5"], later / current - 1)
        self.assertTrue(pd.isna(g.iloc[-1].return_1))
        self.assertEqual(g.loc[str(dates[i].date()), "target_end_5"], str(dates[i + 5].date()))

    def test_future_mutation_cannot_change_past_features(self):
        c, bars, dates = fixture()
        a, _, _ = build_panel(bars, pd.DataFrame(), c)
        bars.loc[pd.to_datetime(bars.date) > dates[70], "close"] *= 3
        b, _, _ = build_panel(bars, pd.DataFrame(), c)
        cols = ["past_return_5", "past_return_20", "past_vol_20", "market_past_return_5"]
        pd.testing.assert_frame_equal(a[a.date <= str(dates[70].date())][cols], b[b.date <= str(dates[70].date())][cols])

    def test_missing_bar_does_not_compress_future_horizon(self):
        c, bars, dates = fixture()
        bars = bars[~((bars.ticker == "AAPL") & (bars.date == str(dates[42].date())))]
        p, _, quality = build_panel(bars, pd.DataFrame(), c)
        row = p[(p.ticker == "AAPL") & (p.date == str(dates[40].date()))].iloc[0]
        self.assertTrue(pd.isna(row.return_5))
        self.assertEqual(quality["missing_issuer_bar_rows"], 1)

    def test_event_clock_and_distinct_filing_sequence(self):
        c, bars, dates = fixture()
        a, b = c["categories"]
        events = pd.DataFrame([event(dates, 35, a, "first"), event(dates, 40, b, "first"), event(dates, 45, b, "second")])
        p, _, _ = build_panel(bars, events, c)
        g = p[p.ticker == "AAPL"].set_index("date")
        self.assertEqual(g.loc[str(dates[35].date()), f"event__{a}"], 0)
        ia = dates.searchsorted(pd.Timestamp(events.iloc[0].available_date))
        self.assertEqual(g.loc[str(dates[ia].date()), f"event__{a}"], 1)
        ib = dates.searchsorted(pd.Timestamp(events.iloc[1].available_date))
        ic = dates.searchsorted(pd.Timestamp(events.iloc[2].available_date))
        self.assertEqual(g.loc[str(dates[ib].date()), "sequence_a_before_b"], 0)
        self.assertEqual(g.loc[str(dates[ic].date()), "sequence_a_before_b"], 1)

    def test_same_filing_date_cannot_form_sequence(self):
        c, bars, dates = fixture()
        a, b = c["categories"]
        rows = [event(dates, 35, a, "a"), event(dates, 36, b, "b", filing=dates[35])]
        p, _, _ = build_panel(bars, pd.DataFrame(rows), c)
        self.assertEqual(p.sequence_a_before_b.sum(), 0)

    def test_purge_uses_actual_target_end(self):
        c, bars, _ = fixture()
        p, _, _ = build_panel(bars, pd.DataFrame(), c)
        for _, train, valid, start, _ in folds(p.dropna(subset=["return_5"]), 5):
            q = p.dropna(subset=["return_5"])
            self.assertTrue((q.loc[train, "target_end_5"] < start).all())
            self.assertTrue((q.loc[valid, "date"] >= start).all())

    def test_protected_window_and_duplicate_bars_rejected(self):
        c, bars, _ = fixture()
        changed = {**c, "end": "2026-01-01"}
        with self.assertRaises(ValueError):
            validate_config(changed)
        with self.assertRaises(ValueError):
            build_panel(pd.concat([bars, bars.iloc[[0]]]), pd.DataFrame(), c)

    def test_math_helpers(self):
        x = np.arange(40, dtype=float)
        self.assertAlmostEqual(correlation(x, -x, True), -1)
        self.assertAlmostEqual(distance_correlation(x, x), 1)
        self.assertTrue(np.max(np.abs(residuals(2 * x + 5, x[:, None]))) < 1e-10)
        self.assertTrue(np.isnan(correlation(np.ones(10), np.arange(10))))
        ix = block_indices(list(range(100)), 10, np.random.default_rng(3))
        self.assertEqual(len(ix), 100)
        self.assertTrue(((ix >= 0) & (ix < 100)).all())

    def test_lag_preserves_missing_session_gap(self):
        c, bars, _ = fixture()
        p, features, quality = build_panel(bars, pd.DataFrame(), c)
        p = p[~((p.ticker == "AAPL") & (p.session == 45))].copy()
        p[features[0]] = (p.session % 11 == 0).astype(float)
        meta = {"features": [features[0]], "controls": ["past_return_5"]}
        found = False
        for frame, r in pairs(p, meta, c):
            if r["lag"] == 1:
                self.assertFalse(((frame.ticker == "AAPL") & (frame.session == 46)).any())
                found = True
        self.assertTrue(found)

    def test_event_support_counts_event_issuers_not_ordinary_issuers(self):
        c,bars,_=fixture()
        p,features,_=build_panel(bars,pd.DataFrame(),c)
        p[features[0]] = ((p.ticker == 'AAPL') & (p.session % 5 == 0)).astype(float)
        meta={"features":[features[0]],"controls":["past_return_5"]}
        for _,row in pairs(p,meta,c,[0]):
            self.assertEqual(row['positive_issuers'],1)
            self.assertEqual(row['status'],'inconclusive')

    def test_snapshot_tampering_and_missing_tasks_are_visible(self):
        c, bars, _ = fixture()
        with tempfile.TemporaryDirectory(dir=ROOT / "data/cache") as tmp:
            path = Path(tmp)
            snapshot(path / "input", bars, pd.DataFrame(), c, {"synthetic": True})
            m = plan(path / "input", path / "run")
            report = aggregate(path / "run")
            self.assertFalse(report["complete"])
            self.assertEqual(len(report["failures"]), len(m["tasks"]))
            with (path / "input/panel.csv").open("a") as f:
                f.write("changed")
            with self.assertRaises(ValueError):
                load_snapshot(path / "input")
            m["config"]["seed"] = 1
            write_json(path / "run/manifest.json", m)
            with self.assertRaises(ValueError):
                read_manifest(path / "run")

    def test_result_hash_rejects_forged_measurement(self):
        task = {"id": 0, "study": "H03"}
        m = {"manifest_id": "test"}
        r = {"manifest_id": "test", "task": task, "status": "complete", "rows": [{"pearson": .1}]}
        r["result_id"] = identity(r)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            write_json(path, r)
            self.assertTrue(valid_receipt(path, m, task))
            r["rows"][0]["pearson"] = .99
            write_json(path, r)
            with self.assertRaises(ValueError):
                valid_receipt(path, m, task)

    def test_date_moments_equal_explicit_row_bootstrap(self):
        p = pd.DataFrame({"date": ["a", "a", "b", "b", "b", "c"], "x": [0., 1., 0., 1., 1., 0.], "y": [.2, .3, -.1, .5, .2, .9]})
        sampled = [0, 1, 1]
        explicit = pd.concat([p[p.date == d] for d in ["a", "b", "b"]])
        self.assertAlmostEqual(correlation_moments(moments(p, "date")[sampled].sum(axis=0)), correlation(explicit.x, explicit.y))

    def test_demeaning_equals_full_issuer_fixed_effect_design(self):
        rng = np.random.default_rng(2)
        p = pd.DataFrame({"issuer": np.repeat(["a", "b", "c"], 20), "z": rng.normal(size=60), "x": rng.normal(size=60)})
        p["y"] = .4 * p.x + 2 * p.z + np.repeat([3, -1, 2], 20)
        full = np.column_stack([p.z, pd.get_dummies(p.issuer, drop_first=True, dtype=float)])
        rx, ry = residuals(p.x.to_numpy(), full), residuals(p.y.to_numpy(), full)
        within = p[["z", "x", "y"]] - p.groupby("issuer")[["z", "x", "y"]].transform("mean")
        wx, wy = residuals(within.x.to_numpy(), within[["z"]].to_numpy()), residuals(within.y.to_numpy(), within[["z"]].to_numpy())
        self.assertAlmostEqual(np.dot(rx, ry)/np.dot(rx,rx), np.dot(wx,wy)/np.dot(wx,wx))

    def test_all_nine_owned_implementations_parse(self):
        for study, folder in STUDIES.items():
            tree = ast.parse((ROOT / "Hypotheses" / folder / "analysis.py").read_text(encoding="utf-8"))
            self.assertTrue(any(isinstance(n, ast.FunctionDef) and n.name == "analyze" for n in tree.body), study)

    def test_return_archive_cannot_escape_the_run(self):
        import hashlib, json
        c, bars, _ = fixture()
        with tempfile.TemporaryDirectory(dir=ROOT / "data/cache") as tmp:
            path=Path(tmp)
            snapshot(path/'input', bars, pd.DataFrame(), c, {"synthetic": True})
            m=plan(path/'input',path/'run')
            archive=path/'return.zip'
            raw=b'escaped'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('../outside.txt',raw)
                z.writestr('RETURN-RECEIPT.json',json.dumps({"manifest_id":m['manifest_id'],"files":{"../outside.txt":hashlib.sha256(raw).hexdigest()}}))
            with self.assertRaises(ValueError):
                import_results(archive,path/'run')
            self.assertFalse((path/'outside.txt').exists())

    def test_scheduler_caps_and_dependencies_are_generated(self):
        c,bars,_=fixture()
        with tempfile.TemporaryDirectory(dir=ROOT/'data/cache') as tmp:
            path=Path(tmp)
            snapshot(path/'input',bars,pd.DataFrame(),c,{"synthetic":True})
            plan(path/'input',path/'run')
            job=write_jobs(path/'run','/blue/test-allocation/test-user/quanthacks/discovery/test-discovery','ai-workshop','ai-workshop',4)
            self.assertIn('--array=0-7%4',(job/'core.sbatch').read_text())
            submit=(job/'submit.sh').read_text()
            self.assertIn('afterok:$SETUP',submit)
            self.assertIn('afterany:$CORE',submit)
            self.assertIn('afterany:$UNCERTAINTY',submit)
            self.assertIn('SLURM_ARRAY_TASK_ID + 8',(job/'uncertainty.sbatch').read_text())
            setup=(job/'setup.sbatch').read_text()
            module_load=setup.index('module load python/3.12')
            clean_runtime=setup.index('unset PYTHONHOME PYTHONPATH',module_load)
            self.assertLess(module_load,clean_runtime)
            self.assertLess(clean_runtime,setup.index('uv sync --frozen --python 3.11'))
            for name in ['core.sbatch','uncertainty.sbatch','report.sbatch']:
                body=(job/name).read_text()
                self.assertLess(body.index('unset PYTHONHOME PYTHONPATH'),body.index('.venv/bin/python'))


if __name__ == "__main__":
    unittest.main()
