"""Artificial cash-flow, timing, path and checkpoint fixtures; no real data."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from discovery.io import digest, identity, read_json, write_json
from discovery.financing_strategy import (
    Data, Ledger, fees, eligibility, performance, unit_trade, run_task, quoted_diagnostics,
    owned_strategy, benchmark_checks,
)
from discovery.financing_research import CONFIG
from discovery.mechanism_engine import replay


def fixture(shape='covered_call'):
    cfg=read_json(CONFIG)
    cfg.update(stock_friction=0.,option_friction=0.,option_fee=0.,name_limit=1.,
               sector_limit=1.,gross_limit=1.,drawdown_limit=.5)
    dates=pd.bdate_range('2024-01-02',periods=55).strftime('%Y-%m-%d').tolist()
    cfg.update(start=dates[0],end=dates[-1])
    row={'study':'H23','shape':shape,'variant':'primary','pair_id':'pair',
         'anchor_id':'anchor-'+shape,'issuer':'001','ticker':'SYNTHETIC','role':'event',
         'date':dates[6],'entry_date':dates[7],'session':6,'entry_session':7,
         'event_decision':dates[6],'accessions':['a'],'features':{'momentum':.01},
         'status':'bars_downloaded','nominal_decision_close':100.,
         'contract':{'ticker':'O:SYNTHETIC','contract_type':'call' if shape=='covered_call' else 'put',
                     'strike_price':105. if shape=='covered_call' else 95.,
                     'expiration_date':dates[45],'shares_per_contract':100,'exercise_style':'american'}}
    stock={d:{'c':100.,'v':20000} for d in dates}
    option={d:{'c':5.,'v':100} for d in dates}
    class ArtificialData:
        def marks(self,r,leg):
            return stock if leg=='stock' else option
        def benchmark_asset(self,ticker):
            return Data.benchmark_asset(self,ticker)
    data=ArtificialData();data.cfg=cfg;data.dates=dates;data.index={d:i for i,d in enumerate(dates)}
    data.actions={'SYNTHETIC':{'splits':[],'dividends':[]}}
    return data,row,stock,option


def add_quotes(data,row):
    data.objects={};row['quote_objects']={}
    data.quote_pair=Data.quote_pair.__get__(data)
    for label in ['decision','entry','exit']:
        cutoff=10**15
        for leg in ['stock','option']:
            bid,ask=((109.,111.) if label=='exit' else (99.,101.)) if leg=='stock' else ((2.8,3.2) if label=='exit' else (4.8,5.2))
            key=label+'_'+leg
            data.objects[key]=[{'bid_price':bid,'ask_price':ask,'bid_size':100 if leg=='stock' else 2,
                                'ask_size':100 if leg=='stock' else 2,'sip_timestamp':cutoff-10**9}]
            row['quote_objects'][key]={'object':key,'cutoff_ns':cutoff}


class CashAndTimingTests(unittest.TestCase):
    def test_covered_call_cash_and_stock_counterfactual(self):
        data,row,stock,option=fixture()
        stock[data.dates[17]]['c']=110.;option[data.dates[17]]['c']=7.
        result=unit_trade(row,data,10)
        self.assertEqual(result['status'],'completed')
        self.assertAlmostEqual(result['stock_pnl'],1000.)
        self.assertAlmostEqual(result['option_pnl'],-200.)
        self.assertAlmostEqual(result['net_pnl'],800.)
        overlay=Ledger(data,[row])
        for day in data.dates:overlay.step(day)
        self.assertAlmostEqual(overlay.result()['daily'][-1]['nav']-data.cfg['initial_cash'],800.)
        counter=Ledger(data,overlay.accepted_entries,True,True)
        for day in data.dates:counter.step(day)
        self.assertAlmostEqual(counter.result()['daily'][-1]['nav']-data.cfg['initial_cash'],1000.)

    def test_protective_put_is_paid_long_leg_not_short_premium(self):
        data,row,stock,option=fixture('protective_put')
        for i in range(8,18):
            stock[data.dates[i]]['c']=80.;option[data.dates[i]]['c']=15.
        result=unit_trade(row,data,10)
        self.assertAlmostEqual(result['stock_pnl'],-2000.)
        self.assertAlmostEqual(result['option_pnl'],1000.)
        self.assertAlmostEqual(result['net_pnl'],-1000.)
        self.assertAlmostEqual(result['downside_loss'],.10)
        self.assertAlmostEqual(unit_trade(row,data,10,True)['downside_loss'],.20)
        ledger=Ledger(data,[row])
        for d in data.dates:ledger.step(d)
        self.assertAlmostEqual(ledger.rows[7]['cash'],data.cfg['initial_cash']-10500.)
        self.assertAlmostEqual(ledger.rows[-1]['nav']-data.cfg['initial_cash'],-1000.)

    def test_doubled_costs_and_contract_size(self):
        data,row,_,_=fixture()
        data.cfg.update(stock_friction=.0006,option_friction=.05,option_fee=.65)
        self.assertAlmostEqual(fees(100.,5.,data.cfg),31.65)
        base=unit_trade(row,data,10)
        row2={**row,'variant':'double_cost'}
        stressed=unit_trade(row2,data,10)
        self.assertAlmostEqual(stressed['total_cost'],2*base['total_cost'])
        self.assertAlmostEqual(base['downside_loss'],base['total_cost']/base['funded_notional'])
        big=unit_trade({**row,'variant':'size10'},data,10)
        self.assertAlmostEqual(big['total_cost'],10*base['total_cost'])
        self.assertAlmostEqual(big['funded_notional'],10*base['funded_notional'])

    def test_liquidity_uses_completed_sessions_before_decision(self):
        data,row,stock,option=fixture()
        option[data.dates[6]]['v']=0;option[data.dates[7]]['v']=0
        self.assertEqual(eligibility(row,data),'eligible')
        for d in data.dates[1:6]:option[d]['v']=0
        option[data.dates[6]]['v']=999999;option[data.dates[7]]['v']=999999
        self.assertEqual(eligibility(row,data),'thin_prior_option_volume')
        with self.assertRaises(ValueError):eligibility({**row,'entry_session':6,'entry_date':data.dates[6]},data)

    def test_missing_entry_unfilled_future_exit_unresolved(self):
        data,row,stock,option=fixture()
        option.pop(row['entry_date'])
        self.assertEqual(unit_trade(row,data,10)['status'],'missing_decision_or_entry_bar')
        data,row,stock,option=fixture()
        for d in data.dates[17:23]:option.pop(d)
        self.assertEqual(unit_trade(row,data,10)['status'],'initiated_unresolved')
        ledger=Ledger(data,[row])
        for day in data.dates:ledger.step(day)
        self.assertIsNone(performance(ledger.result(),data.cfg)['net_pnl'])

    def test_complete_endpoint_with_missing_interior_is_not_downside_path(self):
        data,row,_,option=fixture()
        option.pop(data.dates[10]);option.pop(data.dates[11])
        result=unit_trade(row,data,10)
        self.assertEqual(result['status'],'completed')
        self.assertFalse(result['path_complete'])
        self.assertIsNone(result['downside_loss'])
        self.assertIsNotNone(result['net_return'])

    def test_one_session_carried_mark_is_labeled_but_complete(self):
        data,row,_,option=fixture()
        option.pop(data.dates[10])
        result=unit_trade(row,data,10)
        self.assertTrue(result['path_complete'])
        ledger=Ledger(data,[row])
        for d in data.dates:ledger.step(d)
        self.assertEqual(ledger.rows[10]['stale_sessions'],1)

    def test_dividend_receivable_is_not_paid_twice(self):
        data,row,_,_=fixture()
        data.actions['SYNTHETIC']['dividends']=[{'ex_dividend_date':data.dates[9],
            'pay_date':data.dates[25],'declaration_date':data.dates[3],'currency':'USD','cash_amount':1.}]
        result=unit_trade(row,data,10)
        self.assertEqual(result['dividend_accrual'],100.)
        ledger=Ledger(data,[row])
        for d in data.dates:ledger.step(d)
        self.assertEqual(ledger.rows[9]['dividend_receivable'],100.)
        self.assertEqual(ledger.rows[25]['dividend_receivable'],0.)
        self.assertAlmostEqual(ledger.rows[-1]['nav']-data.cfg['initial_cash'],100.)

    def test_ex_dividend_same_day_payment_is_spendable_without_delay(self):
        data,row,_,_=fixture()
        data.actions['SYNTHETIC']['dividends']=[{'ex_dividend_date':data.dates[9],
            'pay_date':data.dates[9],'declaration_date':data.dates[3],'currency':'USD','cash_amount':1.}]
        ledger=Ledger(data,[row])
        for d in data.dates:ledger.step(d)
        self.assertAlmostEqual(ledger.rows[9]['cash']-ledger.rows[8]['cash'],100.)
        self.assertEqual(ledger.rows[9]['dividend_receivable'],0.)
        self.assertEqual(ledger.rows[10]['cash'],ledger.rows[9]['cash'])
        self.assertAlmostEqual(ledger.rows[-1]['nav']-data.cfg['initial_cash'],100.)

    def test_short_call_assignment_precedes_ex_dividend(self):
        data,row,stock,option=fixture()
        stock[data.dates[8]]['c']=110.;option[data.dates[8]]['c']=5.2
        data.actions['SYNTHETIC']['dividends']=[{'ex_dividend_date':data.dates[9],
            'pay_date':data.dates[20],'declaration_date':data.dates[1],'currency':'USD','cash_amount':1.}]
        result=unit_trade(row,data,10)
        self.assertEqual(result['exit_reason'],'modelled_early_assignment')
        self.assertEqual(result['dividend_accrual'],0.)
        self.assertAlmostEqual(result['net_pnl'],1000.)
        counter=unit_trade(row,data,10,True)
        self.assertEqual(result['evaluation_date'],counter['evaluation_date'])
        self.assertEqual(result['actual_exit_date'],data.dates[9])
        self.assertEqual(counter['actual_exit_date'],data.dates[17])
        self.assertTrue(result['evaluation_aligned'])

    def test_late_executable_exit_keeps_cash_outcome_without_horizon_alignment(self):
        data,row,_,option=fixture()
        option.pop(data.dates[17])
        result=unit_trade(row,data,10)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['evaluation_date'],data.dates[17])
        self.assertEqual(result['actual_exit_date'],data.dates[18])
        self.assertFalse(result['evaluation_aligned'])

    def test_put_physical_expiry_and_no_post_expiry_estimate(self):
        data,row,stock,option=fixture('protective_put')
        row['contract']['expiration_date']=data.dates[12]
        stock[data.dates[12]]['c']=80.
        result=unit_trade(row,data,'expiry')
        self.assertEqual(result['exit_reason'],'modelled_physical_expiry')
        self.assertAlmostEqual(result['net_pnl'],-1000.)
        self.assertEqual(unit_trade(row,data,10)['status'],'unavailable_after_expiry')
        self.assertEqual(unit_trade(row,data,'expiry',True)['net_pnl'],-2000.)

    def test_future_split_updates_stock_quantity_but_not_unknown_option(self):
        data,row,stock,_=fixture()
        data.actions['SYNTHETIC']['splits']=[{'execution_date':data.dates[9],'split_from':1,'split_to':2}]
        for d in data.dates[9:]:stock[d]['c']=50.
        self.assertEqual(eligibility(row,data),'eligible')
        result=unit_trade(row,data,10)
        self.assertEqual(result['reason'],'adjusted_option_deliverable_unknown')
        stock_result=unit_trade(row,data,10,True)
        self.assertEqual(stock_result['status'],'completed')
        self.assertEqual(stock_result['shares_exit'],200.)
        self.assertAlmostEqual(stock_result['net_pnl'],0.)

    def test_limits_and_identical_counterfactual_entry_schedule(self):
        data,row,_,_=fixture()
        data.cfg['name_limit']=.001
        ledger=Ledger(data,[row])
        for d in data.dates:ledger.step(d)
        self.assertEqual(len(ledger.accepted_entries),0)
        baseline=Ledger(data,[row],True,True)
        for d in data.dates:baseline.step(d)
        self.assertEqual(len(baseline.accepted_entries),1)
        self.assertFalse(baseline.baseline_risk_comparable)

    def test_drawdown_exit_uses_following_session_not_trigger_close(self):
        data,row,stock,option=fixture('protective_put')
        data.cfg.update(initial_cash=12000.,drawdown_limit=.05)
        stock[data.dates[9]]['c']=80.
        ledger=Ledger(data,[row])
        for d in data.dates:ledger.step(d)
        closed=[r for r in ledger.trades if r['status']=='completed']
        self.assertEqual(closed[0]['exit_date'],data.dates[10])
        self.assertEqual(closed[0]['exit_reason'],'drawdown_exit')

    def test_cooldown_reentry_begins_on_registered_eligibility_session(self):
        data,row,_,_=fixture()
        ledger=Ledger(data,[row]);ledger.derisk=True;ledger.cooldown=row['entry_session']
        for day in data.dates:ledger.step(day)
        self.assertEqual(len(ledger.accepted_entries),1)

    def test_unknown_dividend_currency_is_unresolved_not_zero_cash(self):
        data,row,_,_=fixture()
        data.actions['SYNTHETIC']['dividends']=[{'ex_dividend_date':data.dates[9],
            'currency':'EUR','cash_amount':1.}]
        result=unit_trade(row,data,10)
        self.assertEqual(result['status'],'initiated_unresolved')
        self.assertEqual(result['reason'],'unsupported_dividend_cashflow')

    def test_folder_owned_backtrader_strategy_replays_explicit_ledger(self):
        data,row,stock,option=fixture();stock[data.dates[17]]['c']=110.;option[data.dates[17]]['c']=7.
        strategy=owned_strategy(data,'H23')
        self.assertEqual(strategy.study,'H23')
        result=replay(strategy,Ledger(data,[row]),data.dates)
        self.assertAlmostEqual(performance(result,data.cfg)['net_pnl'],800.)


class BoundedQuoteTests(unittest.TestCase):
    def test_bid_ask_call_put_and_stock_costs_without_extra_spread(self):
        for shape,expected in [('covered_call',946.5),('protective_put',546.5)]:
            data,row,_,_=fixture(shape);data.cfg['option_fee']=.65;add_quotes(data,row)
            result=quoted_diagnostics(row,data,unit_trade(row,data,10))
            self.assertEqual(result['quote_status'],'completed_bounded_proxy')
            self.assertAlmostEqual(result['quote_net_pnl'],expected)
            self.assertAlmostEqual(result['quote_total_cost'],13.5)
            self.assertFalse(result['quote_path_complete']);self.assertIsNone(result['quote_downside_loss'])
            baseline=quoted_diagnostics(row,data,unit_trade(row,data,10,True),True)
            self.assertAlmostEqual(baseline['quote_net_pnl'],795.8)

    def test_doubled_quote_friction_does_not_double_observed_spread(self):
        data,row,_,_=fixture();data.cfg['option_fee']=.65;add_quotes(data,row)
        outcome=unit_trade(row,data,10);base=quoted_diagnostics(row,data,outcome)
        outcome['cost_multiplier']=2;stress=quoted_diagnostics(row,data,outcome)
        self.assertAlmostEqual(stress['quote_total_cost'],2*base['quote_total_cost'])
        self.assertAlmostEqual(base['quote_net_pnl']-stress['quote_net_pnl'],base['quote_total_cost'])
        self.assertEqual(stress['quote_entry_option'],base['quote_entry_option'])

    def test_stale_future_crossed_wide_and_asynchronous_quotes_are_rejected(self):
        cases=[('stale',{'sip_timestamp':10**15-61*10**9},'missing_or_stale_quote'),
               ('future',{'sip_timestamp':10**15+1},'missing_or_stale_quote'),
               ('crossed',{'bid_price':6.,'ask_price':5.},'invalid_quote_or_size'),
               ('nan',{'bid_price':float('nan')},'invalid_quote_or_size'),
               ('size',{'ask_size':0},'invalid_quote_or_size'),
               ('wide',{'bid_price':1.,'ask_price':5.},'wide_option_spread'),
               ('async',{'sip_timestamp':10**15-7*10**9},'asynchronous_quotes')]
        for name,change,expected in cases:
            data,row,_,_=fixture();add_quotes(data,row);data.objects['entry_option'][0].update(change)
            with self.subTest(name=name):
                self.assertEqual(data.quote_pair(row,'entry')[1],expected)

    def test_missing_and_unsampled_quotes_remain_explicit(self):
        data,row,_,_=fixture();outcome=unit_trade(row,data,10)
        self.assertEqual(quoted_diagnostics(row,data,outcome)['quote_status'],'not_sampled_or_missing_quotes')
        add_quotes(data,row);row['quote_objects']['entry_option']={'failure':'denied'}
        self.assertEqual(quoted_diagnostics(row,data,outcome)['quote_status'],'entry_missing_quote')
        self.assertEqual(quoted_diagnostics(row,data,unit_trade(row,data,5))['quote_status'],'not_requested_for_horizon_or_variant')


class ImmutableInputAndCheckpointTests(unittest.TestCase):
    def test_benchmark_missing_source_or_policy_never_becomes_performance(self):
        data,_,_,_=fixture();data.source={}
        evidence=benchmark_checks(data)
        self.assertEqual(evidence['status'],'partial')
        self.assertEqual(evidence['spy_source_status'],'pending_acquisition')
        self.assertEqual(len(evidence['spy_missing_objects']),4)
        self.assertIn('ex_ante_volatility_target_and_scaling_formula',evidence['missing_method_decisions'])
        self.assertNotIn('annualized_return',evidence)

    def test_benchmark_asset_nominal_adjusted_and_action_provenance(self):
        data,_,_,_=fixture();data.objects={};data.source={'benchmark_objects':{'SPY':{}},'objects':{}}
        keys=['nominal_object','adjusted_object','dividends_object','splits_object']
        for label in keys:
            if label in {'nominal_object','adjusted_object'}:
                path=f"/v2/aggs/ticker/SPY/range/1/day/{data.cfg['start']}/{data.cfg['end']}"
                params={'adjusted':'false' if label=='nominal_object' else 'true'}
                rows=[{'t':int(pd.Timestamp(data.dates[0]+'T05:00:00Z').value/10**6),
                       'c':100. if label=='nominal_object' else 50.,'v':100000}]
            else:
                path='/v3/reference/'+('dividends' if label=='dividends_object' else 'splits')
                params={'ticker':'SPY'};rows=[]
            data.source['benchmark_objects']['SPY'][label]=label
            data.source['objects'][label]={'spec':{'path':path,'params':params,'paginate':True}}
            data.objects[label]=rows
        result=Data.benchmark_asset(data,'SPY')
        self.assertEqual(result['status'],'available_data')
        self.assertEqual(result['nominal'][data.dates[0]]['c'],100.)
        self.assertEqual(result['adjusted'][data.dates[0]]['c'],50.)
        data.source['objects']['nominal_object']['spec']['params']['adjusted']='true'
        with self.assertRaises(ValueError):Data.benchmark_asset(data,'SPY')
        data.source['objects']['nominal_object']['spec']['params']['adjusted']='false'
        data.source['objects']['dividends_object']['spec']['params']['ticker']='ANOTHER_ASSET'
        with self.assertRaises(ValueError):Data.benchmark_asset(data,'SPY')

    def test_artificial_whole_task_writes_hashed_outputs_and_restarts(self):
        data,row,_,_=fixture();data.records=[row];data.source={'source_id':'artificial-source'}
        with tempfile.TemporaryDirectory() as temp:
            run=Path(temp);write_json(run/'tasks.json',[{'task':0,'study':'H23','variant':'primary'}])
            manifest={'manifest_id':'artificial-manifest'}
            with patch('discovery.financing_strategy.scheduled'),\
                    patch('discovery.financing_strategy.verify_manifest',return_value=manifest),\
                    patch('discovery.financing_research.verify_manifest',return_value=manifest),\
                    patch('discovery.financing_strategy.Data',return_value=data):
                result=run_task(run,0)
                self.assertEqual(result['status'],'completed');self.assertEqual(result['unit_outcomes'],18)
                folder=run/'results/tasks/0'
                with (folder/'trades.csv').open(newline='',encoding='utf-8') as handle:
                    rows=list(csv.DictReader(handle))
                self.assertEqual(len(rows),18)
                self.assertTrue({'evaluation_date','actual_exit_date','net_return','quote_status'}<=set(rows[0]))
                self.assertIn('initiated_outcome_outside_history',{r['status'] for r in rows})
                with (folder/'coverage.csv').open(newline='',encoding='utf-8') as handle:
                    coverage=list(csv.DictReader(handle))
                self.assertEqual({r['coverage_stage'] for r in coverage},{'acquisition_eligibility','portfolio_ledger'})
                self.assertEqual(sum(r['coverage_stage']=='portfolio_ledger' and r['status']=='completed' for r in coverage),2)
                receipt=read_json(run/'receipts/task-0.json')
                self.assertEqual(len(receipt['files']),5)
                for member,expected in receipt['files'].items():self.assertEqual(digest(run/member),expected)
                with patch('discovery.financing_strategy.Data',side_effect=AssertionError('Completed task must not rerun')):
                    self.assertEqual(run_task(run,0)['source_id'],'artificial-source')

    def test_incomplete_source_and_changed_anchor_or_config_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            run=Path(temp);(run/'prepared').mkdir();(run/'acquisition').mkdir()
            write_json(run/'prepared/calendar.json',{'dates':['2024-01-02']})
            write_json(run/'prepared/actions.json',{})
            write_json(run/'prepared/anchors.json',[])
            source={'complete':True,'anchors_sha256':digest(run/'prepared/anchors.json'),
                    'settings_sha256':digest(CONFIG),'objects':{},'records':[]}
            source['source_id']=identity(source)
            write_json(run/'acquisition/source.json',source)
            self.assertEqual(Data(run).records,[])
            for field,value in [('complete',False),('anchors_sha256','bad'),('settings_sha256','bad')]:
                modified={**source,field:value};modified.pop('source_id');modified['source_id']=identity(modified)
                write_json(run/'acquisition/source.json',modified)
                with self.subTest(field=field),self.assertRaises(ValueError):Data(run)

    def test_completed_checkpoint_skips_compute_and_changed_output_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            run=Path(temp);(run/'receipts').mkdir()
            write_json(run/'tasks.json',[{'task':0,'study':'H23','variant':'primary'}])
            out=run/'output.json';write_json(out,{'artificial':1})
            write_json(run/'receipts/task-0.json',{'manifest_id':'fixed','status':'completed','files':{'output.json':digest(out)}})
            with patch('discovery.financing_strategy.scheduled'),patch('discovery.financing_strategy.verify_manifest',return_value={'manifest_id':'fixed'}):
                with patch('discovery.financing_strategy.Data',side_effect=AssertionError('Must not compute')):
                    self.assertEqual(run_task(run,0)['status'],'completed')
                write_json(out,{'artificial':2})
                with self.assertRaises(ValueError):run_task(run,0)

    def test_checkpoint_cannot_reference_outside_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);run=root/'run';(run/'receipts').mkdir(parents=True)
            write_json(run/'tasks.json',[{'task':0,'study':'H23','variant':'primary'}])
            out=root/'outside.json';write_json(out,{'artificial':1})
            write_json(run/'receipts/task-0.json',{'manifest_id':'fixed','status':'completed','files':{'../outside.json':digest(out)}})
            with patch('discovery.financing_strategy.scheduled'),patch('discovery.financing_strategy.verify_manifest',return_value={'manifest_id':'fixed'}):
                with self.assertRaises(ValueError):run_task(run,0)


if __name__=='__main__':unittest.main()
