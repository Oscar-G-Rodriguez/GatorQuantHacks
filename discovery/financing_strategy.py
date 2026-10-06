"""Registered H23-H25 funded-share accounting, adapted from H22.

Backtrader supplies only the Webull starter's session/Strategy organization.
Actual NAV comes from this explicit share/option ledger, never its clock feed.
Both shapes retain unknown paths, unfilled orders and unresolved cash flows.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
import json
import importlib.util
import math
from pathlib import Path
import sys
import time
from urllib.parse import quote
try:
    import resource
except ImportError:
    resource = None

import numpy as np
import pandas as pd

from .io import digest, identity, read_json, write_json
from .mechanism_engine import FundedStrategy, replay
from .financing_research import ROOT, CONFIG, scheduled, csv_write, verify_manifest, receipt, bar_map


class Data:
    """Immutable complete acquisition; no future-filled session lookups."""
    def __init__(self, run):
        self.run = Path(run)
        self.cfg = read_json(CONFIG)
        self.calendar = read_json(self.run/'prepared/calendar.json')
        self.dates = self.calendar['dates']
        if self.dates != sorted(set(self.dates)):
            raise ValueError('Calendar must be ordered unique sessions')
        self.index = {d:i for i,d in enumerate(self.dates)}
        self.actions = read_json(self.run/'prepared/actions.json')
        self.source = read_json(self.run/'acquisition/source.json')
        if self.source.get('complete') is not True:
            raise ValueError('Incomplete acquisition cannot become a backtest')
        if self.source.get('anchors_sha256') != digest(self.run/'prepared/anchors.json'):
            raise ValueError('Prepared anchor identity differs')
        if self.source.get('settings_sha256', self.source.get('config_sha256')) != digest(CONFIG):
            raise ValueError('Acquisition settings identity differs')
        if self.source.get('source_id') != identity({k:v for k,v in self.source.items() if k!='source_id'}):
            raise ValueError('Acquisition identity differs')
        self.objects, self.bars = {}, {}
        directory = (self.run/'acquisition/objects').resolve()
        for key,obj in self.source['objects'].items():
            path = (directory/(key+'.json')).resolve()
            if not path.is_relative_to(directory) or digest(path)!=obj['sha256']:
                raise ValueError('Acquired object differs or escapes directory')
            self.objects[key] = read_json(path)
        self.records = self.source['records']
        seen = set()
        for row in self.records:
            key = (row['anchor_id'], row['shape'])
            if key in seen:
                raise ValueError('Duplicate acquisition anchor/shape')
            seen.add(key)
            if row.get('status') in {'pending','request_failed'}:
                raise ValueError('Acquisition still has unfinished anchors')

    def marks(self, row, leg):
        key = row.get(leg+'_object')
        if key is None:
            return {}
        if key not in self.objects:
            raise ValueError('Missing frozen object')
        if key not in self.bars:
            self.bars[key] = bar_map(self.objects[key])
        return self.bars[key]

    def quote_pair(self, row, label):
        quotes = []
        for leg in ['stock','option']:
            keys = [label+'_'+leg]
            if leg=='option':
                keys += [label+('_call' if row['shape']=='covered_call' else '_put')]
            ref = next((row.get('quote_objects',{}).get(k) for k in keys
                        if row.get('quote_objects',{}).get(k)), {})
            if 'object' not in ref:
                return None,'missing_quote'
            cutoff = ref['cutoff_ns']
            candidates = [q for q in self.objects[ref['object']]
                          if 0<=cutoff-q.get('sip_timestamp',0)<=self.cfg['quote_max_age_seconds']*1e9]
            if not candidates:
                return None,'missing_or_stale_quote'
            q = max(candidates,key=lambda q:q['sip_timestamp'])
            bid,ask = q.get('bid_price',0),q.get('ask_price',0)
            if (not all(isinstance(x,(int,float)) and math.isfinite(x) for x in [bid,ask])
                    or bid<=0 or ask<bid or min(q.get('bid_size',0),q.get('ask_size',0))<1):
                return None,'invalid_quote_or_size'
            mid = (bid+ask)/2
            if leg=='option' and (ask-bid)/mid>self.cfg['quote_max_relative_spread']:
                return None,'wide_option_spread'
            quotes.append({'bid':bid,'ask':ask,'mid':mid,'timestamp':q['sip_timestamp'],
                           'bid_size':q['bid_size'],'ask_size':q['ask_size'],
                           'age_seconds':(cutoff-q['sip_timestamp'])/1e9,'relative_spread':(ask-bid)/mid})
        if abs(quotes[0]['timestamp']-quotes[1]['timestamp'])/1e9>self.cfg['quote_synchrony_seconds']:
            return None,'asynchronous_quotes'
        return quotes,'fresh_quotes'

    def benchmark_asset(self,ticker):
        """Verify an optional Massive-only source; never relabel another asset.

        Acquisition may reference four already hashed objects under
        source.benchmark_objects[ticker]. Missing benchmark acquisition does
        not invalidate the distinct event/option study's source completeness.
        """
        refs=self.source.get('benchmark_objects',{}).get(ticker,{})
        required=['nominal_object','adjusted_object','dividends_object','splits_object']
        missing=[k for k in required if not refs.get(k)]
        if missing:
            return {'asset':ticker,'status':'pending_acquisition','missing':missing}
        for label in required:
            key=refs[label]
            if key not in self.objects or key not in self.source['objects']:
                raise ValueError('Referenced benchmark object is missing')
            spec=self.source['objects'][key].get('spec',{})
            params=spec.get('params',{})
            if spec.get('paginate') is not True:
                raise ValueError('Benchmark source is not fully paginated')
            if label in {'nominal_object','adjusted_object'}:
                expected=f"/v2/aggs/ticker/{quote(ticker,safe='')}/range/1/day/{self.cfg['start']}/{self.cfg['end']}"
                adjusted='false' if label=='nominal_object' else 'true'
                if spec.get('path')!=expected or params.get('adjusted')!=adjusted:
                    raise ValueError('Benchmark asset/adjustment identity differs')
            else:
                endpoint='dividends' if label=='dividends_object' else 'splits'
                if spec.get('path')!='/v3/reference/'+endpoint or params.get('ticker')!=ticker:
                    raise ValueError('Benchmark corporate-action asset identity differs')
        return {'asset':ticker,'status':'available_data','objects':refs,
                'nominal':bar_map(self.objects[refs['nominal_object']]),
                'adjusted':bar_map(self.objects[refs['adjusted_object']]),
                'actions':{'dividends':self.objects[refs['dividends_object']],
                           'splits':self.objects[refs['splits_object']]}}


def direction(shape, stock_only=False):
    if stock_only:
        return 0
    if shape=='covered_call':
        return -1
    if shape=='protective_put':
        return 1
    raise ValueError('Unregistered shape')


def variant_settings(data, row):
    return next(v for v in data.cfg['variants'] if v['id']==row['variant'])


def fees(stock, option, cfg, costs=1, contracts=1, stock_only=False, shares=None):
    shares = 100*contracts if shares is None else shares
    return costs*(shares*stock*cfg['stock_friction'] +
                  (0 if stock_only else contracts*(100*option*cfg['option_friction']+cfg['option_fee'])))


def fresh_mark(marks, dates, i, max_age=1):
    for age in range(max_age+1):
        if i-age>=0 and dates[i-age] in marks:
            close=marks[dates[i-age]].get('c')
            if isinstance(close,(int,float)) and math.isfinite(close) and close>=0:
                return close,age
    return None,None


def expiry_session(row, data):
    expiry = row['contract']['expiration_date']
    if expiry>data.cfg['end'] or expiry<data.cfg['start']:
        return None
    i = bisect_right(data.dates,expiry)-1
    return i if i>=0 else None


def eligibility(row, data):
    if row.get('status')!='bars_downloaded':
        return row.get('status','missing_record')
    di,ei = row['session'],row['entry_session']
    if not 0<=di<ei<len(data.dates) or ei!=di+1:
        raise ValueError('Fill must follow decision by one session')
    if data.dates[di]!=row['date'] or data.dates[ei]!=row['entry_date']:
        raise ValueError('Decision/fill calendar differs')
    contract = row['contract']
    expected = 'call' if row['shape']=='covered_call' else 'put'
    if (contract.get('shares_per_contract')!=100 or contract.get('additional_underlyings')
            or contract.get('contract_type')!=expected
            or contract.get('exercise_style') not in {'american','european'}):
        return 'unsupported_contract_deliverable'
    stock,option = data.marks(row,'stock'),data.marks(row,'option')
    if any(d not in stock or d not in option for d in [row['date'],row['entry_date']]):
        return 'missing_decision_or_entry_bar'
    if any(not isinstance(marks[d].get('c'),(int,float)) or not math.isfinite(marks[d]['c'])
           or marks[d]['c']<=0 for marks in [stock,option] for d in [row['date'],row['entry_date']]):
        return 'invalid_decision_or_entry_price'
    # Both volume gates precede decision; neither decision nor fill volume enters.
    prior = data.dates[max(0,di-5):di]
    if len(prior)!=5 or any(d not in stock or d not in option for d in prior):
        return 'incomplete_prior_liquidity'
    if sum(option[d].get('v',0) for d in prior)<data.cfg['minimum_prior_option_volume']:
        return 'thin_prior_option_volume'
    if np.mean([stock[d].get('v',0) for d in prior])<data.cfg['minimum_prior_stock_volume']:
        return 'thin_prior_stock_volume'
    return 'eligible'


def new_position(row, data, stock_only=False):
    v = variant_settings(data,row)
    stock,option = data.marks(row,'stock'),data.marks(row,'option')
    s0,o0 = stock[row['entry_date']]['c'],option[row['entry_date']]['c']
    n = v['contracts'];q = 100*n
    opening = fees(s0,o0,data.cfg,v['cost_multiplier'],n,stock_only,q)
    return {'r':row,'s0':s0,'o0':o0,'shares':q,'initial_shares':q,'contracts':n,
            'sign':direction(row['shape'],stock_only),'opening':opening,
            'costs':v['cost_multiplier'],'stock_only':stock_only,
            'assignment':v.get('assignment','time_value'),'dividends':0.,
            'path_complete':True,'minimum_return':0.,'mark_gaps':0,
            'funded_notional':q*s0,'outlay':q*s0+direction(row['shape'],stock_only)*100*n*o0+opening}


def mark_position(p, data, i, include_exit_cost=True):
    row=p['r'];s,sa=fresh_mark(data.marks(row,'stock'),data.dates,i,data.cfg['max_mark_carry_sessions'])
    o,oa=(0.,0) if p['stock_only'] else fresh_mark(data.marks(row,'option'),data.dates,i,data.cfg['max_mark_carry_sessions'])
    if s is None or o is None or p.get('unresolved'):
        p['path_complete']=False;p['mark_gaps']+=1
        return None,None
    value=p['shares']*s+p['sign']*100*p['contracts']*o
    closing=fees(s,o,data.cfg,p['costs'],p['contracts'],p['stock_only'],p['shares']) if include_exit_cost else 0
    net=value+p['dividends']-p['outlay']-closing
    p['minimum_return']=min(p['minimum_return'],net/p['funded_notional'])
    return value,max(sa,oa)


def advance(p, data, i, target, risk_exit=False):
    """Cash-flow processing shared by unit diagnostics and the daily portfolio.

    Return (stock settlement price, option settlement price, reason), plus new
    dividend receivables. A future split never cancels an earlier valid entry.
    """
    row=p['r'];day=data.dates[i];stock=data.marks(row,'stock');option=data.marks(row,'option')
    actions=data.actions.get(row['ticker'],{'splits':[],'dividends':[]});new_dividends=[]
    for split in actions.get('splits',[]):
        if split.get('execution_date')!=day:
            continue
        a,b=split.get('split_to'),split.get('split_from')
        if not a or not b or a<=0 or b<=0:
            p['unresolved']='unknown_share_split_ratio'
        else:
            p['shares']*=a/b
            if abs(p['shares']-round(p['shares']))>1e-9:
                p['unresolved']='fractional_share_cash_in_lieu_unknown'
            if not p['stock_only']:
                p['unresolved']='adjusted_option_deliverable_unknown'
    if p.get('unresolved'):
        p['path_complete']=False
        return None,new_dividends
    divs=[a for a in actions.get('dividends',[]) if a.get('ex_dividend_date')==day]
    if any(a.get('currency')!='USD' or not isinstance(a.get('cash_amount'),(int,float))
           or not math.isfinite(a['cash_amount']) or a['cash_amount']<0 for a in divs):
        p['unresolved']='unsupported_dividend_cashflow';p['path_complete']=False
        return None,new_dividends
    previous=data.dates[i-1] if i else None
    contract=row['contract'];strike=float(contract['strike_price'])
    for dividend in divs:
        if (p['sign']==-1 and contract['exercise_style']=='american' and previous
                and dividend.get('declaration_date',day)<=previous and previous in stock and previous in option):
            s,o=stock[previous]['c'],option[previous]['c']
            if s>strike and (p['assignment']=='all_itm_pre_dividend' or o-(s-strike)<dividend['cash_amount']):
                return (strike,0.,'modelled_early_assignment'),new_dividends
        dollars=p['shares']*dividend['cash_amount'];p['dividends']+=dollars
        new_dividends.append({'dollars':dollars,'pay':dividend.get('pay_date') or data.cfg['end']+'~'})
    expiry=expiry_session(row,data)
    if not p['stock_only'] and expiry is not None and i>=expiry:
        if day not in stock:
            p['unresolved']='missing_expiry_stock';p['path_complete']=False
            return None,new_dividends
        s=stock[day]['c']
        itm=(s>strike if p['sign']==-1 else s<strike)
        return (strike if itm else s,0.,'modelled_physical_expiry' if itm else 'expiry_worthless'),new_dividends
    if i>=target or risk_exit:
        if day in stock and (p['stock_only'] or day in option):
            return (stock[day]['c'],0. if p['stock_only'] else option[day]['c'],
                    'drawdown_exit' if risk_exit else 'scheduled_exit'),new_dividends
        if i>target+data.cfg['exit_retry_sessions']:
            p['unresolved']='unfilled_exit_after_retries';p['path_complete']=False
    return None,new_dividends


def close_position(p, data, i, settlement):
    s,o,reason=settlement
    closing=fees(s,o,data.cfg,p['costs'],p['contracts'],p['stock_only'],p['shares'])
    stock_pnl=p['shares']*s-p['initial_shares']*p['s0']
    option_pnl=p['sign']*100*p['contracts']*(o-p['o0'])
    net=stock_pnl+option_pnl+p['dividends']-p['opening']-closing
    p['minimum_return']=min(p['minimum_return'],net/p['funded_notional'])
    return {'exit_date':data.dates[i],'exit_session':i,'exit_reason':reason,
            'stock_exit':s,'option_exit':o,'stock_pnl':stock_pnl,'option_pnl':option_pnl,
            'dividend_accrual':p['dividends'],'closing_cost':closing,'total_cost':p['opening']+closing,
            'net_pnl':net,'net_return':net/p['funded_notional'],
            'downside_loss':max(0.,-p['minimum_return']) if p['path_complete'] else None,
            'path_complete':p['path_complete'],'mark_gap_sessions':p['mark_gaps'],
            'shares_exit':p['shares'],'closing_cash':p['shares']*s+p['sign']*100*p['contracts']*o-closing}


def unit_trade(row, data, horizon, stock_only=False):
    result={k:row.get(k) for k in ['study','variant','shape','anchor_id','pair_id','issuer','ticker','role','event_decision']}
    v=variant_settings(data,row)
    result.update(horizon=horizon,stock_only=stock_only,status=eligibility(row,data),reason=None,
                  date=row['date'],decision_date=row['date'],decision_session=row['session'],
                  entry_date=row['entry_date'],entry_session=row['entry_session'],year=int(row['entry_date'][:4]),
                  cost_multiplier=v['cost_multiplier'],contracts=v['contracts'],
                  assignment_policy=v.get('assignment','time_value'),path_complete=False,
                  net_pnl=None,net_return=None,downside_loss=None,exit_date=None,exit_session=None,
                  evaluation_date=None,evaluation_session=None,evaluation_aligned=False,
                  actual_exit_date=None,actual_exit_session=None,
                  fill_model='assumed_next_daily_close',features_json=json.dumps(row.get('features',{}),sort_keys=True))
    result.update(row.get('features',{}))
    if result['status']!='eligible':
        result['reason']=result['status'];return result
    expiry=expiry_session(row,data)
    target=expiry if horizon=='expiry' else row['entry_session']+int(horizon)
    if target is None or target>=len(data.dates):
        result.update(status='initiated_outcome_outside_history',reason='outcome_outside_history');return result
    if target<row['entry_session'] or (horizon!='expiry' and expiry is not None and target>expiry):
        result.update(status='unavailable_after_expiry',reason='registered_horizon_after_contract_expiry');return result
    result.update(evaluation_date=data.dates[target],evaluation_session=target)
    p=new_position(row,data,stock_only)
    option=data.marks(row,'option');stock=data.marks(row,'stock');prior=data.dates[row['session']-5:row['session']]
    nominal=row.get('nominal_decision_close',stock[row['date']]['c'])
    strike=float(row['contract']['strike_price'])
    result.update(stock_entry=p['s0'],option_entry=p['o0'],funded_notional=p['funded_notional'],opening_cost=p['opening'],
                  decision_premium_ratio=option[row['date']]['c']/nominal,
                  achieved_otm=strike/nominal-1 if row['shape']=='covered_call' else 1-strike/nominal,
                  decision_dte=(pd.Timestamp(row['contract']['expiration_date'])-pd.Timestamp(row['date'])).days,
                  prior_option_volume=sum(option[d].get('v',0) for d in prior),
                  prior_stock_volume=float(np.mean([stock[d].get('v',0) for d in prior])),
                  prior_option_participation=p['contracts']/sum(option[d].get('v',0) for d in prior),
                  prior_stock_participation=p['shares']/float(np.mean([stock[d].get('v',0) for d in prior])),
                  execution_option_volume=option[row['entry_date']].get('v'),
                  execution_stock_volume=stock[row['entry_date']].get('v'),
                  contract_ticker=row['contract']['ticker'],expiry=row['contract']['expiration_date'])
    mark_position(p,data,row['entry_session'])
    for i in range(row['entry_session']+1,min(target+data.cfg['exit_retry_sessions'],len(data.dates)-1)+1):
        settlement,_=advance(p,data,i,target)
        if settlement:
            result.update(close_position(p,data,i,settlement),status='completed')
            # Assignment proceeds earn the registered zero cash return until
            # the common horizon. Late executable fills keep their real cash
            # outcome but are not horizon-aligned observations for inference.
            result.update(actual_exit_date=data.dates[i],actual_exit_session=i,
                          evaluation_aligned=i==target or (i<target and settlement[2]=='modelled_early_assignment'))
            result.pop('closing_cash',None)
            return result
        mark_position(p,data,i)
        if p.get('unresolved'):
            break
    result.update(status='initiated_unresolved',reason=p.get('unresolved','unfilled_exit_after_retries'),
                  path_complete=p['path_complete'],mark_gap_sessions=p['mark_gaps'])
    return result


def quoted_diagnostics(row,data,outcome,stock_only=False):
    """Bounded bid/ask cash outcomes; no assumed extra spread or daily path.

    Quotes describe observations at most sixty seconds before the close,
    rather than guaranteeing execution at the exact daily closing price.
    Corporate-delivery paths need quotes at their actual settlement clock and
    are retained as unsupported by this bounded scheduled-exit quote sample.
    """
    result={'quote_status':'not_requested_for_horizon_or_variant','quote_net_pnl':None,
            'quote_net_return':None,'quote_downside_loss':None,'quote_path_complete':False,
            'quote_fill_model':'bounded_preclose_bid_ask'}
    if outcome['horizon']!=data.cfg['primary_horizon'] or row['variant']!='primary':
        return result
    if not row.get('quote_objects'):
        result['quote_status']='not_sampled_or_missing_quotes';return result
    if outcome['status']!='completed':
        result['quote_status']='bar_outcome_not_completed';return result
    if (not outcome['evaluation_aligned'] or outcome['actual_exit_session']!=outcome['evaluation_session']
            or outcome['exit_reason']!='scheduled_exit'
            or outcome['shares_exit']!=100*outcome['contracts']):
        result['quote_status']='unsupported_actual_delivery_or_exit_clock';return result
    for label in ['decision','entry','exit']:
        pair,status=data.quote_pair(row,label)
        if pair is None:
            result['quote_status']=label+'_'+status;return result
        for leg,q in zip(['stock','option'],pair):
            for field in ['bid','ask','bid_size','ask_size','age_seconds','relative_spread']:
                result[f'quote_{label}_{leg}_{field}']=q[field]
    n=outcome['contracts'];shares=100*n;sign=direction(row['shape'],stock_only)
    s0=result['quote_entry_stock_ask'];st=result['quote_exit_stock_bid']
    o0=(result['quote_entry_option_bid'] if sign==-1 else result['quote_entry_option_ask']) if sign else 0.
    ot=(result['quote_exit_option_ask'] if sign==-1 else result['quote_exit_option_bid']) if sign else 0.
    multiplier=outcome['cost_multiplier']
    costs=multiplier*(shares*(s0+st)*(data.cfg['quote_stock_fee']+data.cfg['quote_stock_impact'])+
                      (0. if stock_only else n*(100*(o0+ot)*data.cfg['quote_impact']+2*data.cfg['option_fee'])))
    stock_pnl=shares*(st-s0);option_pnl=sign*100*n*(ot-o0)
    net=stock_pnl+option_pnl+outcome['dividend_accrual']-costs
    relevant_size=min(result['quote_entry_option_bid_size' if sign==-1 else 'quote_entry_option_ask_size'],
                      result['quote_exit_option_ask_size' if sign==-1 else 'quote_exit_option_bid_size'])
    result.update(quote_status='completed_bounded_proxy',quote_net_pnl=net,quote_net_return=net/(shares*s0),
                  quote_stock_pnl=stock_pnl,quote_option_pnl=option_pnl,quote_total_cost=costs,
                  quote_entry_stock=s0,quote_exit_stock=st,quote_entry_option=o0,quote_exit_option=ot,
                  quote_displayed_option_size=relevant_size,quote_contracts_within_displayed_size=n<=relevant_size)
    return result


class Ledger:
    """Actual funded shares and one signed option leg; no broker P&L shortcut."""
    def __init__(self,data,records,stock_only=False,accepted_only=False):
        self.data=data;self.records=defaultdict(list);self.stock_only=stock_only;self.accepted_only=accepted_only
        self.cash=data.cfg['initial_cash'];self.positions={};self.rows=[];self.trades=[];self.accepted_entries=[]
        self.receivables=[];self.invalid_nav=False;self.baseline_risk_comparable=True
        self.high=self.cash;self.last_nav=self.cash;self.derisk=False;self.cooldown=-1;self.turnover=0.
        for row in records:
            self.records[row['entry_date']].append(row)

    def _close(self,key,i,settlement):
        p=self.positions.pop(key);closed=close_position(p,self.data,i,settlement)
        self.cash+=closed.pop('closing_cash');self.turnover+=p['shares']*settlement[0]+(0 if self.stock_only else 100*p['contracts']*settlement[1])
        row=p['r'];self.trades.append({**{k:row.get(k) for k in ['anchor_id','pair_id','issuer','ticker','role','shape']},
            'entry_date':row['entry_date'],'status':'completed','stock_only':self.stock_only,**closed})

    def step(self,day):
        data=self.data;i=data.index[day];bad=False;stale=0
        due=[r for r in self.receivables if r['pay']<=day]
        self.cash+=sum(r['dollars'] for r in due)
        self.receivables=[r for r in self.receivables if r['pay']>day]
        for key,p in list(self.positions.items()):
            settlement,divs=advance(p,data,i,p['target'],self.derisk)
            # A new accrual can also be payable today. Cash becomes available
            # before today's ordered entries, rather than one session late.
            self.cash+=sum(r['dollars'] for r in divs if r['pay']<=day)
            self.receivables.extend(r for r in divs if r['pay']>day)
            if settlement:
                self._close(key,i,settlement)
        if self.derisk and not self.positions and i>=self.cooldown and not self.invalid_nav:
            self.derisk=False;self.high=self.last_nav;self.cooldown=-1
        gross=0.;sectors=defaultdict(float);names=defaultdict(float)
        for p in self.positions.values():
            s,_=fresh_mark(data.marks(p['r'],'stock'),data.dates,i,data.cfg['max_mark_carry_sessions'])
            funding=p['shares']*(s if s is not None else p['s0'])
            gross+=funding;sectors[p['r'].get('sector') or 'unknown']+=funding;names[p['r']['issuer']]+=funding
        # Sizing/cooldown state comes from an earlier close. Today's drawdown
        # cannot retroactively reject an order already filled at today's close.
        for row in sorted(self.records.get(day,[]),key=lambda r:(r['issuer'],str(r.get('accessions')),r['anchor_id'])):
            reason=eligibility(row,data);p=None
            if reason=='eligible':
                p=new_position(row,data,self.stock_only);p['target']=i+data.cfg['primary_horizon']
                expiry=expiry_session(row,data)
                if p['target']>=len(data.dates) or (expiry is not None and p['target']>expiry):
                    reason='primary_exit_outside_history_or_after_expiry'
                elif not self.accepted_only and any(q['r']['issuer']==row['issuer'] for q in self.positions.values()):
                    reason='issuer_position_already_open'
                elif not self.accepted_only and (self.derisk or i<self.cooldown or self.invalid_nav):
                    reason='risk_cooldown_or_unknown_nav'
                funding=p['funded_notional'];sector=row.get('sector') or 'unknown'
                limit_bad=(names[row['issuer']]+funding>self.last_nav*data.cfg['name_limit'] or
                           gross+funding>self.last_nav*data.cfg['gross_limit'] or
                           sectors[sector]+funding>self.last_nav*data.cfg['sector_limit'] or p['outlay']>self.cash)
                if self.accepted_only and (limit_bad or self.derisk or i<self.cooldown):
                    self.baseline_risk_comparable=False
                elif reason=='eligible' and limit_bad:
                    reason='funding_or_exposure_limit'
                if reason=='eligible':
                    self.cash-=p['outlay'];self.turnover+=funding+(0 if self.stock_only else 100*p['contracts']*p['o0'])
                    gross+=funding;names[row['issuer']]+=funding;sectors[sector]+=funding
                    self.positions[row['anchor_id']]=p;self.accepted_entries.append(row)
                    if self.cash<0:
                        self.baseline_risk_comparable=False;bad=True
                    continue
            self.trades.append({'anchor_id':row['anchor_id'],'pair_id':row['pair_id'],'issuer':row['issuer'],
                                'entry_date':day,'stock_only':self.stock_only,'status':'unfilled','reason':reason})
        nav=self.cash+sum(r['dollars'] for r in self.receivables)
        for p in self.positions.values():
            value,age=mark_position(p,data,i,False)
            if value is None:
                bad=True
            else:
                nav+=value;stale=max(stale,age)
        if bad:
            self.invalid_nav=True
        else:
            self.high=max(self.high,nav)
            if nav/self.high-1<=-data.cfg['drawdown_limit'] and not self.derisk:
                self.derisk=True;self.cooldown=i+data.cfg['cooldown_sessions']
            self.last_nav=nav
        self.rows.append({'date':day,'session':i,'nav':None if bad else nav,'cash':self.cash,
                          'dividend_receivable':sum(r['dollars'] for r in self.receivables),'funded_gross':gross,
                          'positions':len(self.positions),'stale_sessions':stale,'unknown_nav':bad,
                          'baseline_risk_comparable':self.baseline_risk_comparable})

    def result(self):
        trades=list(self.trades)
        for p in self.positions.values():
            row=p['r'];trades.append({'anchor_id':row['anchor_id'],'pair_id':row['pair_id'],'issuer':row['issuer'],
                'entry_date':row['entry_date'],'status':'unresolved','reason':p.get('unresolved','still_open_at_history_end')})
        return {'daily':self.rows,'trades':trades,'accepted_entries':self.accepted_entries,
                'turnover_dollars':self.turnover,'invalid_nav':self.invalid_nav,
                'remaining_positions':len(self.positions),'baseline_risk_comparable':self.baseline_risk_comparable}


class FinancingStrategy(FundedStrategy):
    """Registered financing ledger driven by the shared Backtrader clock."""


def owned_strategy(data, study):
    folder=next(s['folder'] for s in data.cfg['studies'] if s['id']==study)
    path=ROOT/'Hypotheses'/folder/'strategies/funded.py'
    spec=importlib.util.spec_from_file_location('financing_owned_'+study,path)
    module=importlib.util.module_from_spec(spec)
    # Backtrader resolves class-owned parameters through sys.modules when it
    # instantiates the strategy, so the dynamically loaded owner must exist.
    sys.modules[spec.name]=module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name,None)
        raise
    if not issubclass(module.FinancingStrategy,FundedStrategy):
        raise ValueError('Folder strategy must use the registered funded session interface')
    return module.FinancingStrategy


def performance(result,cfg):
    rows=result['daily'];complete=bool(rows) and not result['invalid_nav'] and not result['remaining_positions']
    output={'sessions':len(rows),'completed_trades':sum(r['status']=='completed' for r in result['trades']),
            'unfilled_trades':sum(r['status']=='unfilled' for r in result['trades']),
            'unresolved_trades':result['remaining_positions'],'full_nav_available':complete,
            'baseline_risk_comparable':result['baseline_risk_comparable'],'turnover_dollars':result['turnover_dollars'],
            'annualization_sessions':252,'cash_return':0}
    if not complete:
        output.update(annualized_return=None,volatility=None,sharpe=None,max_drawdown=None,net_pnl=None)
        return output
    nav=np.array([cfg['initial_cash']]+[r['nav'] for r in rows],dtype=float)
    returns=nav[1:]/nav[:-1]-1;vol=float(returns.std(ddof=1)*np.sqrt(252)) if len(returns)>1 else 0.
    output.update(annualized_return=float((nav[-1]/nav[0])**(252/len(rows))-1),volatility=vol,
                  sharpe=float(returns.mean()*252/vol) if vol>0 else None,
                  max_drawdown=float(np.min(nav/np.maximum.accumulate(nav)-1)),net_pnl=float(nav[-1]-nav[0]),
                  turnover=float(result['turnover_dollars']/nav[:-1].mean()))
    return output


def benchmark_checks(data):
    """Expose S05 omissions without inventing a numerical benchmark policy."""
    spy=data.benchmark_asset('SPY')
    return {'id':'S05','status':'partial','spy_source_status':spy['status'],
            'spy_missing_objects':spy.get('missing',[]),
            'available_comparisons':['same_accepted_entry_stock','zero_interest_cash','ordinary_same_shape'],
            'registered_momentum':'prior21_session_return_positive_long_otherwise_cash',
            'pending_comparisons':['funded_SPY','past_risk_matched_momentum','same_universe_buy_and_hold'],
            'missing_method_decisions':['ex_ante_volatility_target_and_scaling_formula',
                'volatility_floor_and_exposure_scaling_cap','whole_or_fractional_share_rounding',
                'benchmark_rebalance_schedule','SPY_name_sector_cap_treatment',
                'same_universe_weighting_and_missing_asset_policy'],
            'reason':'Registration names these baselines but does not freeze their numerical risk-scaling and portfolio policies'}


def run_task(run,task_id):
    scheduled();run=Path(run);manifest=verify_manifest(run);task=read_json(run/'tasks.json')[task_id]
    checkpoint=run/'receipts'/f'task-{task_id}.json'
    if checkpoint.exists():
        old=read_json(checkpoint)
        if old.get('manifest_id')!=manifest['manifest_id'] or old.get('status')!='completed':
            raise ValueError('Checkpoint identity/status differs')
        for relative,h in old['files'].items():
            target=(run/relative).resolve()
            if not target.is_relative_to(run.resolve()) or digest(target)!=h:
                raise ValueError('Completed checkpoint output differs')
        return old
    started=time.monotonic();data=Data(run)
    records=[r for r in data.records if r['study']==task['study'] and r['variant']==task['variant']]
    strategy_class=owned_strategy(data,task['study'])
    folder=run/'results/tasks'/str(task_id);folder.mkdir(parents=True,exist_ok=True)
    trades=[];nav=[];coverage=[];metrics=[]
    for row in records:
        coverage.append({**task,'anchor_id':row['anchor_id'],'pair_id':row['pair_id'],'shape':row['shape'],
                         'role':row['role'],'issuer':row['issuer'],'status':eligibility(row,data),
                         'coverage_stage':'acquisition_eligibility'})
        for horizon in [*data.cfg['horizons'],'expiry']:
            for stock_only in [False,True]:
                outcome=unit_trade(row,data,horizon,stock_only)
                trades.append({**task,**outcome,**quoted_diagnostics(row,data,outcome,stock_only)})
    for shape in data.cfg['shapes']:
        for role in ['event','ordinary','debt_only','underwriting_only']:
            selected=[r for r in records if r['shape']==shape and r['role']==role]
            overlay=Ledger(data,selected);over_result=replay(strategy_class,overlay,data.dates)
            stock=Ledger(data,over_result['accepted_entries'],True,True);stock_result=replay(strategy_class,stock,data.dates)
            for stock_only,result in [(False,over_result),(True,stock_result)]:
                label={**task,'shape':shape,'role':role,'stock_only':stock_only}
                nav.extend({**label,**r} for r in result['daily'])
                # Preserve actual portfolio fills, costs, risk exits and every
                # funding/cooldown exclusion separately from unit diagnostics.
                coverage.extend({**label,**r,'coverage_stage':'portfolio_ledger'} for r in result['trades'])
                metrics.append({**label,**performance(result,data.cfg)})
    fields=sorted({k for r in trades for k in r}) or ['study','variant','shape','anchor_id','pair_id','role','stock_only','horizon','status','reason','net_pnl','net_return','downside_loss','path_complete']
    csv_write(folder/'trades.csv',trades,fields)
    csv_write(folder/'signal_diagnostics.csv',trades,fields)
    csv_write(folder/'nav.csv',nav)
    csv_write(folder/'coverage.csv',coverage,sorted({k for r in coverage for k in r}) or ['study','variant','shape','role','issuer','status'])
    details={'status':'completed','task':task,'manifest_id':manifest['manifest_id'],
             'source_id':data.source['source_id'],'elapsed_seconds':time.monotonic()-started,
             'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None,
             'records':len(records),'unit_outcomes':len(trades),'portfolios':metrics,
             'benchmark_checks':benchmark_checks(data),'fill_model':'assumed_next_daily_close'}
    write_json(folder/'task.json',details)
    receipt(run,f'task-{task_id}',list(folder.glob('*.csv'))+[folder/'task.json'],details)
    return details
