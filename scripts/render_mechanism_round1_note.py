"""Typeset verified returned evidence; never fit a model or replay a portfolio.

Run after both phase returns are verified. Requires ReportLab for presentation
only. The frozen scientific runners and their dependency lock are unchanged.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Line, String, PolyLine


ROOT = Path(__file__).resolve().parents[1]
RUNS = {'IS': 'development-v3', 'OOS': 'final-oos-v2'}
STUDIES = ['H18', 'H19', 'H20']
PALETTE = {'H18': colors.HexColor('#215E9C'), 'H19': colors.HexColor('#BA5225'),
           'H20': colors.HexColor('#237660'), 'cash': colors.HexColor('#666666')}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metric(data, baseline='registered_shape', multiplier='1'):
    matches = [r for r in data if r['baseline'] == baseline and r['delay'] == '0'
               and r['cost_multiplier'] == multiplier]
    if len(matches) != 1:
        raise ValueError('Missing or duplicate headline metric')
    return matches[0]


def pct(value, digits=3):
    return f'{100*float(value):.{digits}f}%' if value not in ['', None] else 'N/A'


def num(value):
    return f'{float(value):.3f}' if value not in ['', None] else 'N/A'


def load(root):
    data = {}
    for phase, run_name in RUNS.items():
        run = root/'data/cache/massive-mechanisms/runs'/run_name
        manifest = read(run/'manifest.json')
        returned = read(run/'return-verification.json')
        observed = read(run/'completion-observation.json')
        if observed['verified_return_sha256'] != returned['archive_sha256'] or any(r[1:3] != ['COMPLETED','0:0'] for r in observed['actual_jobs'].values()):
            raise ValueError('Terminal setup/core/report/return observation required')
        if returned['manifest_id'] != manifest['manifest_id'] or not read(run/'aggregate.json')['all_tasks_complete']:
            raise ValueError('Verified complete phase required')
        accounting = (run/'scheduler/scheduler-accounting.txt').read_text()
        ids = dict(token.split('=', 1) for token in (run/'scheduler/submission-ids.txt').read_text().split() if '=' in token)
        required = [ids['setup'], ids['report'], *[ids['core']+'_'+str(i) for i in range(3)]]
        for jid in required:
            records = [r.split('|') for r in accounting.splitlines() if r.split('|')[0] == jid]
            if len(records) != 1 or records[0][2:4] != ['COMPLETED', '0:0']:
                raise ValueError('Actual scheduler proof missing: '+jid)
        for study in STUDIES:
            task = run/'tasks'/study
            completion = read(task/'completion.json')
            if any(hash_file(task/name) != digest for name, digest in completion['files'].items()):
                raise ValueError('Returned task content changed')
            data[phase, study] = {'findings': read(task/'findings.json'),
                                  'metrics': rows(task/'metrics.csv'),
                                  'curves': [r for r in rows(task/'equity_curves.csv') if r['delay']=='0' and r['cost_multiplier']=='1'],
                                  'validation_checks': read(task/'validation_checks.json'),
                                  'completion_files': completion['files'],
                                  'return_sha256': returned['archive_sha256'],
                                  'submission_ids': (run/'scheduler/submission-ids.txt').read_text().strip(),
                                  'scheduler_accounting': accounting,
                                  'terminal_observation': observed,
                                  'manifest': {k: manifest[k] for k in ['manifest_id','registration_commit','phase','code_commit','window','config_sha256','code_files','freeze_sha256']}}
    return data


def curve(drawing, data, phase, origin_y, excess=False):
    """Draw the returned daily NAV, or a display transform relative to cash."""
    left, bottom, width, height = 55, origin_y, 397, 90
    series = {}
    cash_rows = [r for r in data[phase, 'H18']['curves'] if r['baseline'] == 'cash'
                 and r['delay'] == '0' and r['cost_multiplier'] == '1']
    cash = {r['date']: float(r['nav']) for r in cash_rows if r.get('nav') and math.isfinite(float(r['nav']))}
    for study in STUDIES:
        selected = [r for r in data[phase, study]['curves'] if r['baseline'] == 'registered_shape'
                    and r['delay'] == '0' and r['cost_multiplier'] == '1']
        series[study] = []
        for r in selected:
            valid = bool(r.get('nav')) and math.isfinite(float(r['nav'])) and (not excess or r['date'] in cash)
            value = (10000*(float(r['nav'])/cash[r['date']]-1) if excess else float(r['nav'])/1e6) if valid else None
            series[study].append((date.fromisoformat(r['date']).toordinal(), value))
    if not excess:
        series['cash'] = [(date.fromisoformat(day).toordinal(), value/1e6) for day, value in cash.items()]
    points = [point for values in series.values() for point in values if point[1] is not None]
    x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
    y0, y1 = min(p[1] for p in points), max(p[1] for p in points)
    padding = max((y1-y0)*0.1, 0.001 if not excess else 0.05)
    y0 -= padding; y1 += padding
    sx = lambda x: left+(x-x0)/(x1-x0)*width
    sy = lambda y: bottom+(y-y0)/(y1-y0)*height
    title = ('Development 2024-2025' if phase == 'IS' else 'Corrective final 2026') + (' | relative to cash, bp' if excess else ' | NAV / $1 million')
    drawing.add(String(left, bottom+height+14, title, fontName='Times-Bold', fontSize=11))
    for fraction in [0, .5, 1]:
        value = y0+(y1-y0)*fraction; y=sy(value)
        drawing.add(Line(left, y, left+width, y, strokeColor=colors.HexColor('#DDDDDD'), strokeWidth=.4))
        drawing.add(String(left-6, y-3, f'{value:.2f}' if excess else f'{value:.3f}',
                           textAnchor='end', fontName='Times-Roman', fontSize=11))
    for key, values in series.items():
        segments = [[]]
        for x, y in values:
            if y is None:
                segments.append([])
            else:
                segments[-1].extend((sx(x), sy(y)))
        for flat in segments:
            if len(flat) >= 4:
                drawing.add(PolyLine(flat, strokeColor=PALETTE[key], strokeWidth=1.1 if key != 'cash' else 1.8))
    for x, anchor in [(x0, 'start'), (x1, 'end')]:
        drawing.add(String(sx(x), bottom-15, date.fromordinal(x).isoformat(), textAnchor=anchor,
                           fontName='Times-Roman', fontSize=11))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=ROOT/'output/pdf/massive-mechanisms-round1.pdf')
    parser.add_argument('--evidence', type=Path, help='Regenerate from the retained derived-evidence snapshot, without raw data or scientific execution')
    args = parser.parse_args(); root=args.root.resolve()
    if args.evidence:
        expected = args.evidence.with_suffix('.sha256').read_text().split()[0]
        if hash_file(args.evidence) != expected:
            raise ValueError('Derived evidence snapshot hash differs')
        snapshot = read(args.evidence)
        data = {(phase,study): snapshot['phases'][phase][study] for phase in RUNS for study in STUDIES}
        ledger_count = snapshot['repository_ledger_records']
    else:
        data = load(root)
        ledger_count = len(rows(root/'Hypotheses/EXPERIMENTS.csv'))
        snapshot = {'schema':1, 'description':'Selected derived results from whole/member-verified HiPerGator returns; no raw provider responses or credentials.',
                    'repository_ledger_records':ledger_count, 'runs':RUNS,
                    'phases':{phase:{study:data[phase,study] for study in STUDIES} for phase in RUNS}}
        evidence = root/'docs/massive/mechanism-round1-evidence.json'
        evidence.write_text(json.dumps(snapshot,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        evidence.with_suffix('.sha256').write_text(hash_file(evidence)+'  '+evidence.name+'\n',encoding='utf-8')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    styles = {'body': ParagraphStyle('body', fontName='Times-Roman', fontSize=11, leading=14, spaceAfter=7),
              'heading': ParagraphStyle('heading', fontName='Times-Bold', fontSize=13, leading=16, spaceBefore=8, spaceAfter=8),
              'title': ParagraphStyle('title', fontName='Times-Bold', fontSize=18, leading=21, spaceAfter=10),
              'cell': ParagraphStyle('cell', fontName='Times-Roman', fontSize=11, leading=12, alignment=TA_LEFT)}
    flow = []
    def para(text): flow.append(Paragraph(text, styles['body']))
    def heading(text): flow.append(Paragraph(text, styles['heading']))
    def table(matrix, widths):
        t=Table([[Paragraph(str(c),styles['cell']) for c in r] for r in matrix],colWidths=widths,repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EAF0F5')),
                              ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.grey),
                              ('LINEBELOW',(0,1),(-1,-1),.3,colors.lightgrey),
                              ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
                              ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        flow.append(t);flow.append(Spacer(1,8))
    totals={phase:sum(data[phase,s]['findings']['scientific_trials'] for s in STUDIES) for phase in RUNS}
    flow.append(Paragraph('Leadership disclosures and option risk',styles['title']))
    para('H18-H20 | Massive track | Registered round 1 | Evidence reviewed October 3, 2026')
    heading('01 - Summary')
    para('All three studies are <b>INCONCLUSIVE</b>. They examine CEO-departure uncertainty resolution, concentration of leadership risk, and verified incoming-CFO compensation context. Sparse matched samples, incomplete executable comparisons and unknown historical delivery/assignment facts prevent a supported incremental-signal claim. Funded returns mainly reflect the declared cash yield. The first final H18/H19 jobs failed on an empty-comparison schema; H20 completed. A documented guard repair was tested on unchanged development outputs before a <b>corrective final replay after exposure</b>. Both attempts are retained; this is not an untouched replication.')
    heading('02 - Economic Hypothesis')
    para('<b>H18:</b> confirmation of a CEO departure may settle leadership uncertainty, so same-contract call-plus-put premium should compress unusually over five feasible sessions after conditional disclosure availability, controlling price movement and elapsed maturity. Protection buyers and liquidity providers are the proposed counterparties. A covered call is the permitted expression. Different attention to headline and remaining risk may sustain repeated episodes. Ordinary decay, a pre-availability response, or price exposure explaining the effect counts against it.')
    para('<b>H19:</b> investors may resolve transition concerns unevenly, concentrating downside in the first five sessions relative to the next five. Insurance buyers accept a put premium while information is assessed. Paid protection should reduce worst-decile loss without excessive drag. Each transition creates a new assessment problem, so the pattern could recur. Ordinary-day protection, delayed-entry disappearance or dispersed subsequent risk weakens the mechanism.')
    para('<b>H20:</b> explicit terms for the incoming CFO may accompany a more specified transition and lower subsequent risk. Protection demand can compensate a fully collateralized put seller. Verified terms must distinguish five-session risk and net return from verified complete-filing absence. Coarse labels may receive attention before contract details, allowing a recurring information gap. A co-tag about another executive cannot establish this mechanism. Counterparty behavior and persistence are hypotheses, not observed participant facts.')
    heading('03 - Data & Universe')
    para('The static sponsor universe contains 100 tickers; historical membership and delistings are unavailable. Sources are Massive 8-K categories/context, standard historical contracts, unadjusted daily option bars and backward timestamped quotes [1-4]. Development is 2024-2025. Final filings are January-August 2026, outcomes through October 2. The Massive-specific window overrides the generic track template. XNYS sessions and early closes use America/New_York. Approximate American-option parity supplies a price proxy, not observed shares or IV. Final first access was October 3 at 21:09:22 UTC, after the verified development freeze.')
    flow.append(PageBreak())
    heading('04 - Methodology')
    para('Economic registration 7688ad1d96303039d6e61ef2dcc6f19f21764a15 predates new code/data. It follows earlier adaptive discovery, which remains disclosed. Conditional availability is the first session close on/after filing date plus one calendar day. After that close, select standard multiplier-100 paired contracts from the nearest eligible expiry to 120 days, with 5% OTM overlay. Selection uses completed decision-session bars only. Place orders at the next open plus two minutes. Additional 1/3-session delays and 30/60/120-day, 3/5/10% grids were fixed beforehand.')
    para('Funded synthetic long is long ATM call, short ATM put and strike cash. H18 additionally sells an upper call; H19 buys a lower put; H20 sells a fully cash-secured lower put. Buy at ask, sell at bid; add $0.65 per contract per side and one premium basis point of assumed adverse slippage on every leg. Require backward quotes no older than 60 seconds, leg timestamps within 60 seconds, positive uncrossed prices, spread at most 20%, size at least one and prior five-session each-leg average volume at least 100. Double half-spread, fees and slippage in stress. Full cash/reserves accrue the same 4% calendar-day rate used in parity. Impact is uncalibrated; dividend/assignment validity is unknown.')
    para('The primary portfolio exits at filing-session offset 5 using close-minus-five-minute quotes. All mandated offsets 1, 2, 3, 5, 10, 21, 42, 63 and expiry retain missing reasons. The mechanism window is separately entry through entry+5; H19 additionally uses entry+6 through entry+10. Ordinary anchors are 84 sessions earlier within the same phase, excluding nearby selected events only when the complete +/-30-calendar-day history interval is known. No missing control is replaced from another phase.')
    para('H18 estimates abnormal paired log-premium compression with price/decay/entry-uncertainty controls. H19 estimates paired early-minus-late normalized downside. H20 requires incoming-person text and a verified complete-filing absence group before RMS regression or the filtered put program. Complete observations determine inference, with at least 12 events, 8 issuers and 2 observations per parameter; H20 also needs 8 events/3 issuers per group. Missing support is inconclusive.')
    para('The six primary comparisons use 9,999 deterministic issuer-cluster draws and 99.1667% family-adjusted intervals, when support permits. Retain duplicate cluster multiplicity, issuer-equal/removal checks and 63-session date blocks (4 minimum for strong replication). Secondary 999-draw intervals are nonconfirmatory. Three chronological folds use training ends June 2024, December 2024 and June 2025 with subsequent six-month validation, actual-target maturity purge, training-only scaling and fixed Ridge alpha 10. Models were frozen before final access; unsupported development models stay unsupported in final evaluation.')
    para(f'The corrected runs retain {totals["IS"]} development and {totals["OOS"]} final cells. Earlier records retain 531 development cells, 182 completed H20 final cells, two failed final tasks and three affected-study setup records. The repository ledger has {ledger_count} records including prior discovery; granularity varies. Replays are repeated cells. Repair plan 7d66cae preceded guard 88bda53; formulas/rules stayed fixed. Only HiPerGator jobs performed fits/replays. Method files record S04/S05/S10 executed, S03/S08 inconclusive, and S01/S02/S06/S07/S09/S11/S12 pending [5-7]. Later verified return/reproduction receipts supplement these frozen statuses.')
    flow.append(PageBreak())
    heading('05 - Results')
    para('Each phase starts independently with $1 million. IS denotes corrected development; OOS denotes the final corrective replay after exposure. These are base-cost, zero-extra-delay metrics. Geometric annualized return, sample volatility and excess Sharpe use 252 sessions; drawdown is a positive loss magnitude. Premium turnover sums traded option-premium value divided by NAV; reserve turnover is separate in the companion table.')
    matrix=[['Study /<br/>phase','Return','Vol.','Sharpe','Max DD','Trades','Premium<br/>turnover']]
    headline=[]
    for study in STUDIES:
        for phase in RUNS:
            m=metric(data[phase,study]['metrics'])
            matrix.append([f'{study} {phase}',pct(m['annualized_return']),pct(m['annualized_volatility']),num(m['sharpe']),pct(abs(float(m['maximum_drawdown'])) if m['maximum_drawdown'] else None),m['trades'],pct(m['premium_turnover'])])
            f=data[phase,study]['findings'];mech=f['mechanism'];trade=f['trade']
            headline.append({'study':study,'phase':phase,'mechanism_observations':mech.get('observations'),
                             'mechanism_issuers':mech.get('issuers'),'mechanism_status':mech['status'],
                             'mechanism_reason':mech.get('reason'),'mechanism_estimate':mech.get('estimate'),
                             'mechanism_ci_low':mech.get('ci_low'),'mechanism_ci_high':mech.get('ci_high'),
                             'trade_observations':trade.get('observations'),'trade_status':trade['status'],
                             'trade_reason':trade.get('reason'),'trade_estimate':trade.get('estimate'),
                             'trade_ci_low':trade.get('ci_low'),'trade_ci_high':trade.get('ci_high'),
                             'verdict':f['verdict'],'trial_cells':f['scientific_trials'],**m})
            for group in ['verified_incoming_cfo_terms','verified_absence_in_complete_filing']:
                for count in ['events','issuers']:
                    headline[-1][group+'_'+count] = f.get('groups',{}).get(group,{}).get(count)
    table(matrix,[77,66,61,52,62,50,100])
    cash=metric(data['OOS','H18']['metrics'],'cash')
    para(f'IS cash returned 4.0948% annually; final cash returned {pct(cash["annualized_return"])}. All three primary final portfolios executed zero trades and equal cash; their positive return is interest, with undefined excess Sharpe. IS has 502 sessions (January 2, 2024-December 31, 2025); final has 189 (January 2-October 2, 2026). Irregular calendar-day accrual creates cash-return variation. Sparse IS holdings and failed scheduled exits cannot replace complete filing-offset-5 comparisons.')
    support=[['Study','IS primary support','OOS primary support','Verdict']]
    for study in STUDIES:
        counts=[]
        for phase in RUNS:
            f=data[phase,study]['findings'];m=f['mechanism']
            if study=='H20':
                g=f['groups'];counts.append(f'Terms {g["verified_incoming_cfo_terms"]["events"]}; absence {g["verified_absence_in_complete_filing"]["events"]}')
            else:counts.append(f'{m.get("observations",0)} observations / {m.get("issuers",0)} issuers')
        support.append([study,*counts,'Inconclusive'])
    table(support,[43,152,152,121])
    para('Insufficient support is neither evidence of no effect nor a supported opposite direction. Full primary intervals are absent where support fails; no zero estimate or narrow interval is substituted. Cash, same-contract long, ordinary shape and own-price momentum controls are retained. Broad market/sector/value attribution is incomplete. Conditional estimates cannot override historical vendor-clock, dividend or assignment gaps.')
    flow.append(PageBreak())
    heading('05 - Results, continued: measured curves and stress')
    para('The two panels show returned NAV divided by starting capital. H18 is blue, H19 orange, H20 green, cash gray; nearly overlapping lines reflect mostly idle collateral. The phase boundary separates development from the final corrective replay. Each starts with $1 million; the two series are not compounded together.')
    drawing=Drawing(468,325)
    curve(drawing,data,'IS',200);curve(drawing,data,'OOS',35)
    flow.append(drawing)
    stress=[['Study','IS base / double return','OOS base / double return']]
    for study in STUDIES:
        values=[]
        for phase in RUNS:
            values.append(pct(metric(data[phase,study]['metrics'])['annualized_return'])+' / '+pct(metric(data[phase,study]['metrics'],multiplier='2')['annualized_return']))
        stress.append([study,*values])
    table(stress,[48,210,210])
    para('Full curves, delayed-entry results, nearby maturity/strike mark scenarios, yearly and prior shock/quiet diagnostics are retained. Sparse matched observations and failed rank/fold support prevent strong replication or learned forecast claims. Unfilled scheduled exits stay in the position ledger and retry at feasible retained quotes; eventual closed-trade counts do not repair a missing scheduled-horizon comparison.')
    flow.append(PageBreak())
    heading('06 - Risk Management')
    para('Each intended standard-contract unit reserves its full strike cash and must stay below 5% of NAV per name. Gross reserved exposure is at most 40%; all unverified sectors share one conservative 20% bucket. One open position per issuer and deterministic filing/CIK/accession/ticker ordering prevent outcome-based allocation. No leverage is used. Covered calls retain substantial underlying downside and cap gains; protective puts pay insurance; cash-secured puts expose nearly the reserved strike cash to a severe underlying decline. American assignment and corporate-action effects can differ from this modeled liquidation.')
    para('A 5% portfolio drawdown stops entries and requests liquidation at the next feasible retained quote. Re-entry needs 21 sessions, drawdown below 2% and fresh/integrity-clear marks. Missing quotes do not authorize fills. One-session mark carry is flagged; longer gaps make NAV/affected metrics undefined until resolution. The few traded units provide little evidence about crash or liquidity-freeze behavior. Broad factor/sector correlations remain unverified.')
    heading('07 - Liquidity & Capacity')
    para('Entry requires at least 100 contracts of each-leg prior average daily volume and displayed size at least one, so a one-contract unit uses at most 1% of that daily proxy. Snapshot size is not market depth or execution-window volume. Capacity files retain one-unit reserves and 0.5/1/2% prior-volume scenarios, each-leg quote constraints and an uncalibrated square-root impact coefficient 0.1, stressed to 0.2. Fees, spreads, synthetic legs and cash financing are explicit. No measured dollar capacity before edge erosion can be claimed because the incremental edge itself is unsupported.')
    heading('08 - Limitations & Next Steps')
    para('All three primary conclusions remain inconclusive. Historical membership, Massive label release clocks, first announcements, dividends, early assignment, complete CFO filings, broad exposure attribution and empirical impact remain incomplete. Approximate parity and asynchronous daily trades can distort uncertainty and returns. Matched timing does not identify causality. All failures are preserved. The guard repair followed final exposure; development numerical equality was verified before corrective replay. No threshold or selection rule was relaxed. A supported verdict requiring untouched final evidence cannot be supplied by this reused window.')
    para('A later experiment should first improve point-in-time event clocks, complete-person filing review and executable options coverage, then preregister a new development/holdout split. It should retain repeated announcements as distinct accessions while checking their dependence. This final window is now exposed and cannot serve as an untouched selection set for that new round. The organizer-controlled sealed interval was not accessed. Code, assumptions and this note agree on an inconclusive verdict; research completion does not guarantee alpha.')
    flow.append(PageBreak())
    heading('References and reproduction record (outside main five pages)')
    for text in [
        '[1] QuantHacks. Systematic Trading workflow and Massive track rules, reviewed October 3, 2026. https://www.gqhacks.com/tracks/systematic-trading and https://www.gqhacks.com/tracks/systematic-trading/massive',
        '[2] Massive. 8-K disclosure category/context endpoints. https://massive.com/docs/rest/alternative/overview. Downloaded locally October 3, 2026; exact query specifications and response hashes are retained privately.',
        '[3] Massive. Historical contract reference and daily aggregates. https://massive.com/docs/rest/options/contracts/all-contracts and https://massive.com/docs/rest/options/aggregates/custom-bars',
        '[4] Massive. Historical option quote timestamps, bid/ask and sizes. https://massive.com/docs/rest/options/quotes. SEC accession links in reviewed disclosure evidence establish text provenance; excerpt absence is not full-filing absence.',
        '[5] Backtrader. Offline feed/strategy organization and timing. https://www.backtrader.com/docu/order-creation-execution/order-creation-execution/. Webull starter entry organization was adapted; its broker P&L is not used. The Massive starter inspired parity/payoff conventions. The funded ledger and hypothesis-specific tests are local extensions.',
        '[6] Local registered protocol: docs/massive/mechanism-round1-plan.md; settings: config/mechanism-round1.json. Six-primary-family bootstrap, chronological fixed Ridge and S01-S12 evidence are documented with unknown gates retained.',
        '[7] Reproduction: install root Python 3.11 locked dependencies, use the documented acquisition/manifest/bundle workflow, verify transfer, then invoke the phase hpg/submit.sh once. See docs/massive/mechanism-run-guide.md. Licensed raw data and credentials stay private. Reproducing acquisition requires the appropriate Massive entitlement; a public repository alone cannot supply those licensed inputs.',
        'Code implementation 200cfe0309dcec2a46acd83e339fdfb3a3746c35; transfer repair 127e5db356b62f7313b49a3092a4fa5242726234; development evidence 6dedad4. The post-exposure repair plan 7d66cae preceded scientific guard 88bda53. The guard changes empty comparison handling only; nonempty formulas and all parameters remain fixed. See docs/massive/mechanism-round1-correction.md and the development equality receipt.',
        'Original development successful jobs: setup 44611122; core 44611123_0/1/2; report 44611124; return 44611125. Original final setup 44612650 completed; H18/H19 44612651_0/1 failed; H20 44612651_2 completed; report 44612652 and return 44612653 completed. The initial setup 44609020 failed before analysis and waiting dependents were cancelled.',
    ]:para(text)
    for phase in RUNS:
        para(('Corrected development' if phase=='IS' else 'Corrective final replay after exposure')+' jobs: '+data[phase,'H18']['submission_ids']+'. Actual setup/core/report accounting verifies COMPLETED 0:0 for every task.')
    para('Development return SHA-256: '+data['IS','H18']['return_sha256'])
    para('Final return SHA-256: '+data['OOS','H18']['return_sha256'])
    para('Original freeze SHA-256: ec5e6b0a7e27d1beeceb2cc25652f4ef3f3a185955473db3debaa75643f1afa9. Corrected freeze SHA-256: '+data['OOS','H18']['manifest']['freeze_sha256']+'. Both freezes, first exposure receipt, trial history and headline evidence are retained. The corrected freeze postdates exposure and cannot restore untouched status.')
    def footer(canvas, doc):
        canvas.setFont('Times-Roman',11);canvas.setFillColor(colors.HexColor('#555555'))
        canvas.drawString(72,44,'Massive mechanisms | October 3, 2026')
        canvas.drawRightString(540,44,f'{doc.page}' if doc.page<=5 else 'References')
    doc=SimpleDocTemplate(str(args.output),pagesize=(612,792),leftMargin=72,rightMargin=72,
                          topMargin=72,bottomMargin=72,title='Leadership disclosures and option risk - H18-H20',author='GatorQuantHacks')
    doc.build(flow,onFirstPage=footer,onLaterPages=footer)
    derived=root/'docs/massive/mechanism-round1-headline.csv'
    with derived.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(headline[0]));writer.writeheader();writer.writerows(headline)
    print(json.dumps({'pdf':str(args.output),'headline':str(derived),'trial_cells':totals,'pdf_sha256':hash_file(args.output)}))


if __name__ == '__main__':
    main()
