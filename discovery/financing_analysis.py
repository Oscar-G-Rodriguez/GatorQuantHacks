"""Registered financing comparisons; real calculations require Slurm.

Trading cash flows belong to financing_strategy. This module compares its
verified outcomes without changing entry rules, filtering the label cohort,
choosing a winning variant, or manufacturing an unseen confirmation period.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import time
try:
    import resource
except ImportError:
    resource = None
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .io import digest, identity, now, read_json, safe_child, write_json
from .financing_research import CONFIG, REGISTRATION, csv_write, receipt, scheduled, verify_manifest


@dataclass(frozen=True)
class EffectSpec:
    effect_id: str
    study: str
    shape: str
    metric: str
    comparator: str
    threshold: float


def family(cfg):
    """The nineteen predeclared effects, including unavailable contrasts."""
    specs = []
    for study in cfg['studies']:
        sid = study['id']
        for shape, metric, threshold in [
            ('covered_call', 'overlay_increment', cfg['practical_call_overlay']),
            ('covered_call', 'strategy_increment', 0.),
            ('protective_put', 'hedge_increment', 0.),
            ('protective_put', 'event_downside_reduction', cfg['practical_put_downside']),
            ('protective_put', 'event_return_drag', -cfg['maximum_put_return_drag']),
        ]:
            specs.append(EffectSpec(f'{sid}:{metric}:ordinary', sid, shape, metric, 'ordinary', threshold))
    for role in ['debt_only', 'underwriting_only']:
        for shape, metric in [('covered_call', 'overlay_increment'), ('protective_put', 'hedge_increment')]:
            specs.append(EffectSpec(f'H25:{metric}:{role}', 'H25', shape, metric, role, 0.))
    if len(specs) != cfg['primary_family_size']:
        raise ValueError('Declared family size differs from the registered estimands')
    return specs


def truth(value):
    return str(value).strip().lower() in {'true', '1', 'yes'}


def finite(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def records(path):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def verify_receipt(run, stage, manifest_id):
    """Verify completed files, rather than trusting a status string."""
    path = Path(run) / 'receipts' / (stage + '.json')
    if not path.exists():
        return None
    result = read_json(path)
    if result.get('manifest_id') != manifest_id or result.get('status') != 'completed':
        raise ValueError('Wrong or incomplete scientific receipt: ' + stage)
    if not result.get('files'):
        raise ValueError('Scientific receipt has no verified members: ' + stage)
    for name, expected in result.get('files', {}).items():
        if digest(safe_child(run, name)) != expected:
            raise ValueError('Scientific output changed: ' + name)
    return result


def receipted_file(run, checked, path):
    relative = Path(path).relative_to(run).as_posix()
    if not checked or relative not in {str(k).replace('\\', '/') for k in checked['files']}:
        raise ValueError('Required scientific artifact is not in its receipt: ' + relative)
    return path


def row_key(row):
    return (row['study'], row['variant'], row['shape'], row['pair_id'], row['role'],
            truth(row['stock_only']), str(row['horizon']))


def unique_rows(rows):
    found = {}
    for row in rows:
        key = row_key(row)
        if key in found:
            # Attempt/task IDs are provenance, not extra independent observations.
            ignored = {'task', 'attempt'}
            left = {k: v for k, v in row.items() if k not in ignored}
            right = {k: v for k, v in found[key].items() if k not in ignored}
            if left != right:
                raise ValueError('Conflicting duplicate outcome: ' + repr(key))
        else:
            found[key] = row
    return list(found.values())


class OutcomeIndex:
    """One deduplication pass, then bounded study/setting/shape/horizon scans."""
    def __init__(self, rows):
        self.rows = unique_rows(rows); self.groups = defaultdict(list)
        for row in self.rows:
            self.groups[(row['study'], row['variant'], row['shape'], str(row['horizon']))].append(row)

    def __iter__(self):
        return iter(self.rows)

    def get(self, study, variant, shape, horizon):
        return self.groups[(study, variant, shape, str(horizon))]


def complete(row, path=False):
    if row.get('status') not in {'completed', 'complete'} or finite(row.get('net_return')) is None:
        return False
    return not path or (truth(row.get('path_complete')) and finite(row.get('downside_loss')) is not None)


def calipers(event, control, cfg):
    values = [(finite(event.get(k)), finite(control.get(k))) for k in
              ['decision_dte', 'achieved_otm', 'decision_premium_ratio']]
    if any(a is None or b is None for a, b in values):
        return False
    (ed, od), (em, om), (ep, op) = values
    return (abs(ed - od) <= cfg['match_dte_days'] and
            abs(em - om) <= cfg['match_otm'] + 1e-12 and ep > 0 and op > 0 and
            max(ep, op) / min(ep, op) <= cfg['match_premium_factor'])


def quartets(rows, cfg, spec, variant='primary', horizon=10, year=None, omit_issuer=None):
    """Return-complete and path-complete cohorts are deliberately separate."""
    groups = defaultdict(dict)
    path = spec.metric in {'hedge_increment', 'event_downside_reduction'}
    source = rows.get(spec.study, variant, spec.shape, horizon) if isinstance(rows, OutcomeIndex) else unique_rows(rows)
    for row in source:
        if (row['study'], row['variant'], row['shape'], str(row['horizon'])) != (
                spec.study, variant, spec.shape, str(horizon)):
            continue
        if row['issuer'] == omit_issuer:
            continue
        groups[row['pair_id']][(row['role'], truth(row['stock_only']))] = row
    accepted, excluded = [], []
    for pair_id, group in sorted(groups.items()):
        required = [('event', False), ('event', True), (spec.comparator, False), (spec.comparator, True)]
        if not all(key in group for key in required):
            excluded.append({'pair_id': pair_id, 'reason': 'missing_quartet_member'}); continue
        e, es, o, os = (group[key] for key in required)
        event_year = int(str(e.get('event_decision') or e.get('decision_date') or e['date'])[:4])
        if year is not None and event_year != int(year):
            continue
        if not all(complete(row, path) for row in [e, es, o, os]):
            excluded.append({'pair_id': pair_id, 'reason': 'incomplete_path' if path else 'incomplete_return'}); continue
        if len({row['issuer'] for row in [e, es, o, os]}) != 1:
            raise ValueError('A paired comparison crosses issuers')
        for strategy, stock in [(e, es), (o, os)]:
            aligned = all(truth(row.get('evaluation_aligned')) for row in [strategy, stock])
            end = lambda row: row.get('evaluation_date') or row['exit_date']
            if not aligned or (strategy['entry_date'], end(strategy)) != (stock['entry_date'], end(stock)):
                excluded.append({'pair_id': pair_id, 'reason': 'stock_counterfactual_clock_differs'}); break
        else:
            if not calipers(e, o, cfg):
                excluded.append({'pair_id': pair_id, 'reason': 'option_caliper_failed'}); continue
            accepted.append((e, es, o, os))
    return accepted, excluded


def outcome_legs(spec, quartet):
    """Keep actual control dates, including each reused control's contribution."""
    e, es, o, os = quartet
    r = lambda row: float(row['net_return'])
    d = lambda row: float(row['downside_loss'])
    if spec.metric == 'overlay_increment':
        return [(e, r(e) - r(es), 1.), (o, r(o) - r(os), -1.)]
    if spec.metric == 'strategy_increment':
        return [(e, r(e), 1.), (o, r(o), -1.)]
    if spec.metric == 'hedge_increment':
        return [(e, d(es) - d(e), 1.), (o, d(os) - d(o), -1.)]
    if spec.metric == 'event_downside_reduction':
        return [(e, d(es) - d(e), 1.)]
    if spec.metric == 'event_return_drag':
        return [(e, r(e) - r(es), 1.)]
    raise ValueError('Unknown estimand')


def effect(rows, cfg, spec, variant='primary', horizon=10, year=None, omit_issuer=None):
    qs, exclusions = quartets(rows, cfg, spec, variant, horizon, year, omit_issuer)
    return summarize_quartets(qs, exclusions, cfg, spec, variant, horizon, year)


def summarize_quartets(qs, exclusions, cfg, spec, variant='primary', horizon=10, year=None):
    values, legs = [], []
    for q in qs:
        terms = outcome_legs(spec, q)
        values.append(sum(value * sign for _, value, sign in terms))
        for position, (row, value, sign) in enumerate(terms):
            legs.append({'issuer': row['issuer'], 'date': row.get('decision_date') or row['date'],
                         'value': value, 'sign': sign, 'position': position, 'pair_id': row['pair_id']})
    issuers = len({q[0]['issuer'] for q in qs})
    minimum = cfg['minimum_pairs'] if year is None else cfg['minimum_year_pairs']
    minimum_issuers = cfg['minimum_issuers'] if year is None else cfg['minimum_year_issuers']
    supported = len(qs) >= minimum and issuers >= minimum_issuers
    result = {'effect_id': spec.effect_id, 'study': spec.study, 'shape': spec.shape,
              'variant': variant, 'horizon': horizon, 'year': 'all' if year is None else year,
              'comparator': spec.comparator, 'metric': spec.metric,
              'estimate': float(np.mean(values)) if values else None, 'pairs': len(qs), 'issuers': issuers,
              'status': 'eligible_descriptive' if supported else 'insufficient_support',
              'reason': '' if supported else 'registered_pair_or_issuer_floor',
              'threshold': spec.threshold, 'excluded_pairs': len(exclusions),
              'reused_controls': len(qs) - len({(q[2]['issuer'], q[2].get('decision_date') or q[2]['date']) for q in qs}),
              'support': supported}
    return {'summary': result, 'legs': legs, 'values': values, 'exclusions': exclusions}


def bootstrap_design(effects, dates):
    """Sparse issuer/date influence coefficients for the fixed mean contrasts.

    Each role is centered separately. Paired differences retain their actual
    event AND control calendars, so reused controls and overlapping studies
    share the same weights instead of becoming independent synthetic rows.
    """
    issuers = sorted({leg['issuer'] for item in effects for leg in item['legs']})
    calendar = {str(day): i for i, day in enumerate(dates)}
    if len(calendar) != len(dates):
        raise ValueError('Duplicate calendar sessions')
    coefficient = defaultdict(lambda: np.zeros(len(effects)))
    for k, item in enumerate(effects):
        n = item['summary']['pairs']
        if not item['summary']['support'] or not n:
            continue
        centered = {}
        for position in {leg['position'] for leg in item['legs']}:
            centered[position] = np.mean([leg['value'] for leg in item['legs'] if leg['position'] == position])
        for leg in item['legs']:
            if leg['date'] not in calendar:
                raise ValueError('An inference leg lies outside the approved calendar')
            coefficient[(leg['issuer'], leg['date'])][k] += (
                leg['sign'] * (leg['value'] - centered[leg['position']]) / n)
    cells = sorted(coefficient)
    imap = {name: i for i, name in enumerate(issuers)}
    coefficients = np.vstack([coefficient[key] for key in cells]) if cells else np.empty((0, len(effects)))
    return (issuers, np.array([imap[key[0]] for key in cells], dtype=int),
            np.array([calendar[key[1]] for key in cells], dtype=int), coefficients)


def draw_weights(rng, issuers, dates, block, count):
    """Multinomial histories plus common circular calendar blocks by year."""
    iw = rng.multinomial(issuers, np.full(issuers, 1 / issuers), size=count).astype(float)
    cw = np.zeros((count, len(dates)), dtype=float)
    strata = defaultdict(list)
    for index, day in enumerate(dates):
        strata[str(day)[:4]].append(index)
    for indices in strata.values():
        n = len(indices)
        starts = rng.integers(n, size=(count, math.ceil(n / block)))
        slots = ((starts[..., None] + np.arange(block)) % n).reshape(count, -1)[:, :n]
        local = np.zeros((count, n), dtype=float)
        np.add.at(local, (np.repeat(np.arange(count), n), slots.ravel()), 1.)
        cw[:, indices] = local
    return iw, cw


def joint_draws(effects, dates, block, draws, seed, batch=256):
    """All family members use the same sampled issuer histories/calendar."""
    issuers, ii, ti, coefficients = bootstrap_design(effects, dates)
    result = np.full((draws, len(effects)), np.nan)
    if not len(issuers) or not len(ii):
        return result
    rng = np.random.default_rng(seed)
    for start in range(0, draws, batch):
        count = min(batch, draws - start)
        iw, cw = draw_weights(rng, len(issuers), dates, block, count)
        weights = iw[:, ii] * cw[:, ti] - 1.
        result[start:start + count] = weights @ coefficients
    result[:, [not item['summary']['support'] for item in effects]] = np.nan
    return result


def simultaneous(effects, draws, block, alpha=.05):
    """Centered studentized max-|t| bounds and Romano--Wolf stepdown."""
    rows = []
    standard_errors = np.array([np.std(draws[:, i], ddof=1) if np.isfinite(draws[:, i]).all() else np.nan
                               for i in range(len(effects))])
    valid = [i for i, item in enumerate(effects) if item['summary']['support'] and
             np.isfinite(standard_errors[i]) and standard_errors[i] > 1e-12]
    pvalues = {}; critical = None
    if valid:
        studentized = np.abs(draws[:, valid] / standard_errors[valid])
        maximum = np.max(studentized, axis=1)
        critical = float(np.quantile(maximum, 1 - alpha, method='higher'))
        observed = {i: abs(effects[i]['summary']['estimate'] / standard_errors[i]) for i in valid}
        remaining = sorted(valid, key=lambda i: (-observed[i], i))
        previous = 0.
        while remaining:
            index = remaining[0]
            null_maximum = np.max(np.abs(draws[:, remaining] / standard_errors[remaining]), axis=1)
            pvalue = (1 + np.count_nonzero(null_maximum >= observed[index])) / (len(draws) + 1)
            previous = max(previous, float(pvalue))
            pvalues[index] = previous
            remaining.pop(0)
    for index, item in enumerate(effects):
        row = {**item['summary'], 'block': block, 'draws': len(draws), 'declared_family_size': len(effects),
               'eligible_family_size': len(valid), 'standard_error': None, 'lower': None,
               'upper': None, 'p_adjusted': None, 'critical_value': critical}
        if index in valid:
            se = float(standard_errors[index]); estimate = row['estimate']
            row.update(standard_error=se, lower=estimate - critical * se, upper=estimate + critical * se,
                       p_adjusted=pvalues[index], status='approximate_inference')
        elif row['support']:
            row.update(status='unsupported_uncertainty', reason='degenerate_or_nonfinite_joint_draws')
        rows.append(row)
    return rows


def synthetic_null(seed, cfg):
    """Zero-effect synthetic histories with shared shocks and reused controls.

    This is an estimator calibration fixture, not an economic backtest or
    manufactured market result. Nonnegative loss levels have zero-mean hedge
    differences; all nineteen true contrasts are zero under this fixture.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range('2022-01-01', '2025-12-31').strftime('%Y-%m-%d').tolist()
    n = len(dates); ni = 20
    shocks = rng.normal(size=(4, n))
    for j in range(1, n):
        shocks[:, j] = .6 * shocks[:, j - 1] + shocks[:, j]
    histories = rng.normal(size=(ni, 4, n))
    for j in range(1, n):
        histories[:, :, j] = .35 * histories[:, :, j - 1] + histories[:, :, j]
    values = .002 * histories + .003 * shocks[None, :, :] + rng.normal(0, .001, (ni, 4, 1))
    rows = []
    for study in cfg['studies']:
        for issuer in range(ni):
            for observation, e in enumerate([300, 340, 600, 640, 850, 890]):
                # Two events reuse the same actual ordinary-date observation.
                base = e - (observation % 2) * 40
                role_dates = {'event': e, 'ordinary': base - 100}
                if study['id'] == 'H25':
                    role_dates.update(debt_only=base - 120, underwriting_only=base - 140)
                for shape in cfg['shapes']:
                    for role, t in role_dates.items():
                        stock = values[issuer, 0, t]
                        overlay = values[issuer, 1 if shape == 'covered_call' else 2, t]
                        reduction = values[issuer, 3, t]
                        for stock_only in [False, True]:
                            rows.append({'study': study['id'], 'variant': 'primary', 'shape': shape,
                                'pair_id': f'{study["id"]}-{issuer}-{observation}', 'issuer': str(issuer),
                                'role': role, 'stock_only': stock_only, 'horizon': 10, 'status': 'completed',
                                'path_complete': True, 'date': dates[t], 'decision_date': dates[t],
                                'event_decision': dates[e], 'entry_date': dates[t + 1], 'exit_date': dates[t + 11],
                                'evaluation_date': dates[t + 11], 'evaluation_aligned': True,
                                'decision_dte': 120, 'achieved_otm': .05, 'decision_premium_ratio': .02,
                                'net_return': stock if stock_only else stock + overlay,
                                'downside_loss': .1 if stock_only else .1 - reduction})
    return rows, dates


def calibration(run):
    """Fixed, checkpointed synthetic calibration; never retry favorable seeds."""
    scheduled(); m = verify_manifest(run); run = Path(run); cfg = read_json(CONFIG)
    if verify_receipt(run, 'calibration', m['manifest_id']):
        return calibration_gate(run, m, cfg)
    directory = run / 'results/calibration'; directory.mkdir(parents=True, exist_ok=True)
    evidence = []; specs = family(cfg)
    for replica in range(cfg['synthetic_null_replicas']):
        started = time.monotonic(); cpu_started = time.process_time(); path = directory / f'dataset-{replica:03d}.json'
        if path.exists():
            record = read_json(path)
            if (record.get('manifest_id') != m['manifest_id'] or record.get('replica') != replica or
                    record.get('seed') != cfg['seed'] + 900000 + replica or record.get('draws') != cfg['resamples'] or
                    record.get('checkpoint_id') != identity({k: v for k, v in record.items() if k != 'checkpoint_id'}) or
                    sorted(x['block'] for x in record.get('blocks', [])) != sorted(cfg['blocks'])):
                raise ValueError('Calibration checkpoint differs')
            for block_result in record['blocks']:
                if block_result['status'] == 'completed' and (len(block_result.get('effects', [])) != len(specs) or
                        any(x.get('draws') != cfg['resamples'] for x in block_result['effects'])):
                    raise ValueError('Calibration checkpoint has incomplete family or draws')
        else:
            rows, dates = synthetic_null(cfg['seed'] + 900000 + replica, cfg)
            effects = [effect(rows, cfg, spec) for spec in specs]
            blocks = []
            for block in cfg['blocks']:
                sampled = joint_draws(effects, dates, block, cfg['resamples'], cfg['seed'] + replica * 1000 + block)
                inference = simultaneous(effects, sampled, block)
                if any(row['status'] != 'approximate_inference' for row in inference):
                    blocks.append({'block': block, 'status': 'unsupported', 'rejected': None})
                else:
                    blocks.append({'block': block, 'status': 'completed',
                        'rejected': any(row['p_adjusted'] <= .05 for row in inference),
                        'effects': inference})
            record = {'manifest_id': m['manifest_id'], 'replica': replica,
                'seed': cfg['seed'] + 900000 + replica, 'draws': cfg['resamples'], 'blocks': blocks,
                'elapsed_seconds': time.monotonic() - started, 'cpu_seconds': time.process_time() - cpu_started,
                'max_rss_kib_linux': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None,
                'completed_at': now()}
            record['checkpoint_id'] = identity(record)
            write_json(path, record)
        evidence.append(record)
        print(json.dumps({'stage': 'calibration', 'replica': replica,
                          'elapsed_seconds': record['elapsed_seconds'], 'blocks': record['blocks'][0]['status'],
                          'first_rep_estimated_total_seconds': record['elapsed_seconds'] * cfg['synthetic_null_replicas'] if replica == 0 else None,
                          'max_rss_kib_linux': record.get('max_rss_kib_linux')}), flush=True)
    counts = []
    for block in cfg['blocks']:
        results = [next(x for x in row['blocks'] if x['block'] == block) for row in evidence]
        completed = [row for row in results if row['status'] == 'completed']
        rejected = sum(row['rejected'] for row in completed)
        counts.append({'block': block, 'datasets': len(results), 'completed': len(completed),
                       'false_rejections': rejected, 'maximum_allowed': cfg['synthetic_null_max_rejections'],
                       'status': 'pass' if len(completed) == cfg['synthetic_null_replicas'] and
                       rejected <= cfg['synthetic_null_max_rejections'] else 'fail'})
    summary = {'manifest_id': m['manifest_id'], 'datasets': len(evidence), 'draws_per_dataset': cfg['resamples'],
               'declared_family_size': len(specs), 'blocks': counts,
               'status': 'pass' if all(row['status'] == 'pass' for row in counts) else 'fail',
               'fixture': 'serial histories/shared calendar shocks/reused controls/overlapping cohorts',
               'scope': 'synthetic estimator calibration, not empirical signal evidence'}
    write_json(directory / 'summary.json', summary)
    receipt(run, 'calibration', list(directory.glob('*.json')), {'calibration_status': summary['status']})
    return summary


def load_tasks(run, manifest):
    """Consume only immutable completed task artifacts; missing stays pending."""
    rows, nav, tasks = [], [], []
    for task in read_json(Path(run) / 'tasks.json'):
        task_id = task['task']
        checked = verify_receipt(run, f'task-{task_id}', manifest['manifest_id'])
        folder = Path(run) / 'results/tasks' / str(task_id)
        if checked is None:
            tasks.append({**task, 'status': 'pending', 'reason': 'missing_verified_task_receipt'}); continue
        required = [folder / name for name in ['trades.csv', 'nav.csv', 'task.json']]
        if not all(str(path.relative_to(run)).replace('\\', '/') in checked['files'] or
                   str(path.relative_to(run)) in checked['files'] for path in required):
            raise ValueError('Task receipt omits required outcomes')
        details = read_json(folder / 'task.json')
        if details.get('task') != task or details.get('manifest_id') != manifest['manifest_id']:
            raise ValueError('Task artifact identity differs')
        task_rows = records(folder / 'trades.csv')
        if any(row.get('study') != task['study'] or row.get('variant') != task['variant'] for row in task_rows):
            raise ValueError('Task table has another study or setting')
        rows.extend(task_rows); nav.extend(records(folder / 'nav.csv'))
        tasks.append({**task, 'status': 'completed', 'reason': '', 'details': details})
    return unique_rows(rows), nav, tasks


def nav_performance(nav, cfg, task_records, calendar=None):
    """Cash-funded daily NAV metrics. Invalid paths never disappear silently."""
    groups = defaultdict(list)
    for row in nav:
        key = tuple(row[k] for k in ['study', 'variant', 'shape', 'role', 'stock_only'])
        groups[key].append(row)
    output = []
    portfolios = {}
    for task in task_records:
        for p in task.get('details', {}).get('portfolios', []):
            portfolios[(p['study'], p['variant'], p['shape'], p['role'], str(truth(p['stock_only'])))] = p
    for key, source in sorted(groups.items()):
        source.sort(key=lambda row: row['date'])
        if len({row['date'] for row in source}) != len(source):
            raise ValueError('Duplicate daily portfolio valuation')
        for year in ['all', 2022, 2023, 2024, 2025]:
            selected = source if year == 'all' else [r for r in source if str(r['date']).startswith(str(year))]
            label = dict(zip(['study', 'variant', 'shape', 'role', 'stock_only'], key))
            row = {**label, 'stock_only': truth(label['stock_only']), 'year': year,
                   'start': selected[0]['date'] if selected else None,
                   'end': selected[-1]['date'] if selected else None, 'sessions': len(selected),
                   'annualized_return': None, 'annualized_volatility': None, 'sharpe': None,
                   'max_drawdown': None, 'turnover': None, 'status': 'unsupported', 'reason': 'empty_nav'}
            if not selected:
                output.append(row); continue
            prior = [r for r in source if r['date'] < selected[0]['date']]
            initial = finite(prior[-1]['nav']) if prior else cfg['initial_cash']
            values = [finite(r['nav']) for r in selected]
            expected = calendar if year == 'all' else [d for d in (calendar or []) if d.startswith(str(year))]
            if calendar is not None and [r['date'] for r in selected] != expected:
                row['reason'] = 'missing_portfolio_calendar_sessions'; output.append(row); continue
            if initial is None or initial <= 0 or any(v is None or v <= 0 for v in values) or any(
                    truth(r.get('unknown_nav')) for r in selected) or (prior and truth(prior[-1].get('unknown_nav'))):
                row['reason'] = 'missing_or_invalid_daily_nav'; output.append(row); continue
            p = portfolios.get((*key[:4], str(truth(key[4]))), {})
            if year == 'all' and p and not truth(p.get('full_nav_available')):
                row['reason'] = 'unresolved_funded_positions'; output.append(row); continue
            path = np.array([initial, *values]); returns = path[1:] / path[:-1] - 1
            vol = float(np.std(returns, ddof=1) * np.sqrt(252)) if len(returns) > 1 else 0.
            row.update(annualized_return=float((path[-1] / initial) ** (252 / len(selected)) - 1),
                       annualized_volatility=vol, sharpe=float(np.mean(returns) * 252 / vol) if vol > 0 else None,
                       max_drawdown=float(np.min(path / np.maximum.accumulate(path) - 1)),
                       turnover=finite(p.get('turnover')) if year == 'all' else None,
                       status='completed_descriptive', reason='' if year == 'all' else 'annual_turnover_not_available')
            output.append(row)
    return output


FEATURES = ['momentum', 'volatility', 'volume_state', 'market_momentum', 'market_volatility']
OPTION_FEATURES = ['decision_premium_ratio', 'decision_dte', 'achieved_otm']


def ridge_fit_predict(train_x, train_y, test_x, penalty=10.):
    """The scaler, intercept and ridge fit use training observations only."""
    x = np.asarray(train_x, dtype=float); y = np.asarray(train_y, dtype=float)
    z = np.asarray(test_x, dtype=float)
    if x.ndim != 2 or z.ndim != 2 or x.shape[1] != z.shape[1] or not len(x):
        raise ValueError('Invalid ridge input dimensions')
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(z).all():
        raise ValueError('Missing ridge features cannot become zero')
    mean = x.mean(axis=0); scale = x.std(axis=0); scale[scale < 1e-12] = 1.
    sx = (x - mean) / scale; sz = (z - mean) / scale; intercept = float(y.mean())
    coefficient = np.linalg.solve(sx.T @ sx + penalty * np.eye(x.shape[1]), sx.T @ (y - intercept))
    return sz @ coefficient + intercept, {'training_mean': mean.tolist(), 'training_scale': scale.tolist(),
                                          'coefficient': coefficient.tolist(), 'intercept': intercept}


def prediction_diagnostics(rows, cfg):
    """Chronological stock-outcome forecasts on identical paired observations.

    These diagnostic forecasts do not optimize a trading rule. Ordinary controls
    are not cloned for fitting when multiple later events reuse them.
    """
    output = []
    for study in cfg['studies']:
        for shape in cfg['shapes']:
            spec = EffectSpec('', study['id'], shape, 'overlay_increment', 'ordinary', 0.)
            qs, _ = quartets(rows, cfg, spec)
            observations = {}
            for q in qs:
                for strategy, stock in [(q[0], q[1]), (q[2], q[3])]:
                    xs = [finite(strategy.get(k)) for k in FEATURES + OPTION_FEATURES]
                    if any(x is None for x in xs):
                        continue
                    key = (strategy['issuer'], strategy['date'], strategy['role'])
                    observations[key] = {'row': strategy, 'x': xs,
                        'label': float(strategy['role'] == 'event'), 'target': float(stock['net_return']),
                        'evaluation_date': stock.get('evaluation_date') or stock['exit_date']}
            for year in [2023, 2024, 2025]:
                boundary = f'{year}-01-01'
                train = [r for r in observations.values() if r['evaluation_date'] < boundary]
                test = [r for r in observations.values() if str(r['row']['date']).startswith(str(year))]
                base = {'study': study['id'], 'shape': shape, 'variant': 'primary', 'year': year,
                        'training_observations': len(train), 'validation_observations': len(test),
                        'training_issuers': len({r['row']['issuer'] for r in train}),
                        'validation_issuers': len({r['row']['issuer'] for r in test}),
                        'status': 'insufficient_support', 'reason': 'chronological_training_or_validation_floor',
                        'baseline_mse': None, 'disclosure_mse': None, 'paired_error_improvement': None,
                        'event_error_improvement': None, 'cohort': 'matched_priced_pairs',
                        'fresh_oos': False}
                enough = (len(train) >= cfg['minimum_pairs'] and base['training_issuers'] >= cfg['minimum_issuers'] and
                          len(test) >= cfg['minimum_year_pairs'] and base['validation_issuers'] >= cfg['minimum_year_issuers'])
                for target in ['signed_return', 'absolute_return']:
                    record = {**base, 'target': target}
                    if enough:
                        tx = np.array([r['x'] for r in train]); vx = np.array([r['x'] for r in test])
                        ty = np.array([r['target'] for r in train]); vy = np.array([r['target'] for r in test])
                        if target == 'absolute_return':
                            ty = np.abs(ty); vy = np.abs(vy)
                        pred, fit = ridge_fit_predict(tx, ty, vx, cfg['ridge_penalty'])
                        aug, aug_fit = ridge_fit_predict(
                            np.column_stack([tx, [r['label'] for r in train]]), ty,
                            np.column_stack([vx, [r['label'] for r in test]]), cfg['ridge_penalty'])
                        difference = (vy - pred) ** 2 - (vy - aug) ** 2
                        event = np.array([r['label'] == 1 for r in test])
                        record.update(baseline_mse=float(np.mean((vy - pred) ** 2)),
                                      disclosure_mse=float(np.mean((vy - aug) ** 2)),
                                      paired_error_improvement=float(np.mean(difference)),
                                      event_error_improvement=float(np.mean(difference[event])) if event.any() else None,
                                      status='completed_development_diagnostic', reason='',
                                      baseline_fit=json.dumps(fit), disclosure_fit=json.dumps(aug_fit))
                    output.append(record)
    return output


def attribution_diagnostics(rows, cfg):
    """Earlier-fit Massive market/option conditional residuals, never factor alpha."""
    output = []
    for study in cfg['studies']:
        for shape in cfg['shapes']:
            spec = EffectSpec('', study['id'], shape, 'strategy_increment', 'ordinary', 0.)
            qs, _ = quartets(rows, cfg, spec)
            unique = {}
            for q in qs:
                for r in [q[0], q[2]]:
                    x = [finite(r.get(k)) for k in FEATURES + OPTION_FEATURES]
                    if all(v is not None for v in x):
                        unique[(r['issuer'], r['date'], r['role'])] = (r, x)
            residuals = {}; fitted = {}
            for clock_year in [2023, 2024, 2025]:
                # Each ordinary observation needs its OWN earlier-year fit. An
                # event's later fit must not learn that ordinary target first.
                train = [(r, x) for r, x in unique.values() if (r.get('evaluation_date') or r['exit_date']) < f'{clock_year}-01-01']
                validation = [(r, x) for r, x in unique.values() if str(r['date']).startswith(str(clock_year))]
                if len(train) < cfg['minimum_pairs'] or len({r['issuer'] for r, _ in train}) < cfg['minimum_issuers'] or not validation:
                    continue
                predicted, fit = ridge_fit_predict([x for _, x in train], [float(r['net_return']) for r, _ in train],
                                                  [x for _, x in validation], cfg['ridge_penalty'])
                fitted[clock_year] = {'observations': len(train), 'fit': fit}
                for (r, _), prediction in zip(validation, predicted):
                    residuals[(r['issuer'], r['date'], r['role'])] = float(r['net_return']) - float(prediction)
            for year in [2023, 2024, 2025]:
                test = [q for q in qs if str(q[0].get('event_decision') or q[0]['date']).startswith(str(year)) and
                        all((r['issuer'], r['date'], r['role']) in residuals for r in [q[0], q[2]])]
                result = {'study': study['id'], 'shape': shape, 'year': year, 'variant': 'primary',
                    'training_observations': fitted.get(year, {}).get('observations', 0), 'pairs': len(test),
                    'issuers': len({q[0]['issuer'] for q in test}), 'residual_increment': None,
                    'status': 'insufficient_support', 'reason': 'earlier_fit_or_validation_floor',
                    'interpretation': 'conditional residual diagnostic; not full factor alpha',
                    'clock': 'each event and control predicted in its own calendar fold', 'fits': json.dumps(fitted)}
                if len(test) >= cfg['minimum_year_pairs'] and result['issuers'] >= cfg['minimum_year_issuers']:
                    differences = [residuals[(q[0]['issuer'], q[0]['date'], q[0]['role'])] -
                                   residuals[(q[2]['issuer'], q[2]['date'], q[2]['role'])] for q in test]
                    result.update(residual_increment=float(np.mean(differences)),
                                  status='completed_development_diagnostic', reason='')
                output.append(result)
    return output


def state_diagnostics(rows, cfg, specs, history=None):
    output = []
    frozen_bins = {}
    if history is not None:
        for year in [2023, 2024, 2025]:
            for feature in ['volatility', 'momentum']:
                prior = [(ticker, finite(values.get(feature))) for ticker, dates in history.items()
                         for day, values in dates.items() if day < f'{year}-01-01' and finite(values.get(feature)) is not None]
                enough = len(prior) >= cfg['minimum_pairs'] and len({ticker for ticker, _ in prior}) >= cfg['minimum_issuers']
                frozen_bins[(year, feature)] = (np.quantile([v for _, v in prior], [1 / 3, 2 / 3]).tolist() if enough else None, len(prior))
    for spec in specs:
        qs, _ = quartets(rows, cfg, spec)
        for year in [2023, 2024, 2025]:
            boundary = f'{year}-01-01'
            train = {}
            for row in rows:
                if row['study'] == spec.study and row['variant'] == 'primary' and row['shape'] == spec.shape and row['date'] < boundary:
                    train[(row['issuer'], row['date'])] = row
            validation = [q for q in qs if str(q[0].get('event_decision') or q[0]['date']).startswith(str(year))]
            for feature in ['volatility', 'momentum']:
                prior = [finite(r.get(feature)) for r in train.values() if finite(r.get(feature)) is not None]
                cutpoints = np.quantile(prior, [1 / 3, 2 / 3]).tolist() if len(prior) >= cfg['minimum_pairs'] else None
                count = len(prior)
                if history is not None:
                    cutpoints, count = frozen_bins[(year, feature)]
                for state in range(3):
                    selected = [q for q in validation if finite(q[0].get(feature)) is not None and cutpoints is not None and
                                int(np.searchsorted(cutpoints, float(q[0][feature]), side='right')) == state]
                    record = summarize_quartets(selected, [], cfg, spec, year=year)['summary']
                    record.update(diagnostic='earlier_fit_prior_state', state_feature=feature, state=state,
                                  cutpoints=json.dumps(cutpoints), training_observations=len(prior))
                    record.update(training_observations=count, bin_training_scope='frozen universe earlier market history' if history is not None else 'synthetic selected-observation fixture')
                    if cutpoints is None:
                        record.update(status='insufficient_support', reason='earlier_feature_history_floor')
                    output.append(record)
    return output


def common_shape_diagnostics(rows, cfg):
    output = []
    for study in cfg['studies']:
        qs = {}
        for shape in cfg['shapes']:
            spec = EffectSpec('', study['id'], shape, 'overlay_increment', 'ordinary', 0.)
            qs[shape] = {q[0]['pair_id']: q for q in quartets(rows, cfg, spec)[0]}
        common = sorted(set(qs['covered_call']) & set(qs['protective_put']))
        eligible = []
        for pair in common:
            call, put = qs['covered_call'][pair], qs['protective_put'][pair]
            if any((a['entry_date'], a.get('evaluation_date') or a['exit_date']) !=
                   (b['entry_date'], b.get('evaluation_date') or b['exit_date']) for a, b in zip(call, put)):
                continue
            eligible.append((call, put))
        for year in ['all', 2023, 2024, 2025]:
            selected = eligible if year == 'all' else [q for q in eligible if str(q[0][0]['event_decision']).startswith(str(year))]
            issuers = len({q[0][0]['issuer'] for q in selected})
            n = cfg['minimum_pairs'] if year == 'all' else cfg['minimum_year_pairs']
            ni = cfg['minimum_issuers'] if year == 'all' else cfg['minimum_year_issuers']
            values = [(float(c[0]['net_return']) - float(c[1]['net_return'])) -
                      (float(p[0]['net_return']) - float(p[1]['net_return'])) for c, p in selected]
            output.append({'study': study['id'], 'variant': 'primary', 'year': year, 'shape': 'common_call_put',
                'diagnostic': 'common_shape_event_overlay_difference', 'metric': 'call_overlay_minus_put_overlay',
                'pairs': len(selected), 'issuers': issuers, 'estimate': float(np.mean(values)) if values else None,
                'status': 'eligible_descriptive' if len(selected) >= n and issuers >= ni else 'insufficient_support',
                'reason': 'identical observations and clocks; supplemental comparison outside primary family'})
    return output


def calibration_gate(run, manifest, cfg):
    checked = verify_receipt(run, 'calibration', manifest['manifest_id'])
    if checked is None:
        return {'status': 'pending', 'reason': 'separate_scheduled_calibration_not_returned'}
    result = read_json(Path(run) / 'results/calibration/summary.json')
    receipted_file(run, checked, Path(run) / 'results/calibration/summary.json')
    if (result.get('datasets') != cfg['synthetic_null_replicas'] or result.get('draws_per_dataset') != cfg['resamples'] or
            result.get('declared_family_size') != cfg['primary_family_size'] or
            sorted(x['block'] for x in result.get('blocks', [])) != sorted(cfg['blocks'])):
        raise ValueError('Calibration receipt is not the registered complete experiment')
    checkpoints = []
    for replica in range(cfg['synthetic_null_replicas']):
        path = Path(run) / 'results/calibration' / f'dataset-{replica:03d}.json'
        receipted_file(run, checked, path); checkpoint = read_json(path)
        if (checkpoint.get('manifest_id') != manifest['manifest_id'] or checkpoint.get('replica') != replica or
                checkpoint.get('seed') != cfg['seed'] + 900000 + replica or checkpoint.get('draws') != cfg['resamples'] or
                checkpoint.get('checkpoint_id') != identity({k: v for k, v in checkpoint.items() if k != 'checkpoint_id'})):
            raise ValueError('Calibration dataset checkpoint identity differs')
        checkpoints.append(checkpoint)
    for evidence in result['blocks']:
        block = evidence['block']
        actual = [next((x for x in row['blocks'] if x['block'] == block), None) for row in checkpoints]
        if any(x is None for x in actual):
            raise ValueError('Calibration dataset lacks a registered block')
        complete_rows = [x for x in actual if x['status'] == 'completed']
        rejected = sum(bool(x['rejected']) for x in complete_rows)
        if evidence.get('completed') != len(complete_rows) or evidence.get('false_rejections') != rejected:
            raise ValueError('Calibration summary does not reconcile with its datasets')
        passed = len(complete_rows) == cfg['synthetic_null_replicas'] and rejected <= cfg['synthetic_null_max_rejections']
        if (evidence['status'] == 'pass') != passed:
            raise ValueError('Calibration threshold verdict differs')
    if (result['status'] == 'pass') != all(x['status'] == 'pass' for x in result['blocks']):
        raise ValueError('Joint calibration verdict differs')
    return result


def placebo_evidence(run, manifest, cfg, observed):
    """Exact shifted-date artifacts only; never shuffle recorded profits.

    Future shifted acquisitions/tasks use root-manifest receipts named
    placebo-acquire-N and placebo-task-N-STUDY. Their acquisition source is
    complete and hashed against that replica's recomputed anchors. A missing
    source or task is a pending planned replicate, without replacement draws.
    """
    maps = read_json(Path(run) / 'prepared/placebo-map.json')
    if len(maps) != cfg['timing_placebos'] or len({x['replica'] for x in maps}) != len(maps):
        raise ValueError('Timing-placebo map count or identity differs')
    trials, estimates = [], []
    for plan in maps:
        rep = plan['replica']; folder = Path(run) / 'placebos' / str(rep)
        trial = {'replica': rep, 'status': 'pending', 'reason': 'exact_shifted_source_not_acquired',
                 'eligible_effects': 0}
        prepared = verify_receipt(run, f'placebo-prepare-{rep}', manifest['manifest_id'])
        acquired = verify_receipt(run, f'placebo-acquire-{rep}', manifest['manifest_id'])
        if not prepared or not acquired:
            trials.append(trial); continue
        source_path = folder / 'acquisition/source.json'; anchors = folder / 'prepared/anchors.json'
        if not source_path.exists() or not anchors.exists():
            raise ValueError('Placebo receipt lacks its source or recomputed anchors')
        receipted_file(run, acquired, source_path); receipted_file(run, prepared, anchors)
        map_path = folder / 'prepared/map.json'; receipted_file(run, prepared, map_path)
        if read_json(map_path) != plan:
            raise ValueError('Shifted timing map differs from frozen assignments')
        source = read_json(source_path)
        if source.get('complete') is not True or source.get('anchors_sha256') != digest(anchors):
            trial.update(status='unsupported', reason='incomplete_exact_shifted_source'); trials.append(trial); continue
        if source.get('source_id') != identity({k: v for k, v in source.items() if k != 'source_id'}):
            raise ValueError('Placebo source identity differs')
        for key, obj in source.get('objects', {}).items():
            object_path = safe_child(folder / 'acquisition/objects', str(key) + '.json')
            if digest(object_path) != obj['sha256']:
                raise ValueError('Exact shifted source member changed')
        shifted = []; missing = []
        for study in cfg['studies']:
            sid = study['id']; check = verify_receipt(run, f'placebo-task-{rep}-{sid}', manifest['manifest_id'])
            path = folder / 'results' / sid / 'trades.csv'
            if not check or not path.exists():
                missing.append(sid)
            else:
                receipted_file(run, check, path)
                shifted.extend(records(path))
        if missing:
            trial.update(reason='missing_verified_shifted_tasks:' + ','.join(missing)); trials.append(trial); continue
        shifted_index = OutcomeIndex(shifted)
        effects = [effect(shifted_index, cfg, spec) for spec in family(cfg)]
        trial['eligible_effects'] = sum(item['summary']['support'] for item in effects)
        trial.update(status='completed' if trial['eligible_effects'] == len(effects) else 'unsupported',
                     reason='' if trial['eligible_effects'] == len(effects) else 'shifted_match_or_support_missing')
        estimates.extend({'replica': rep, **item['summary']} for item in effects)
        trials.append(trial)
    complete_count = sum(row['status'] == 'completed' for row in trials)
    comparisons = []
    for item in observed:
        summary = item['summary']
        usable = [row for row in estimates if row['effect_id'] == summary['effect_id'] and row['support']]
        full = len(usable) == cfg['timing_placebos'] and summary['support']
        comparisons.append({'effect_id': summary['effect_id'], 'study': summary['study'], 'replicas': len(usable),
            'observed': summary['estimate'], 'status': 'completed_development_placebo' if full else 'pending',
            'placebo_tail_fraction': (1 + sum(row['estimate'] >= summary['estimate'] for row in usable)) /
                                     (len(usable) + 1) if full else None})
    return {'status': 'completed_development_placebo' if complete_count == cfg['timing_placebos'] else 'pending',
            'planned': len(maps), 'completed': complete_count, 'unsupported': sum(r['status'] == 'unsupported' for r in trials),
            'scope': 'calendar-wide issuer/year bundled timing shifts; not H21 atlas placebos',
            'trials': trials, 'effects': comparisons, 'estimates': estimates}


def robustness_diagnostics(rows, cfg, specs):
    result = []
    variants = [v['id'] for v in cfg['variants']]
    for spec in specs:
        for variant in variants:
            for year in ['all', 2023, 2024, 2025]:
                item = effect(rows, cfg, spec, variant, cfg['primary_horizon'], None if year == 'all' else year)
                result.append({**item['summary'], 'diagnostic': 'registered_setting_or_year', 'omitted_issuer': ''})
        issuers = sorted({r['issuer'] for r in rows if r['study'] == spec.study and r['variant'] == 'primary'})
        for issuer in issuers:
            item = effect(rows, cfg, spec, omit_issuer=issuer)
            result.append({**item['summary'], 'diagnostic': 'leave_one_issuer_out', 'omitted_issuer': issuer})
    return result


def validation_checks(manifest, tasks, rows, cfg, calibration_result, placebos, predictions, attribution, states):
    """Executed diagnostics and scientific success are separate fields."""
    complete_tasks = sum(t['status'] == 'completed' for t in tasks)
    quote_rows = [r for r in rows if r.get('quote_status') == 'completed_bounded_proxy' and not truth(r['stock_only'])]
    return [
        {'id': 'S01', 'status': 'implemented_assumed_clock', 'reason': 'filing+1 alignment; delayed decision; next-close fill; aligned unit counterfactuals'},
        {'id': 'S02', 'status': 'pending_fresh_confirmation', 'reason': '2022–2025 development and exposed 2026 are not fresh final tests'},
        {'id': 'S03', 'status': 'completed_diagnostic' if any(r['status'] == 'completed_development_diagnostic' for r in predictions) else 'insufficient_support', 'reason': 'prior-year purged ridge10 signed/absolute stock outcomes; no trading optimization'},
        {'id': 'S04', 'status': 'completed_diagnostic' if any(r['support'] for r in states) else 'insufficient_support', 'reason': 'earlier-history prior-volatility/momentum terciles; registered horizons/settings, sparse and expired cells retained'},
        {'id': 'S05', 'status': 'partial', 'reason': 'paired stock-only, zero-interest cash and matched ordinary comparisons; risk-matched SPY and prior-momentum funded benchmarks pending'},
        {'id': 'S06', 'status': 'completed_descriptive', 'reason': 'fixed stock-overlay/component contrasts and earlier-fit label addition; support shown per cell'},
        {'id': 'S07', 'status': 'completed_diagnostic' if any(r['status'] == 'completed_development_diagnostic' for r in attribution) else 'insufficient_support', 'reason': 'earlier-fit Massive market/option conditional return residuals; no full-factor-alpha claim'},
        {'id': 'S08', 'status': 'completed_development_inference' if calibration_result['status'] == 'pass' else 'pending_or_failed_calibration', 'reason': '19 declared effects, joint9999 two-block draws, simultaneous bounds and stepdown; calibration:' + calibration_result['status']},
        {'id': 'S09', 'status': placebos['status'], 'reason': f"{placebos['completed']}/{cfg['timing_placebos']} exact shifted-source timing replicas complete"},
        {'id': 'S10', 'status': 'completed_diagnostic', 'reason': 'fixed variants/year/issuer omissions, earlier-fit states and common-shape intersection; no favorable variant selected; unsupported cells visible'},
        {'id': 'S11', 'status': 'partial_executable_evidence' if quote_rows else 'pending_executable_evidence', 'reason': f'{len(quote_rows)} bounded quote-proxy strategy outcomes; daily-close fills and assignment assumptions are not execution proof'},
        {'id': 'S12', 'status': 'verified_outputs_partial_research' if complete_tasks < 33 else 'verified_development_outputs', 'reason': f'{complete_tasks}/{len(tasks)} scoped tasks verified; full plan33; scheduler/import verification belongs to immutable transfer receipts'},
    ]


def archive_analysis(run, dependency_id):
    """Preserve an older valid report when later scheduled stages return."""
    path = Path(run) / 'receipts/analysis.json'
    if not path.exists():
        return
    old = read_json(path)
    if old.get('dependency_id') == dependency_id:
        return
    folder = Path(run) / 'results/analysis-history' / (old.get('dependency_id') or identity(old))
    folder.mkdir(parents=True, exist_ok=True)
    for relative, expected in old.get('files', {}).items():
        original = safe_child(run, relative)
        if digest(original) != expected:
            raise ValueError('Prior analysis output changed; refusing silent overwrite')
        destination = safe_child(folder, relative)
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(original, destination)
    shutil.copyfile(path, folder / 'analysis-receipt.json')


def analyze(run):
    scheduled(); run = Path(run); manifest = verify_manifest(run); cfg = read_json(CONFIG)
    rows, nav, tasks = load_tasks(run, manifest)
    cal = calibration_gate(run, manifest, cfg)
    dependencies = {'manifest_id': manifest['manifest_id'], 'tasks': [
        {'task': t['task'], 'receipt': digest(run / 'receipts' / f"task-{t['task']}.json") if t['status'] == 'completed' else None}
        for t in tasks], 'calibration': digest(run / 'receipts/calibration.json') if cal['status'] != 'pending' else None,
        'placebos': {p.name: digest(p) for p in sorted((run / 'receipts').glob('placebo-*.json'))}}
    dependency_id = identity(dependencies)
    old = verify_receipt(run, 'analysis', manifest['manifest_id'])
    if old and old.get('dependency_id') == dependency_id:
        return read_json(run / 'results/joint/summary.json')
    archive_analysis(run, dependency_id)
    specs = family(cfg); indexed = OutcomeIndex(rows); primary = [effect(indexed, cfg, spec) for spec in specs]
    dates = read_json(run / 'prepared/calendar.json')['dates']
    joint = run / 'results/joint'; joint.mkdir(parents=True, exist_ok=True); inference = []
    for block in cfg['blocks']:
        sampled = joint_draws(primary, dates, block, cfg['resamples'], cfg['seed'] + block)
        np.save(joint / f'centered-draws-{block}.npy', sampled, allow_pickle=False)
        block_rows = simultaneous(primary, sampled, block)
        for row in block_rows:
            row['calibration_status'] = cal['status']
            row['inferential_use'] = 'development_only' if cal['status'] == 'pass' else 'suppressed_pending_or_failed_calibration'
            row['clears_practical_bound'] = (cal['status'] == 'pass' and row['lower'] is not None and row['lower'] > row['threshold'])
            if cal['status'] != 'pass' and row['status'] == 'approximate_inference':
                row['status'] = 'unvalidated_approximate_inference'
        inference.extend(block_rows)
    placebo = placebo_evidence(run, manifest, cfg, primary)
    predictions = prediction_diagnostics(indexed, cfg)
    attribution = attribution_diagnostics(indexed, cfg)
    feature_path = run / 'prepared/features.json'
    states = state_diagnostics(indexed, cfg, specs, read_json(feature_path) if feature_path.exists() else {})
    robustness = robustness_diagnostics(indexed, cfg, specs) + states + common_shape_diagnostics(indexed, cfg)
    performance = nav_performance(nav, cfg, tasks, dates)
    checks = validation_checks(manifest, tasks, rows, cfg, cal, placebo, predictions, attribution, states)
    baseline = []
    quote_index = OutcomeIndex([{**row, 'net_return': row.get('quote_net_return'),
        'status': 'completed' if row.get('quote_status') == 'completed_bounded_proxy' else 'unsupported',
        'path_complete': row.get('quote_path_complete', False), 'downside_loss': row.get('quote_downside_loss')}
        for row in rows])
    quoted = [effect(quote_index, cfg, spec)['summary'] for spec in specs]
    for spec in specs:
        for horizon in [*cfg['horizons'], 'expiry']:
            for year in ['all', 2023, 2024, 2025]:
                baseline.append(effect(indexed, cfg, spec, horizon=horizon, year=None if year == 'all' else year)['summary'])
    csv_write(joint / 'primary_family.csv', inference)
    csv_write(joint / 'timing_placebo_trials.csv', placebo['trials'])
    csv_write(joint / 'timing_placebo_estimates.csv', placebo['estimates'])
    csv_write(joint / 'timing_placebo_comparison.csv', placebo['effects'])
    csv_write(joint / 'task_status.csv', [{k: v for k, v in t.items() if k != 'details'} for t in tasks])
    write_json(joint / 'calibration_gate.json', cal)
    write_json(joint / 'dependencies.json', dependencies)
    for study in cfg['studies']:
        sid = study['id']; directory = run / 'results' / sid; directory.mkdir(parents=True, exist_ok=True)
        relevant = [row for row in primary if row['summary']['study'] == sid]
        study_tasks = [t for t in tasks if t['study'] == sid]
        summary = {'study': sid, 'phase': manifest.get('phase'), 'scope': manifest.get('scope', 'full'),
            'verdict': 'UNSUPPORTED_FOR_CONFIRMATORY_CLAIM', 'registration_commit': REGISTRATION,
            'observed_tasks': sum(t['status'] == 'completed' for t in study_tasks), 'planned_tasks': 11,
            'coverage_status': 'priced_subset_conditional; full primary-label cohort preserved in prepared/coverage.csv',
            'primary_effects': [row['summary'] for row in relevant],
            'block_inference_status': 'development_only' if cal['status'] == 'pass' else 'suppressed_' + cal['status'],
            'calibration_status': cal['status'], 'placebo_status': placebo['status'],
            'executable_evidence_status': next(r['status'] for r in checks if r['id'] == 'S11'),
            'fresh_oos_status': 'unavailable', 'manifest_id': manifest['manifest_id'], 'dependency_id': dependency_id,
            'primary_label_coverage': [r for r in records(run / 'prepared/coverage.csv') if r.get('study') == sid],
            'limitations': ['Static-universe survivorship.', 'Assumed label availability does not establish service delivery time.',
                'Historical prices and daily-close fills are assumed models; quotes are bounded proxies.',
                'Option-eligible matched observations are a conditional subset, not the full filing cohort.',
                'Earlier adaptive searches remain exposed; this family adjustment does not erase them.',
                'All development years and the previously inspected 2026 window cannot provide fresh confirmation.',
                'Incomplete calibration, exact-source timing searches and mandatory checks block advancement.']}
        csv_write(directory / 'performance.csv', [r for r in performance if r['study'] == sid])
        csv_write(directory / 'coverage.csv', summary['primary_label_coverage'])
        csv_write(directory / 'baseline_comparison.csv', [r for r in baseline if r['study'] == sid])
        csv_write(directory / 'quote_baseline_comparison.csv', [r for r in quoted if r['study'] == sid])
        csv_write(directory / 'robustness.csv', [r for r in robustness if r['study'] == sid])
        csv_write(directory / 'signal_diagnostics.csv', [r for r in predictions if r['study'] == sid])
        csv_write(directory / 'attribution.csv', [r for r in attribution if r['study'] == sid])
        write_json(directory / 'validation_checks.json', {'study': sid, 'checks': checks, 'fresh_final_oos_available': False})
        write_json(directory / 'summary.json', summary)
        lines = [f'# {sid}: registered financing development results', '',
                 'Verdict: **UNSUPPORTED_FOR_CONFIRMATORY_CLAIM**. No net-alpha or fresh-confirmation claim.', '',
                 f"Verified tasks: {summary['observed_tasks']}/11 full-plan tasks; scope: {summary['scope']}.",
                 f"Calibration: {cal['status']}. Exact timing placebos: {placebo['completed']}/{placebo['planned']}.", '',
                 'All nineteen registered effects remain in the joint family, including insufficient-support cells.',
                 'Complete-return and complete-path priced cohorts differ; no missing outcome becomes zero.', '']
        for item in relevant:
            r = item['summary']; estimate = 'unknown' if r['estimate'] is None else f"{r['estimate']:.6f}"
            lines.append(f"- {r['effect_id']}: estimate {estimate}, {r['pairs']} pairs/{r['issuers']} issuers; {r['status']}.")
        lines += ['', *summary['limitations']]
        (directory / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    summary = {'manifest_id': manifest['manifest_id'], 'dependency_id': dependency_id,
        'scope': manifest.get('scope', 'full'), 'planned_full_tasks': 33, 'scoped_tasks': len(tasks),
        'completed_tasks': sum(t['status'] == 'completed' for t in tasks), 'primary_family_size': len(specs),
        'draws_per_block': cfg['resamples'], 'blocks': cfg['blocks'], 'calibration_status': cal['status'],
        'timing_placebos_planned': placebo['planned'], 'timing_placebos_completed': placebo['completed'],
        'fresh_final_oos_available': False, 'verdict': 'UNSUPPORTED_FOR_CONFIRMATORY_CLAIM'}
    write_json(joint / 'summary.json', summary)
    files = list(joint.glob('*')) + [p for study in cfg['studies'] for p in (run / 'results' / study['id']).glob('*')]
    receipt(run, 'analysis', [p for p in files if p.is_file()], {'dependency_id': dependency_id, 'research_complete': False})
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['analyze', 'calibration'])
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(globals()[args.stage](args.run), sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
