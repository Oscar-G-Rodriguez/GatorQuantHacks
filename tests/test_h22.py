"""Synthetic correctness checks; no real H22 statistical work runs on the PC."""
import importlib.util
from pathlib import Path
import sys
import unittest
import tempfile
import json
import zipfile
import hashlib
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
import pandas as pd

FOLDER=Path(__file__).resolve().parents[1]/"Hypotheses/H22 - Debt Financing Resolution Covered Calls"
sys.path.insert(0,str(FOLDER))
from research import classification, choose_call, control_match, prior_features, collect_debt
from strategy import Ledger, unit_trade, fees, Data
from discovery.mechanism_engine import replay
from strategy import STRATEGY_CLASS
from analysis import uncertainty, joint_weights, pair_trades, diagnostic_predictions
from pipeline import terminal_receipts, import_return
from strategy import run_task
from discovery.io import write_json, digest


class PreparationTests(unittest.TestCase):
    def test_multiple_debt_excerpts_remain_one_filing(self):
        seen={};r={"accession_number":"A","filing_date":"2023-01-01","supporting_text":"Issued notes."}
        collect_debt(seen,"CIK","AAA",r,1)
        collect_debt(seen,"CIK","AAA",{**r,"supporting_text":"Received proceeds."},1)
        collect_debt(seen,"CIK","AAA",r,1)
        self.assertEqual(len(seen),1);self.assertEqual(len(seen[("CIK","A")]["excerpts"]),2)
        with self.assertRaises(ValueError):collect_debt(seen,"CIK","AAA",{**r,"filing_date":"2023-01-02"},2)

    def test_completed_receipt_and_planned(self):
        self.assertEqual(classification("The company completed its offering of notes. It received net proceeds of $100 million.")[0],"completed")
        self.assertEqual(classification("The company will issue notes and expects to receive proceeds.")[0],"planned")
        self.assertEqual(classification("The company entered an underwriting agreement for notes.")[0],"unknown")
        self.assertEqual(classification(None)[0],"unknown")
        self.assertNotEqual(classification("The company has not completed its debt financing or received proceeds.")[0],"completed")
        self.assertEqual(classification("The company completed its sale of notes. The notes will mature in 2030.")[0],"unknown")

    def test_contract_selection_and_units(self):
        base=dict(contract_type="call",shares_per_contract=100,exercise_style="american",expiration_date="2023-05-01")
        rows=[dict(base,ticker="C104",strike_price=104),dict(base,ticker="C106",strike_price=106),dict(base,ticker="ADJ",strike_price=105,shares_per_contract=50)]
        v={"range":[90,180],"dte":120,"otm":.05}
        self.assertEqual(choose_call(rows,"2023-01-02",100,v)["ticker"],"C104")
        self.assertIsNone(choose_call(rows,"2023-01-02",50,v))

    def test_future_control_never_used_and_calipers(self):
        dates=pd.bdate_range("2022-01-01",periods=400).strftime("%Y-%m-%d").tolist()
        x=pd.DataFrame({"a":np.linspace(-.1,.1,400),"b":np.sin(np.arange(400)/30)},index=dates)
        j,_=control_match(x,300,set(),dates)
        self.assertIsNotNone(j);self.assertLessEqual(j,216)
        past=x.iloc[:301].copy(); x.iloc[301:]=1e30
        self.assertEqual(control_match(x,300,set(),dates),control_match(past,300,set(),dates))

    def test_missing_sessions_no_shortened_window(self):
        dates=pd.bdate_range("2022-01-01",periods=50).strftime("%Y-%m-%d").tolist()
        stock={d:{"c":100+i,"v":1000} for i,d in enumerate(dates)};spy=dict(stock)
        f=prior_features(stock,spy,dates)
        self.assertAlmostEqual(f.iloc[30].momentum,130/109-1)
        del stock[dates[20]]
        missing=prior_features(stock,spy,dates)
        self.assertTrue(missing.iloc[30].isna().all())


def synthetic_data():
    dates=pd.bdate_range("2023-01-02",periods=90).strftime("%Y-%m-%d").tolist()
    cfg={"initial_cash":1000000,"stock_friction":.0006,"option_friction":.05,"option_fee":.65,
         "minimum_prior_option_volume":100,"minimum_prior_stock_volume":10000,"exit_retry_sessions":5,
         "name_limit":.05,"gross_limit":.20,"drawdown_limit":.05,"cooldown_sessions":21,"end":dates[-1]}
    stock={d:{"c":100.,"v":100000} for d in dates};call={d:{"c":5.,"v":100} for d in dates}
    r={"anchor_id":"a","pair_id":"p","issuer":"1","ticker":"AAA","variant":"primary","role":"event",
       "event_status":"completed","session":5,"entry_session":6,"date":dates[5],"entry_date":dates[6],
       "status":"bars_downloaded","nominal_decision_close":100.,"accessions":["acc"],"features":{},
       "contract":{"ticker":"CALL","strike_price":105.,"expiration_date":"2023-12-31","exercise_style":"american"}}
    d=SimpleNamespace(dates=dates,index={s:i for i,s in enumerate(dates)},cfg=cfg,actions={},marks=lambda r,leg:stock if leg=="stock" else call)
    return d,r,stock,call


class AccountingTests(unittest.TestCase):
    def test_drawdown_exits_next_session_and_cooldown(self):
        d,r,stock,calls=synthetic_data();d.cfg["drawdown_limit"]=.005
        for day in d.dates[7:]:stock[day]["c"]=1.;calls[day]["c"]=.1
        later={**r,"anchor_id":"later","entry_session":10,"session":9,"date":d.dates[9],"entry_date":d.dates[10]}
        ledger=replay(STRATEGY_CLASS,Ledger(d,[r,later],1,"time_value"),d.dates)
        exits=[t for t in ledger["trades"] if t.get("reason")=="drawdown_exit"]
        self.assertEqual(exits[0]["exit_date"],d.dates[8])
        self.assertTrue(any(t.get("reason")=="risk_cooldown_or_unknown_nav" for t in ledger["trades"]))

    def test_quote_staleness_synchrony_and_sizes(self):
        data=object.__new__(Data);data.cfg={"quote_max_age_seconds":60,"quote_max_relative_spread":.25,"quote_synchrony_seconds":5}
        cut=1000000000000;q={"bid_price":4.,"ask_price":4.2,"bid_size":2,"ask_size":2,"sip_timestamp":cut}
        data.objects={"s":[q],"c":[q]}
        r={"quote_objects":{"entry_stock":{"object":"s","cutoff_ns":cut},"entry_call":{"object":"c","cutoff_ns":cut}}}
        self.assertEqual(data.quote_pair(r,"entry")[1],"fresh_quotes")
        data.objects["c"]=[{**q,"sip_timestamp":cut-int(6e9)}]
        self.assertEqual(data.quote_pair(r,"entry")[1],"asynchronous_quotes")
        data.objects["c"]=[{**q,"sip_timestamp":cut-int(61e9)}]
        self.assertEqual(data.quote_pair(r,"entry")[1],"missing_or_stale_quote")
        data.objects["c"]=[{**q,"bid_size":0}]
        self.assertEqual(data.quote_pair(r,"entry")[1],"invalid_quote_or_size")

    def test_hand_calculated_trade_and_ledger_reconcile(self):
        d,r,stock,call=synthetic_data()
        for day in d.dates[7:]:stock[day]["c"]=103.;call[day]["c"]=3.
        result=unit_trade(r,d,21)
        expected=500-fees(100,5,d.cfg)-fees(103,3,d.cfg)
        self.assertAlmostEqual(result["net_pnl"],expected)
        ledger=replay(STRATEGY_CLASS,Ledger(d,[r],1,"time_value"),d.dates)
        self.assertAlmostEqual(ledger["daily"][-1]["nav"]-1e6,expected)
        self.assertEqual(ledger["remaining_positions"],0)

    def test_fills_after_decision_and_doubled_costs(self):
        d,r,_,_=synthetic_data();bad={**r,"entry_session":5}
        with self.assertRaises(ValueError):unit_trade(bad,d,21)
        a=unit_trade(r,d,21);b=unit_trade(r,d,21,2)
        self.assertAlmostEqual(b["total_cost"],2*a["total_cost"])
        self.assertLess(b["net_pnl"],a["net_pnl"])

    def test_missing_entry_unfilled_and_missing_exit_unresolved(self):
        d,r,_,calls=synthetic_data();del calls[r["entry_date"]]
        self.assertEqual(unit_trade(r,d,21)["status"],"missing_decision_or_entry_bar")
        d,r,_,calls=synthetic_data()
        for i in range(27,33):del calls[d.dates[i]]
        self.assertEqual(unit_trade(r,d,21)["status"],"initiated_unfilled_exit_after_retries")

    def test_assignment_and_dividend_are_not_double_counted(self):
        d,r,stock,calls=synthetic_data();ex=d.dates[10]
        d.actions={"AAA":{"splits":[],"dividends":[{"ex_dividend_date":ex,"cash_amount":1.,"currency":"USD","declaration_date":d.dates[0],"pay_date":d.dates[15]}]}}
        for day in d.dates[7:]:stock[day]["c"]=110.;calls[day]["c"]=5.1
        result=unit_trade(r,d,21)
        self.assertEqual(result["exit_reason"],"modelled_early_assignment");self.assertEqual(result["dividend_accrual"],0)
        ledger=replay(STRATEGY_CLASS,Ledger(d,[r],1,"time_value"),d.dates)
        self.assertAlmostEqual(ledger["daily"][-1]["nav"]-1e6,result["net_pnl"])
        # OTM shares receive the dividend once, including the receivable before payment.
        d,r,stock,calls=synthetic_data();d.actions={"AAA":{"splits":[],"dividends":[{"ex_dividend_date":ex,"cash_amount":1.,"currency":"USD","pay_date":d.dates[15],"declaration_date":d.dates[0]}]}}
        result=unit_trade(r,d,21);ledger=replay(STRATEGY_CLASS,Ledger(d,[r],1,"time_value"),d.dates)
        self.assertEqual(result["dividend_accrual"],100.)
        self.assertAlmostEqual(ledger["daily"][-1]["nav"]-1e6,result["net_pnl"])

    def test_future_split_is_unresolved_not_entry_exclusion(self):
        d,r,_,_=synthetic_data();d.actions={"AAA":{"splits":[{"execution_date":d.dates[10]}],"dividends":[]}}
        result=unit_trade(r,d,21)
        self.assertEqual(result["status"],"initiated_unknown_option_split_deliverable")
        ledger=replay(STRATEGY_CLASS,Ledger(d,[r],1,"time_value"),d.dates)
        self.assertEqual(ledger["remaining_positions"],1);self.assertTrue(ledger["invalid_nav"])

    def test_name_cash_limit_and_repeated_signal(self):
        d,r,stock,calls=synthetic_data();other={**r,"anchor_id":"b","pair_id":"q"}
        ledger=replay(STRATEGY_CLASS,Ledger(d,[r,other],1,"time_value"),d.dates)
        self.assertTrue(any(t.get("reason")=="issuer_position_already_open" for t in ledger["trades"]))
        d,r,stock,calls=synthetic_data()
        for b in stock.values():b["c"]=1000
        ledger=replay(STRATEGY_CLASS,Ledger(d,[r],1,"time_value"),d.dates)
        self.assertTrue(any(t.get("reason")=="funding_or_exposure_limit" for t in ledger["trades"]))


class StatisticalTests(unittest.TestCase):
    def test_joint_resamples_keep_identical_cells_identical(self):
        dates=pd.bdate_range("2022-01-01",periods=500).strftime("%Y-%m-%d").tolist()
        rows=[{"issuer":str(i%10),"event_session":200+i,"ordinary_session":100+i,
               "covered_call_increment":np.sin(i)/100,"overlay_increment":np.sin(i)/100} for i in range(50)]
        cfg={"minimum_pairs":30,"minimum_issuers":8,"resamples":199}
        result=uncertainty(rows,dates,cfg,63,7)
        self.assertEqual(result[0]["adjusted_p"],result[1]["adjusted_p"])
        self.assertEqual(result[0]["mean"],result[1]["mean"])
        self.assertEqual(result[0]["family_size"],2)
        self.assertTrue(all(0<r["adjusted_p"]<=1 for r in result))

    def test_empty_and_rare_groups_remain_unsupported(self):
        r=uncertainty([],[],{"minimum_pairs":30,"minimum_issuers":8},63,1)
        self.assertTrue(all(x["status"]=="insufficient_support" for x in r))
        self.assertTrue(all(x["status"]=="insufficient_support" for x in diagnostic_predictions([])))

    def test_paired_common_rows_and_preentry_caliper(self):
        d,r,_,_=synthetic_data();event=unit_trade(r,d,21)
        ordinary={**event,"role":"ordinary","anchor_id":"control"}
        es=unit_trade(r,d,21,stock_only=True);os={**es,"role":"ordinary","anchor_id":"control"}
        rows,excluded=pair_trades([event,ordinary,es,os])
        self.assertEqual(len(rows),1);self.assertAlmostEqual(rows[0]["overlay_increment"],0)
        ordinary={**ordinary,"decision_premium_ratio":10}
        rows,excluded=pair_trades([event,ordinary,es,os])
        self.assertEqual(len(rows),0);self.assertEqual(excluded[0]["reason"],"pre_entry_option_caliper")


class TransferAndCheckpointTests(unittest.TestCase):
    def test_unfinished_or_changed_stage_cannot_be_exported(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);m={"phase":"backtest","manifest_id":"toy"}
            write_json(run/"tasks.json",[{"task":0}])
            payload=run/"result.txt";payload.write_text("completed toy")
            r={"manifest_id":"toy","status":"completed","files":{"result.txt":digest(payload)}}
            write_json(run/"receipts/task-0.json",r)
            with self.assertRaisesRegex(ValueError,"Unfinished stages"):terminal_receipts(run,m)
            write_json(run/"receipts/analysis.json",r)
            self.assertEqual(len(terminal_receipts(run,m)),2)
            payload.write_text("corrupted")
            with self.assertRaises(ValueError):terminal_receipts(run,m)

    def test_return_verifies_archive_members_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/"run";run.mkdir()
            write_json(run/"manifest.json",{"manifest_id":"toy"})
            content=b"toy output";h=hashlib.sha256(content).hexdigest()
            archive=root/"return.zip"
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("results/toy.txt",content)
                z.writestr("return.json",json.dumps({"manifest_id":"toy","files":{"results/toy.txt":h}}))
            with self.assertRaises(ValueError):import_return(archive,run,"incorrect")
            import_return(archive,run,digest(archive))
            self.assertEqual((run/"results/toy.txt").read_bytes(),content)
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("../escape.txt",content)
                z.writestr("return.json",json.dumps({"manifest_id":"toy","files":{"../escape.txt":h}}))
            with self.assertRaises(ValueError):import_return(archive,run,digest(archive))
            self.assertFalse((root/"escape.txt").exists())

    def test_completed_checkpoint_skips_replay_but_rejects_changed_output(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);write_json(run/"tasks.json",[{"task":0}])
            output=run/"toy.txt";output.write_text("done")
            write_json(run/"receipts/task-0.json",{"manifest_id":"toy","status":"completed","files":{"toy.txt":digest(output)}})
            with patch("strategy.scheduled"),patch("strategy.verify_manifest",return_value={"manifest_id":"toy"}),patch("strategy.Data") as data:
                run_task(run,0);data.assert_not_called()
                output.write_text("changed")
                with self.assertRaises(ValueError):run_task(run,0)
                data.assert_not_called()


if __name__=="__main__": unittest.main()
