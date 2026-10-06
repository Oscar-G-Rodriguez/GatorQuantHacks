"""Independent arithmetic and state-machine fixtures, no historical fits."""
import math
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from discovery.mechanism_accounting import construction, Ledger, performance, quote_set, reserve, transaction
from discovery.mechanism_data import settings
from discovery.mechanism_statistics import cluster_sample, chronological, train_prediction,evaluate_prediction
from discovery.mechanism_engine import FundedStrategy,replay
from discovery.mechanism_run import load,require_compute
from discovery.mechanism_features import classification,build


def quote(bid=4.9, ask=5.1, timestamp=100):
    return dict(bid_price=bid, ask_price=ask, sip_timestamp=timestamp, bid_size=5, ask_size=5)


class AccountingIntegrity(unittest.TestCase):
    def test_zero_category_window_has_schema_and_inconclusive_analyses(self):
        class EmptySource:
            source={"anchors":[]}
            cfg=settings()
        for study in ["H18","H19","H20"]:
            strategy=load(study,"strategy")
            _,f,h,_=build(EmptySource(),strategy.CATEGORY,strategy.SHAPE,{})
            findings=load(study,"analysis").evaluate(f,h,settings())
            self.assertEqual(findings["mechanism"]["status"],"inconclusive")
    def test_real_runner_requires_allocation(self):
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaisesRegex(RuntimeError,"Slurm"):
                require_compute()

    def test_owned_analyses_keep_empty_coverage_inconclusive(self):
        metadata=dict(event_id="fixture",issuer="A",cohort="event",delay=0,bucket="120",otm=.05,
                      filing_session=0,filing_date="2024-01-02",classification="incomplete_text_unknown",
                      premium_log_change=None,synthetic_return=None,abs_synthetic_return=None,elapsed_dte=None,
                      uncertainty=None,momentum=None,earnings=0,guidance=0,debt=0,downside_concentration=None,rms=None,
                      target_end=None,concentration_target_end=None,early_downside=None,verified_terms=0,compensation_cotag=0,text_terms_proxy=0)
        f=pd.DataFrame([metadata])
        h=pd.DataFrame([dict(anchor_id="fixture",event_id="fixture",issuer="A",cohort="event",filing_date="2024-01-02",
                             filing_session=0,shape="covered_call",horizon=5,delay=0,cost_multiplier=1,bucket="120",otm=.05,
                             status="inconclusive",stock_notional_return=None,collateral_return=None)])
        for study in ["H18","H19","H20"]:
            r=load(study,"analysis").evaluate(f,h,settings())
            self.assertEqual(r["mechanism"]["status"],"inconclusive")

    def test_backtrader_clock_runs_every_fixture_session(self):
        class ClockLedger:
            def __init__(self):self.dates=[]
            def step(self,d):self.dates.append(d)
            def result(self):return self.dates
        ledger=ClockLedger();dates=["2024-01-02","2024-01-03","2024-01-04"]
        self.assertEqual(replay(FundedStrategy,ledger,dates),dates)

    def test_excerpt_cannot_be_verified_absence(self):
        with self.assertRaises(ValueError):
            classification({"event_id":"a"},{"a":{"classification":"verified_absence_in_complete_filing"}})

    def test_contract_cash_and_fees_hand_calculation(self):
        cfg = settings(); cfg["adverse_slippage_premium_bps_side"] = 0
        cash, cost, _ = transaction({"call": 1, "put": -1}, {"call": quote(), "put": quote(3.9,4.1)}, cfg)
        self.assertAlmostEqual(cash, -510+390-1.3)
        self.assertAlmostEqual(cost, 20+1.3)
        closing, _, _ = transaction({"call": 1, "put": -1}, {"call": quote(), "put": quote(3.9,4.1)}, cfg, False)
        self.assertAlmostEqual(cash+closing, -40-2.6)

    def test_three_leg_shape_and_doubled_friction(self):
        cfg=settings(); cfg["adverse_slippage_premium_bps_side"]=0
        legs=construction("covered_call")
        self.assertEqual(len(legs),3)
        q={r:quote() for r in legs}
        _,c1,_=transaction(legs,q,cfg)
        _,c2,_=transaction(legs,q,cfg,cost_multiplier=2)
        self.assertAlmostEqual(c1,30+1.95)
        self.assertAlmostEqual(c2,2*c1)

    def test_collateral_not_option_premium(self):
        s={"atm_strike":100,"legs":{"lower_put_0.05":{"strike_price":95}}}
        self.assertEqual(reserve(s,"cash_secured_put",construction("cash_secured_put")),9500)
        self.assertEqual(reserve(s,"protective_put",construction("protective_put")),10000)

    def test_cash_metrics_do_not_invent_sharpe(self):
        cfg=settings(); initial=1e6
        rows=[dict(date="2024-01-02",nav=initial*math.exp(.04/365.25),elapsed_days=1,
                   traded_premium=0,traded_reserve=0,stale_legs=0)]
        self.assertIsNone(performance(rows,initial,cfg)["sharpe"])
        rows[0]["nav"]=None
        self.assertEqual(performance(rows,initial,cfg)["status"],"inconclusive")

    def test_asynchronous_multi_leg_quotes_rejected(self):
        cfg=settings(); cfg["quote_max_leg_span_seconds"]=10
        cutoff=100*10**9
        s={"quotes":{"entry":{"cutoff_ns":cutoff,"legs":{
            "a":{"quote":quote(timestamp=cutoff)},"b":{"quote":quote(timestamp=cutoff-20*10**9)}}}}}
        self.assertEqual(quote_set(s,"entry",["a","b"],cfg)[1],"asynchronous_quote_legs")

    def test_duplicate_issuer_bootstrap_keeps_multiplicity(self):
        class Draw:
            def integers(self,*args):return np.array([0,0])
        f=pd.DataFrame({"issuer":["A","A","B"],"x":[1,2,999]})
        self.assertEqual(cluster_sample(f,Draw()).x.tolist(),[1,2,1,2])

    def test_chronological_fit_excludes_unmatured_training_targets(self):
        f=pd.DataFrame({"filing_date":["2024-06-01"]*20+["2024-08-01"]*5,
                        "target_end":["2024-07-10"]*8+["2024-06-10"]*12+["2024-08-10"]*5,
                        "x":range(25),"y":range(25),"z":range(25)})
        out=chronological(f,"y",["x"],["x","z"],settings())[0]
        self.assertEqual(out["train_rows"],12)
        self.assertEqual(out["last_training_target_end"],"2024-06-10")

    def test_failed_exit_retains_initiated_position_and_cash(self):
        cfg=settings(); cfg["rate"]=0
        dates=["2024-01-02","2024-01-03","2024-01-04"]
        s={"atm_strike":100,"expiry":"2024-05-01","legs":{"lower_put_0.05":{"strike_price":95}},
           "quotes":{"entry":{"date":dates[1],"cutoff_ns":100,"legs":{"lower_put_0.05":{"quote":quote()}}},
                     "2":{"date":dates[2],"cutoff_ns":200,"legs":{"lower_put_0.05":{"quote":None}}}}}
        a=dict(cohort="event",filing_date=dates[0],issuer="A",accession="a",ticker="ABC",anchor_id="a",event_id="a",filing_session=0,
               variants={"0":{"entry_date":dates[1],"decision_date":dates[0],"selected":{"120":s}}})
        class Source:
            index={d:i for i,d in enumerate(dates)}
            source={"window":{"start":dates[0]}}
            def prior_volume(self,*args):return 200
            def mark(self,*args):return {"price":5,"age_sessions":0}
        source=Source();source.dates=dates
        with patch("discovery.mechanism_accounting.settings",return_value=cfg):
            ledger=Ledger(source,[a],"cash_secured_put",horizon=2)
            for d in dates:ledger.step(d)
        self.assertEqual(len(ledger.positions),1)
        self.assertEqual(len(ledger.closed),0)
        self.assertEqual(ledger.result()["metrics"]["unfilled_exits"],1)
        self.assertGreater(ledger.cash,1e6)

    def test_drawdown_liquidates_next_feasible_quote_without_planned_exit(self):
        cfg=settings();cfg["rate"]=0
        dates=["2024-01-02","2024-01-03","2024-01-04"]
        s={"atm_strike":100,"expiry":"2024-05-01","legs":{"lower_put_0.05":{"strike_price":95}},
           "quotes":{"entry":{"date":dates[1],"cutoff_ns":100,"legs":{"lower_put_0.05":{"quote":quote()}}},
                     "risk_available":{"date":dates[2],"cutoff_ns":200,"legs":{"lower_put_0.05":{"quote":quote(999,1000,190)}}}}}
        a=dict(cohort="event",filing_date=dates[0],issuer="A",accession="a",ticker="ABC",anchor_id="a",event_id="a",filing_session=0,
               variants={"0":{"entry_date":dates[1],"decision_date":dates[0],"selected":{"120":s}}})
        class Source:
            index={d:i for i,d in enumerate(dates)}
            source={"window":{"start":dates[0]}}
            def prior_volume(self,*args):return 200
            def mark(self,*args):return {"price":1000,"age_sessions":0}
        source=Source();source.dates=dates
        with patch("discovery.mechanism_accounting.settings",return_value=cfg):
            ledger=Ledger(source,[a],"cash_secured_put",horizon=5)
            for d in dates:ledger.step(d)
        self.assertEqual(len(ledger.closed),1)
        self.assertTrue(ledger.closed[0]["risk_liquidation"])
        self.assertEqual(len(ledger.positions),0)

    def test_frozen_prediction_never_trains_on_final_values(self):
        f=pd.DataFrame({"filing_date":["2024-01-03"]*20+["2026-01-03"],
                        "target_end":["2024-01-10"]*20+["2026-01-10"],
                        "uncertainty":list(range(20))+[9999],"momentum":list(range(20))+[9999],
                        "earnings":[0]*21,"guidance":[0]*21,"debt":[0]*21,"target":list(range(20))+[9999]})
        model=train_prediction(f,"target",settings())
        self.assertEqual(model["train_rows"],20)
        self.assertEqual(model["models"]["baseline"]["mean"],[9.5,9.5])
        import copy
        before=copy.deepcopy(model)
        evaluate_prediction(f,model)
        self.assertEqual(model,before)


if __name__=="__main__":unittest.main()
