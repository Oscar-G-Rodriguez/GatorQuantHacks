"""Synthetic-only checks for the financing estimator and reporting gates."""
import copy
import json
from pathlib import Path

import numpy as np
import unittest
import tempfile
from unittest.mock import patch

from discovery import financing_analysis as a


def configuration():
    return json.loads(a.CONFIG.read_text(encoding='utf-8'))


def quartet(cfg, shape='covered_call'):
    rows = []
    for role, day, ret, loss in [('event', '2024-07-01', .02, .01), ('ordinary', '2024-01-02', .01, .02)]:
        for stock in [False, True]:
            rows.append({'study': 'H23', 'variant': 'primary', 'shape': shape, 'pair_id': 'one',
                'issuer': '001', 'role': role, 'stock_only': stock, 'horizon': 10,
                'status': 'completed', 'path_complete': True, 'date': day, 'decision_date': day,
                'event_decision': '2024-07-01', 'entry_date': day, 'exit_date': day,
                'evaluation_date': day, 'evaluation_aligned': True,
                'net_return': ret if stock else ret + .003, 'downside_loss': loss if stock else loss - .004,
                'decision_dte': 120, 'achieved_otm': .05, 'decision_premium_ratio': .02,
                **{k: float(i + 1) for i, k in enumerate(a.FEATURES)}})
    return rows


class FinancingAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.cfg = configuration()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.tmp_path = Path(self.directory.name)

    def test_nineteen_effects_remain_even_without_observations(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        specs = a.family(cfg)
        assert len(specs) == 19 and len({s.effect_id for s in specs}) == 19
        for s in specs:
            item = a.effect([], cfg, s)
            assert item['summary']['estimate'] is None
            assert item['summary']['status'] == 'insufficient_support'


    def test_duplicates_are_not_extra_activations(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        rows = quartet(cfg)
        assert len(a.unique_rows(rows + copy.deepcopy(rows))) == 4
        changed = copy.deepcopy(rows[0]); changed['net_return'] += .1
        with self.assertRaisesRegex(ValueError, 'Conflicting duplicate'):
            a.unique_rows(rows + [changed])


    def test_assignment_clock_uses_planned_evaluation_and_refuses_late_retry(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        rows = quartet(cfg); rows[0]['exit_date'] = '2024-06-28'
        spec = a.family(cfg)[0]
        assert len(a.quartets(rows, cfg, spec)[0]) == 1
        rows[0]['evaluation_aligned'] = False
        accepted, rejected = a.quartets(rows, cfg, spec)
        assert not accepted and rejected[0]['reason'] == 'stock_counterfactual_clock_differs'


    def test_path_gate_is_separate_from_complete_return(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        rows = quartet(cfg, 'protective_put'); rows[0]['path_complete'] = False
        specs = a.family(cfg)
        assert a.effect(rows, cfg, specs[2])['summary']['pairs'] == 0
        assert a.effect(rows, cfg, specs[4])['summary']['pairs'] == 1


    def test_missing_premium_cannot_become_eligible_zero(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        rows = quartet(cfg); rows[2]['decision_premium_ratio'] = ''
        accepted, rejected = a.quartets(rows, cfg, a.family(cfg)[0])
        assert not accepted and rejected[0]['reason'] == 'option_caliper_failed'
        assert a.finite('nan') is None and a.finite('') is None


    def test_effect_legs_preserve_actual_control_date(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        result = a.effect(quartet(cfg), cfg, a.family(cfg)[0])
        assert [r['date'] for r in result['legs']] == ['2024-07-01', '2024-01-02']
        assert np.allclose(result['values'], [0.])


    def test_reused_controls_collapse_on_same_issuer_calendar_cell(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        reduced = {**cfg, 'minimum_pairs': 1, 'minimum_issuers': 1}
        rows = quartet(cfg)
        other = copy.deepcopy(rows)
        for row in other:
            row['pair_id'] = 'two'
            if row['role'] == 'event':
                row.update(date='2024-07-02', decision_date='2024-07-02', event_decision='2024-07-02',
                           entry_date='2024-07-02', exit_date='2024-07-02', evaluation_date='2024-07-02')
                if not row['stock_only']:
                    row['net_return'] += .005
        item = a.effect(rows + other, reduced, a.family(cfg)[0])
        issuers, ii, ti, coefs = a.bootstrap_design([item], ['2024-01-02', '2024-07-01', '2024-07-02'])
        assert len(ii) == 3 and len(issuers) == 1
        assert item['summary']['reused_controls'] == 1


    def test_year_stratified_weights_have_fixed_stratum_and_history_mass(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        dates = ['2023-01-02', '2023-01-03', '2023-01-04', '2024-01-02', '2024-01-03']
        iw, cw = a.draw_weights(np.random.default_rng(1), 4, dates, 3, 10)
        assert np.all(iw.sum(axis=1) == 4)
        assert np.all(cw[:, :3].sum(axis=1) == 3)
        assert np.all(cw[:, 3:].sum(axis=1) == 2)


    def test_joint_draws_reproduce_and_share_overlap(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        reduced = {**cfg, 'minimum_pairs': 1, 'minimum_issuers': 1}
        rows = quartet(cfg); other = copy.deepcopy(rows)
        for row in other:
            row['pair_id'] = 'two'
            if row['role'] == 'event' and not row['stock_only']:
                row['net_return'] += .01
        item = a.effect(rows + other, reduced, a.family(cfg)[0])
        dates = ['2024-01-02', '2024-07-01']
        first = a.joint_draws([item, item], dates, 1, 33, 2)
        second = a.joint_draws([item, item], dates, 1, 33, 2)
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(first[:, 0], first[:, 1])


    def test_stepdown_monotonicity_and_degenerate_refusal(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        effects = [{'summary': {'support': True, 'estimate': value}} for value in [1., .1, 0.]]
        draws = np.random.default_rng(3).normal(0, .2, (999, 3)); draws[:, 2] = 0
        rows = a.simultaneous(effects, draws, 63)
        assert rows[0]['p_adjusted'] <= rows[1]['p_adjusted']
        assert rows[2]['status'] == 'unsupported_uncertainty'
        assert rows[2]['lower'] is None


    def test_scaling_and_intercept_do_not_fit_validation(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        train = [[0.], [1.], [2.]]; target = [0., 1., 2.]
        pred, fit = a.ridge_fit_predict(train, target, [[100.], [-100.]])
        assert fit['training_mean'] == [1.]
        assert fit['intercept'] == 1.
        assert pred[0] > pred[1]
        with self.assertRaisesRegex(ValueError, 'Missing ridge'):
            a.ridge_fit_predict(train, target, [[np.nan]])


    def test_prediction_purges_training_outcomes_crossing_year(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        reduced = {**cfg, 'minimum_pairs': 1, 'minimum_issuers': 1,
                   'minimum_year_pairs': 1, 'minimum_year_issuers': 1}
        rows = quartet(cfg)
        for row in rows:
            if row['role'] == 'ordinary':
                row.update(date='2023-12-20', decision_date='2023-12-20', evaluation_date='2024-01-05')
        result = a.prediction_diagnostics(rows, reduced)
        h23 = [r for r in result if r['study'] == 'H23' and r['shape'] == 'covered_call' and r['year'] == 2024]
        assert h23 and all(r['training_observations'] == 0 for r in h23)


    def test_invalid_nav_never_drops_missing_days(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        rows = [{'study': 'H23', 'variant': 'primary', 'shape': 'covered_call', 'role': 'event',
                 'stock_only': False, 'date': '2024-01-02', 'nav': 1000000, 'unknown_nav': False},
                {'study': 'H23', 'variant': 'primary', 'shape': 'covered_call', 'role': 'event',
                 'stock_only': False, 'date': '2024-01-03', 'nav': '', 'unknown_nav': True}]
        result = a.nav_performance(rows, cfg, [])
        pooled = next(r for r in result if r['year'] == 'all')
        assert pooled['sessions'] == 2 and pooled['annualized_return'] is None


    def test_changed_receipt_output_refuses_use(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        path = tmp_path / 'results/file.txt'; path.parent.mkdir(); path.write_text('original')
        folder = tmp_path / 'receipts'; folder.mkdir()
        (folder / 'task-0.json').write_text(json.dumps({'manifest_id': 'one', 'status': 'completed',
            'files': {'results/file.txt': a.digest(path)}}))
        assert a.verify_receipt(tmp_path, 'task-0', 'one')
        path.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            a.verify_receipt(tmp_path, 'task-0', 'one')


    def test_missing_calibration_stays_pending(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        assert a.calibration_gate(tmp_path, {'manifest_id': 'one'}, cfg)['status'] == 'pending'


    def test_missing_exact_placebo_sources_cannot_be_replaced_by_return_permutation(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        folder = tmp_path / 'prepared'; folder.mkdir()
        (folder / 'placebo-map.json').write_text(json.dumps([{'replica': i, 'shifts': []} for i in range(199)]))
        result = a.placebo_evidence(tmp_path, {'manifest_id': 'one'}, cfg, [])
        assert result['completed'] == 0 and result['planned'] == 199
        assert len(result['trials']) == 199 and all(r['status'] == 'pending' for r in result['trials'])


    def test_scheduled_entrypoints_refuse_local_real_calculation(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(RuntimeError):
                a.analyze(tmp_path)
            with self.assertRaises(RuntimeError):
                a.calibration(tmp_path)


    def test_null_fixture_is_synthetic_and_covers_all_registered_effects(self):
        cfg = self.cfg
        tmp_path = self.tmp_path
        rows, dates = a.synthetic_null(19, cfg)
        effects = [a.effect(rows, cfg, spec) for spec in a.family(cfg)]
        assert len(dates) > 1000 and len(effects) == 19
        assert all(item['summary']['support'] for item in effects)
        assert all(item['summary']['issuers'] == 20 for item in effects)
        assert all(item['summary']['reused_controls'] == 60 for item in effects)

    def test_index_matches_unindexed_contrasts(self):
        rows = quartet(self.cfg)
        indexed = a.OutcomeIndex(rows)
        spec = a.family(self.cfg)[0]
        assert a.effect(rows, self.cfg, spec) == a.effect(indexed, self.cfg, spec)

    def test_state_bins_fit_strictly_earlier_history(self):
        rows = quartet(self.cfg)
        cfg = {**self.cfg, 'minimum_pairs': 1, 'minimum_year_pairs': 1,
               'minimum_issuers': 1, 'minimum_year_issuers': 1}
        for r in rows:
            if r['role'] == 'ordinary':
                r.update(date='2023-01-03', decision_date='2023-01-03')
            else:
                r['volatility'] = 1000.
        output = a.state_diagnostics(a.OutcomeIndex(rows), cfg, [a.family(cfg)[0]])
        selected = [r for r in output if r['year'] == 2024 and r['state_feature'] == 'volatility']
        assert all(json.loads(r['cutpoints']) == [2., 2.] for r in selected)
        assert next(r for r in selected if r['state'] == 2)['pairs'] == 1

    def test_partial_synthetic_report_writes_all_cells_without_success_claim(self):
        run = self.tmp_path; cfg = {**self.cfg, 'resamples': 9, 'timing_placebos': 2}
        config = run / 'config.json'; config.write_text(json.dumps(cfg))
        prepared = run / 'prepared'; prepared.mkdir()
        (prepared / 'calendar.json').write_text(json.dumps({'dates': ['2024-01-02', '2024-07-01']}))
        (prepared / 'placebo-map.json').write_text(json.dumps([{'replica': i, 'shifts': []} for i in range(2)]))
        receipts = run / 'receipts'; receipts.mkdir(); (receipts / 'task-0.json').write_text('{}')
        rows = quartet(cfg)
        task = {'task': 0, 'study': 'H23', 'variant': 'primary', 'status': 'completed', 'details': {}}
        manifest = {'manifest_id': 'synthetic-only', 'scope': 'pilot', 'phase': 'backtest'}

        def scientific_receipt(run, stage, files, extra=None):
            record = {'manifest_id': 'synthetic-only', 'status': 'completed',
                      'files': {p.relative_to(run).as_posix(): a.digest(p) for p in files}, **(extra or {})}
            (run / 'receipts' / (stage + '.json')).write_text(json.dumps(record))

        with patch.object(a, 'CONFIG', config), patch.object(a, 'scheduled'), \
                patch.object(a, 'verify_manifest', return_value=manifest), \
                patch.object(a, 'load_tasks', return_value=(rows, [], [task])), \
                patch.object(a, 'receipt', side_effect=scientific_receipt):
            result = a.analyze(run)
            assert result['primary_family_size'] == 19
            assert result['calibration_status'] == 'pending'
            assert result['timing_placebos_completed'] == 0
            assert result['verdict'] == 'UNSUPPORTED_FOR_CONFIRMATORY_CLAIM'
            family = a.records(run / 'results/joint/primary_family.csv')
            assert len(family) == 38
            checks = json.loads((run / 'results/H23/validation_checks.json').read_text())['checks']
            assert {r['id'] for r in checks} == {f'S{i:02d}' for i in range(1, 13)}
            assert a.analyze(run) == result

    def test_missing_evaluation_alignment_is_unknown_not_success(self):
        rows = quartet(self.cfg)
        del rows[0]['evaluation_aligned']
        assert not a.quartets(rows, self.cfg, a.family(self.cfg)[0])[0]

    def test_missing_nav_session_cannot_shorten_the_performance_clock(self):
        rows = [{'study': 'H23', 'variant': 'primary', 'shape': 'covered_call', 'role': 'event',
                 'stock_only': False, 'date': '2024-01-02', 'nav': 1000000, 'unknown_nav': False},
                {'study': 'H23', 'variant': 'primary', 'shape': 'covered_call', 'role': 'event',
                 'stock_only': False, 'date': '2024-01-04', 'nav': 1100000, 'unknown_nav': False}]
        output = a.nav_performance(rows, self.cfg, [], ['2024-01-02', '2024-01-03', '2024-01-04'])
        pooled = next(r for r in output if r['year'] == 'all')
        assert pooled['annualized_return'] is None
        assert pooled['reason'] == 'missing_portfolio_calendar_sessions'

    def test_calibration_summary_without_100_checkpoints_cannot_pass(self):
        run = self.tmp_path; directory = run / 'results/calibration'; directory.mkdir(parents=True)
        summary = {'datasets': 100, 'draws_per_dataset': 9999, 'declared_family_size': 19,
                   'blocks': [{'block': 63, 'status': 'pass'}, {'block': 126, 'status': 'pass'}], 'status': 'pass'}
        path = directory / 'summary.json'; path.write_text(json.dumps(summary))
        receipts = run / 'receipts'; receipts.mkdir()
        (receipts / 'calibration.json').write_text(json.dumps({'manifest_id': 'one', 'status': 'completed',
            'files': {'results/calibration/summary.json': a.digest(path)}}))
        with self.assertRaisesRegex(ValueError, 'not in its receipt'):
            a.calibration_gate(run, {'manifest_id': 'one'}, self.cfg)

    def test_control_attribution_requires_own_earlier_fit(self):
        rows = quartet(self.cfg)
        cfg = {**self.cfg, 'minimum_pairs': 1, 'minimum_issuers': 1,
               'minimum_year_pairs': 1, 'minimum_year_issuers': 1}
        for row in rows:
            if row['role'] == 'ordinary':
                row.update(date='2022-07-01', decision_date='2022-07-01', evaluation_date='2022-07-01')
        output = a.attribution_diagnostics(a.OutcomeIndex(rows), cfg)
        result = next(r for r in output if r['study'] == 'H23' and r['shape'] == 'covered_call' and r['year'] == 2024)
        assert result['training_observations'] == 1
        assert result['pairs'] == 0 and result['residual_increment'] is None

if __name__ == "__main__":
    unittest.main()
